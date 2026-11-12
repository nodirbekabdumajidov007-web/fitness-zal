"""Fitness tracker pages (member side) and the read-only view for a trainer's clients. Every query is filtered by the signed-in member;
a trainer only gets the client's data through coach_views.client_or_404 (their own clients)."""
import csv
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from . import tracker
from .coach_views import client_or_404, trainer_required
from .models import BodyLog
from .models_tracker import TrackerGoal, WorkoutSession
from .templatetags.gym_tags import translate
from .tracker_text import tx_for
from .views import bmi_label, flash, safe_next

JS_KEYS = ["ftr_weight", "ftr_ma7", "ftr_goal", "ftr_projection", "ftr_measures", "ftr_body_fat", "ftr_resting_hr", "ftr_strength", "ftr_volume", "ftr_workouts",
           "ftr_visits", "ftr_calories", "ftr_target", "ftr_table", "ftr_no_data", "ftr_date", "ftr_week", "ftr_value", "ftr_diff", "ftr_before", "ftr_after", "ftr_pick_two",
           "ftr_m_waist", "ftr_m_chest", "ftr_m_hips", "ftr_m_neck", "ftr_m_arm", "ftr_m_thigh", "ftr_m_calf", "bmi", "weight", "ftr_est1rm", "ftr_streak", "ftr_adherence"]


TX_JS = ["empty_weight", "empty_measures", "empty_fat", "empty_strength", "empty_volume", "empty_activity", "empty_calories", "v_weight", "v_height", "v_date"]


def _labels(lang):
    labels = {k.replace("_", ""): translate(lang, k) for k in JS_KEYS}  # no underscores: the page audit treats "ftr_x" words as leaked keys
    text = tx_for(lang)
    labels.update({k.replace("_", ""): text[k] for k in TX_JS})
    return labels


def _fmt(v, lang, signed=False):
    """1.2 -> '1,2' (Uzbek / Russian decimal comma); signed adds the arrow: down, up or flat."""
    if v is None:
        return ""
    s = f"{abs(v):.1f}".replace(".", ",") if lang != "en" else f"{abs(v):.1f}"
    return (("↓" if v < 0 else "↑" if v > 0 else "→") + s) if signed else s


def _date_arg(raw, default=None):
    try:
        return date.fromisoformat((raw or "").strip())
    except ValueError:
        return default


def _body_rows(user, limit=30):
    logs = list(user.bodylogs.order_by("-date", "-id")[:limit])
    height = tracker.latest_height(user)  # an entry without its own height still gets a BMI from the newest known one
    out = []
    for l in logs:
        bmi = l.bmi or tracker.bmi_value(l.weight, tracker.latest_height(user, l.date) or height)
        out.append({"l": l, "bmi": bmi, "label": bmi_label(bmi)})
    return out


def _context(request, user, readonly=False, data_url="", compare_url=""):
    period = request.GET.get("period", tracker.DEFAULT_PERIOD)
    period = period if period in tracker.PERIODS else tracker.DEFAULT_PERIOD
    goals = tracker.goals_overview(user)
    last = user.bodylogs.order_by("-date", "-id").first()
    summary = tracker.progress_summary(user)
    summary["d7_txt"], summary["d30_txt"] = _fmt(summary["d7"], request.lang, True), _fmt(summary["d30"], request.lang, True)
    return {
        "readonly": readonly, "member": user, "compare_url": compare_url or reverse("progress_compare"), "period": period, "periods": list(tracker.PERIODS), "data_url": data_url, "goals": goals,
        "labels": _labels(request.lang), "measures": tracker.MEASURES, "rows": _body_rows(user), "last": last, "tx": tx_for(request.lang),
        "recent_sessions": list(user.workout_sessions.prefetch_related("sets")[:3]),
        "summary": summary,
        "today": timezone.localdate().isoformat(),
    }


def _reached_goals(user):
    """Keys of the goals that are already reached right now; a failure here must never break saving a measurement."""
    try:
        return {(g["kind"], g["metric"]) for g in tracker.goals_overview(user) if g["state"] == "reached"}
    except Exception:
        return None


def _flash_goal_reached(request, user, before):
    """A celebration (confetti) when a measurement has just carried a goal over the line - and only then."""
    if before is None:
        return
    now = _reached_goals(user)
    if now and now - before:
        flash(request, messages.SUCCESS, "ftr_goal_reached", celebrate=True)


# ---------------------------------------------------------------- /progress/
@login_required
def progress_view(request):
    u = request.user
    edit = None
    if request.GET.get("edit", "").isdigit():
        edit = BodyLog.objects.filter(pk=int(request.GET["edit"]), user=u).first()
    if request.method == "POST":
        pk = request.POST.get("pk", "")
        before = _reached_goals(u)
        log, err = tracker.save_body_entry(u, request.POST, int(pk) if pk.isdigit() else None)
        if err:
            flash(request, messages.ERROR, err)
            return redirect(request.path + (f"?edit={pk}" if pk.isdigit() else ""))
        flash(request, messages.SUCCESS, "body_saved")
        _flash_goal_reached(request, u, before)
        return redirect("progress")
    ctx = _context(request, u, data_url=reverse("progress_data"))
    last_h = tracker.latest_height(u)
    src = edit or ctx["last"]
    fields = ["weight"] + (["note"] if edit else []) + tracker.MEASURES + (["body_fat", "resting_hr"] if edit else [])
    vals = {k: "" for k in ["weight", "note", "body_fat", "resting_hr"] + tracker.MEASURES}
    if src:
        for k in fields:
            v = getattr(src, k, None)
            vals[k] = "" if v is None else v
    vals["weight"] = vals["weight"] if edit or not src else src.weight  # a new entry starts from the last weight
    ctx.update({"edit": edit, "vals": vals, "form_height": ((edit.height_cm or last_h) if edit else last_h), "form_date": edit.date.isoformat() if edit else ctx["today"],
                "form_sex": u.sex})
    return render(request, "gym/tracker/progress.html", ctx)


@require_POST
@login_required
def progress_delete(request, pk):
    get_object_or_404(BodyLog, pk=pk, user=request.user).delete()
    return redirect("progress")


@require_POST
@login_required
def progress_weight(request):
    """Quick 'enter weight' (dashboard): only the weight; today's row is updated when it exists."""
    u = request.user
    try:
        w = tracker.dec(request.POST.get("weight"), 20, 400)
    except ValueError:
        w = None
    if w is None:
        flash(request, messages.ERROR, "ftr_err_range")
    else:
        today = timezone.localdate()
        before = _reached_goals(u)
        row = u.bodylogs.filter(date=today).order_by("-id").first()
        if row:
            row.weight = w
            row.save(update_fields=["weight"])
        else:
            BodyLog.objects.create(user=u, date=today, weight=w, height_cm=tracker.latest_height(u))
        flash(request, messages.SUCCESS, "weight_saved")
        _flash_goal_reached(request, u, before)
    return redirect(safe_next(request, "dashboard"))


@require_GET
@login_required
def progress_data(request):
    return JsonResponse(tracker.chart_data(request.user, request.GET.get("period", tracker.DEFAULT_PERIOD)))


@require_GET
@login_required
def progress_compare(request):
    today = timezone.localdate()
    a, b = _date_arg(request.GET.get("a")), _date_arg(request.GET.get("b"))
    if not a or not b or a > today or b > today:
        return JsonResponse({"ok": False, "error": translate(request.lang, "ftr_err_date")}, status=400)
    return JsonResponse({"ok": True, **tracker.compare(request.user, a, b)})


@require_GET
@login_required
def progress_export(request):
    kind = "workouts" if request.GET.get("kind") == "workouts" else "body"
    rows = tracker.workout_csv_rows(request.user) if kind == "workouts" else tracker.body_csv_rows(request.user)
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="fitnes-zal-{kind}-{request.user.member_code}.csv"'
    resp.write("﻿")  # Excel opens UTF-8 correctly with the BOM
    csv.writer(resp).writerows(rows)
    return resp


@require_POST
@login_required
def goal_save(request):
    g, err = tracker.save_goal(request.user, request.POST)
    flash(request, messages.ERROR if err else messages.SUCCESS, err or "goal_saved")
    return redirect("progress")


@require_POST
@login_required
def goal_delete(request, pk):
    g = get_object_or_404(TrackerGoal, pk=pk, user=request.user)
    if g.kind == "weight" and request.user.target_weight:
        request.user.target_weight = None
        request.user.save(update_fields=["target_weight"])
    g.delete()
    return redirect("progress")


# ---------------------------------------------------------------- workout log
def _report_records(request, records):
    if records:
        r = max(records, key=lambda x: x["one_rm"])
        flash(request, messages.SUCCESS, "ftr_pr_toast", celebrate=True, exercise=r["exercise"], value=r["one_rm"])


@login_required
def workouts_list(request):
    sessions = list(request.user.workout_sessions.prefetch_related("sets")[:60])
    items = []
    for s in sessions:
        groups = {}
        for st in s.sets.all():
            groups.setdefault(tracker.norm_name(st.exercise), {"name": st.exercise, "sets": []})["sets"].append(st)
        items.append({"s": s, "groups": list(groups.values()), "volume": s.volume})
    return render(request, "gym/tracker/workouts.html", {"items": items})


@login_required
def workout_add(request):
    u = request.user
    today = timezone.localdate()
    if request.method == "POST":
        day = _date_arg(request.POST.get("date"), today)
        rows, err = tracker.parse_sets(request.POST)
        pd = request.POST.get("plan_day", "")
        pd = int(pd) if pd.isdigit() and 0 <= int(pd) <= 6 else None
        if not err and not rows:
            err = "ftr_err_set"
        if not err and (day > today or day < date(2000, 1, 1)):
            err = "ftr_err_date"
        if err:
            flash(request, messages.ERROR, err)
            keys = ("name", "reps", "weight", "rpe", "snote")
            lists = {k: request.POST.getlist(k) for k in keys}
            posted_rows = [{k: (lists[k][i] if i < len(lists[k]) else "") for k in keys} for i in range(min(len(lists["name"]), tracker.MAX_ROWS))]
            return render(request, "gym/tracker/workout_form.html", {"today": today.isoformat(), "posted": {k: request.POST.get(k, "") for k in ("date", "plan_day", "note")}, "days": range(7), "posted_rows": posted_rows}, status=400)
        _s, recs = tracker.save_session(u, day, rows, plan_day=pd, note=request.POST.get("note", "").strip())
        flash(request, messages.SUCCESS, "ftr_session_saved")
        _report_records(request, recs)
        return redirect("workouts_log")
    return render(request, "gym/tracker/workout_form.html", {"today": today.isoformat(), "days": range(7), "posted": {"date": "", "plan_day": "", "note": ""}, "posted_rows": None})


@require_POST
@login_required
def workout_delete(request, pk):
    get_object_or_404(WorkoutSession, pk=pk, user=request.user).delete()
    return redirect("workouts_log")


@require_POST
@login_required
def workout_plan_log(request, pk):
    """The 'log sets' box under a plan exercise (today): replaces that exercise's sets in today's session and ticks it done."""
    from .models import Exercise
    ex = get_object_or_404(Exercise, pk=pk, plan__user=request.user)
    rows, err = tracker.parse_sets(request.POST)
    rows = [dict(r, name=ex.name) for r in rows]
    if err or not rows:
        flash(request, messages.ERROR, err or "ftr_err_set")
        return redirect("workouts")
    _s, recs = tracker.plan_log(request.user, ex, timezone.localdate(), rows)
    flash(request, messages.SUCCESS, "ftr_session_saved")
    _report_records(request, recs)
    return redirect("workouts")


@require_GET
@login_required
def exercise_suggest(request):
    return JsonResponse({"items": tracker.exercise_names(request.user, request.GET.get("q", ""), request.lang)})


# ---------------------------------------------------------------- trainer: a client's tracker, read-only
@trainer_required
def coach_tracker(request, uid):
    u = client_or_404(request.trainer, uid)
    ctx = _context(request, u, readonly=True, data_url=reverse("coach_tracker_data", args=[u.pk]),
                   compare_url=reverse("coach_tracker_compare", args=[u.pk]))
    ctx["sessions"] = list(u.workout_sessions.prefetch_related("sets")[:15])
    return render(request, "gym/coach/tracker.html", ctx)


@require_GET
@trainer_required
def coach_tracker_data(request, uid):
    u = client_or_404(request.trainer, uid)
    return JsonResponse(tracker.chart_data(u, request.GET.get("period", tracker.DEFAULT_PERIOD)))


@require_GET
@trainer_required
def coach_tracker_compare(request, uid):
    u = client_or_404(request.trainer, uid)
    today = timezone.localdate()
    a, b = _date_arg(request.GET.get("a")), _date_arg(request.GET.get("b"))
    if not a or not b or a > today or b > today:
        return JsonResponse({"ok": False, "error": translate(request.lang, "ftr_err_date")}, status=400)
    return JsonResponse({"ok": True, **tracker.compare(u, a, b)})
