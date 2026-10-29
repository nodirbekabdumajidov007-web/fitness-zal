"""Trainer ("coach") area: a trainer whose Trainer profile is linked to their site account signs in as a trainer and gets
their own dashboard: today's classes with who booked, personal-training requests, their clients (with the ones who need
attention first) and a plan builder to give a client a workout plan.

A trainer only ever sees members connected to them (personal sessions, their plans, their classes); a new client is
added by the exact member code or phone number, never by browsing the member list."""
import re
from datetime import timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import services, telegram
from .forms import normalize_phone
from .models import Booking, GymClass, PersonalRecord, PTSession, Trainer, User, Visit, WorkoutPlan
from .views import flash

ATTENTION_DAYS = 7  # a client who has not come for this long is shown first


def trainer_of(user):
    if not user.is_authenticated:
        return None
    return Trainer.objects.filter(user=user, active=True).first()


def trainer_required(view):
    @wraps(view)
    @login_required
    def wrapper(request, *a, **kw):
        t = trainer_of(request.user)
        if not t:
            flash(request, messages.ERROR, "not_trainer")
            return redirect("dashboard")
        request.trainer = t
        return view(request, *a, **kw)
    return wrapper


def client_ids(t):
    since = timezone.localdate() - timedelta(days=60)
    ids = set(PTSession.objects.filter(trainer=t).values_list("user_id", flat=True))
    ids |= set(WorkoutPlan.objects.filter(trainer=t).values_list("user_id", flat=True))
    ids |= set(Booking.objects.filter(gym_class__trainer=t, date__gte=since).values_list("user_id", flat=True))
    return ids


def client_or_404(t, uid):
    if uid not in client_ids(t):
        raise Http404()
    return get_object_or_404(User, pk=uid, is_active=True)


@trainer_required
def home(request):
    t, now, today = request.trainer, timezone.now(), timezone.localdate()
    monday = today - timedelta(days=today.weekday())
    week = []
    for i in range(7):
        d = monday + timedelta(days=i)
        items = []
        for c in GymClass.objects.filter(trainer=t, active=True, weekday=i).order_by("start_time"):
            people = [b.user for b in Booking.objects.filter(gym_class=c, date=d).select_related("user")]
            items.append({"c": c, "people": people, "n": len(people), "w": min(100, round(len(people) / c.capacity * 100)) if c.capacity else 0})
        week.append({"d": d, "wd": str(i), "today": d == today, "items": items})
    ids = client_ids(t)
    last_visit = dict(Visit.objects.filter(user_id__in=ids).values("user_id").annotate(m=Max("ts")).values_list("user_id", "m"))
    plans = {p.user_id: p for p in WorkoutPlan.objects.filter(user_id__in=ids, active=True)}
    clients = []
    for u in User.objects.filter(pk__in=ids, is_active=True).order_by("first_name"):
        lv = last_visit.get(u.pk)
        days = (now - lv).days if lv else None
        plan = plans.get(u.pk)
        mine = bool(plan and plan.trainer_id == t.pk)
        attention = days is None or days >= ATTENTION_DAYS or not plan
        clients.append({"u": u, "days": days, "plan": plan, "mine": mine, "attention": attention,
                        "why": "no_visit" if days is None else ("away" if days >= ATTENTION_DAYS else ("no_plan" if not plan else ""))})
    clients.sort(key=lambda c: (not c["attention"], c["u"].first_name))
    pending = PTSession.objects.filter(trainer=t, status="requested", starts__gte=now).select_related("user")
    upcoming = PTSession.objects.filter(trainer=t, status="confirmed", starts__gte=now).select_related("user")[:8]
    month_done = PTSession.objects.filter(trainer=t, status="confirmed", starts__year=today.year, starts__month=today.month, starts__lt=now).count()
    return render(request, "gym/coach/home.html", {
        "t": t, "week": week, "today_items": week[today.weekday()]["items"], "clients": clients, "pending": pending, "upcoming": upcoming,
        "stats": {"clients": len(clients), "attention": sum(1 for c in clients if c["attention"]), "pending": pending.count(),
                  "week_bookings": sum(x["n"] for d in week for x in d["items"]), "month_done": month_done},
    })


@require_POST
@trainer_required
def pt_action(request, pk, action):
    s = get_object_or_404(PTSession, pk=pk, trainer=request.trainer)  # only the trainer's own sessions
    if s.status != "requested":
        return redirect("coach")
    if action == "confirm":
        s.status = PTSession.Status.CONFIRMED
        telegram.notify_user(s.user, "tg_pt_confirmed", trainer=request.trainer.name, time=timezone.localtime(s.starts).strftime("%d.%m %H:%M"))
    else:
        s.status = PTSession.Status.CANCELLED
        telegram.notify_user(s.user, "tg_pt_cancelled", trainer=request.trainer.name)
    s.save(update_fields=["status"])
    flash(request, messages.SUCCESS, "done_ok")
    return redirect("coach")


@require_POST
@trainer_required
def add_client(request):
    """Find one member by the exact member code (FZ-0012) or phone number and open the plan builder for them."""
    q = request.POST.get("q", "").strip()
    user = None
    m = re.fullmatch(r"(?i)fz-?0*(\d+)", q)
    if m:
        user = User.objects.filter(pk=int(m.group(1)), is_active=True, is_superuser=False).first()
    elif normalize_phone(q):
        user = User.objects.filter(phone=normalize_phone(q), is_active=True, is_superuser=False).first()
    if not user:
        flash(request, messages.ERROR, "client_not_found")
        return redirect("coach")
    request.session["coach_new"] = user.pk  # lets this trainer build a first plan for exactly this member
    return redirect("coach_plan", uid=user.pk)


@trainer_required
def client(request, uid):
    t = request.trainer
    u = client_or_404(t, uid)
    today = timezone.localdate()
    days = services.visit_days(u)
    month = [{"d": today - timedelta(days=i), "on": (today - timedelta(days=i)) in days} for i in range(27, -1, -1)]
    best = {}
    for r in PersonalRecord.objects.filter(user=u):
        if r.lift not in best or r.one_rm > best[r.lift].one_rm:
            best[r.lift] = r
    return render(request, "gym/coach/client.html", {
        "t": t, "m": u, "month": month, "visits_30": sum(1 for x in month if x["on"]), "stats": services.visit_stats(u),
        "plan": u.workout_plans.filter(active=True).first(), "mem": services.active_membership(u),
        "logs": list(u.bodylogs.order_by("-date", "-id")[:6]), "records": sorted(best.values(), key=lambda r: r.lift),
        "sessions": PTSession.objects.filter(user=u, trainer=t).order_by("-starts")[:6],
    })


@trainer_required
def plan(request, uid):
    """Plan builder: rows of (day, exercise, sets, reps, note). Saving replaces the member's active plan."""
    t = request.trainer
    u = get_object_or_404(User, pk=uid, is_active=True, is_superuser=False)
    if uid not in client_ids(t) and request.session.get("coach_new") != uid:
        raise Http404()  # not their client and not just looked up by exact code/phone
    current = u.workout_plans.filter(active=True).first()
    if request.method == "POST":
        rows = []
        for wd, name, sets, reps, note in zip(request.POST.getlist("wd"), request.POST.getlist("name"), request.POST.getlist("sets"),
                                              request.POST.getlist("reps"), request.POST.getlist("note")):
            name = name.strip()[:80]
            if not name:
                continue
            try:
                wd_i, sets_i = int(wd), max(1, min(20, int(sets or 3)))
            except ValueError:
                continue
            if 0 <= wd_i <= 6:
                rows.append((wd_i, name, sets_i, (reps or "10").strip()[:20], note.strip()[:120]))
        title = request.POST.get("title", "").strip()[:80]
        if not title or not rows:
            flash(request, messages.ERROR, "plan_empty")
            return redirect("coach_plan", uid=u.pk)
        with transaction.atomic():
            u.workout_plans.filter(active=True).update(active=False)
            p = WorkoutPlan.objects.create(user=u, trainer=t, title=title, notes=request.POST.get("notes", "").strip()[:2000], active=True)
            for i, (wd, name, sets, reps, note) in enumerate(rows):
                p.exercises.create(weekday=wd, name=name, sets=sets, reps=reps, note=note, order=i)
        telegram.notify_user(u, "tg_plan_new", trainer=t.name, title=title)
        flash(request, messages.SUCCESS, "plan_saved")
        return redirect("coach_client", uid=u.pk)
    rows = [{"wd": e.weekday, "name": e.name, "sets": e.sets, "reps": e.reps, "note": e.note} for e in current.exercises.all()] if current else []
    programs = {k: [{"wd": e[0], "name": e[1], "sets": e[2], "reps": e[3], "note": ""} for e in v["ex"]] for k, v in services.PROGRAMS.items()}
    return render(request, "gym/coach/plan.html", {
        "t": t, "m": u, "current": current, "rows": rows or [{"wd": timezone.localdate().weekday(), "name": "", "sets": 3, "reps": "10", "note": ""}],
        "programs": [{"key": k, "title": v["title"]} for k, v in services.PROGRAMS.items()], "program_rows": programs,
    })
