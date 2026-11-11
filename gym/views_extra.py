"""Pages of the retention features (membership hub with freeze and guest passes, waitlist, calendar, gifts, FAQ, legal pages, trainer
ratings, account deletion, desk attendance). The older pages that gained a feature (plans, classes, dashboard, scan...) are in views.py."""
from datetime import timedelta

import segno
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST

from . import click, extras, services, telegram
from django.core.paginator import Paginator

from .models import Booking, ClassWaitlist, GiftCertificate, GuestPass, GymClass, GymSettings, MembershipFreeze, Plan, ReferralReward, Trainer, User
from .views import allowed_methods, flash, local_back, rl_check, rl_fail, safe_date, staff_required, verify_gate


def _qr(code):
    return mark_safe(segno.make(code, error="m").svg_inline(scale=6, border=2, dark="#111111", light="#ffffff"))


def _int(text, default=0):
    try:
        return int(str(text).strip())
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------- 1. membership hub: freeze, renew, guest passes, invites
@login_required
def membership_view(request):
    u = request.user
    info = extras.freeze_info(u)
    m, allowed, used = extras.guest_quota(u)
    passes = [{"gp": gp, "code": extras.guest_code(gp), "url": request.build_absolute_uri(reverse("guest_public", args=[extras.guest_code(gp)]))}
              for gp in u.guest_passes.all()[:30]]
    today = timezone.localdate()
    last_day = (extras._local_date(m.expires) - timedelta(days=1)) if m else today
    rewards = ReferralReward.objects.filter(referrer=u)
    return render(request, "gym/membership.html", {
        "fz": info, "m": m, "freezes": [f for f in MembershipFreeze.objects.filter(membership__user=u).select_related("membership")[:10] if f.days],
        "g_allowed": allowed, "g_used": used, "g_left": max(0, allowed - used), "passes": passes, "today": today, "last_day": last_day,
        "renew_plan": extras.renew_plan(u), "can_enter": services.can_enter(u),
        "referral_url": request.build_absolute_uri(reverse("register")) + f"?ref={u.referral_code}",
        "invited": u.referrals.count(), "rewarded": rewards.count(), "earned_days": rewards.aggregate(s=Sum("days"))["s"] or 0,
        "bonus_days": GymSettings.load().referral_bonus_days,
    })


@require_POST
@login_required
def freeze_view(request):
    start = safe_date(request.POST.get("start")) if request.POST.get("start") else None
    f, err = extras.start_freeze(request.user, _int(request.POST.get("days")), start)
    info = extras.freeze_info(request.user)
    kw = {"min": info["min"], "max": info["max"], "left": info["left"]}
    if f:
        flash(request, messages.SUCCESS, "freeze_ok_future" if f.start_date > timezone.localdate() else "freeze_ok", date=f"{f.start_date:%d.%m.%Y}",
              until=f"{f.end_date:%d.%m.%Y}", **kw)
    else:
        flash(request, messages.ERROR, err, **kw)
    return redirect(local_back(request, "membership"))


@require_POST
@login_required
def unfreeze_view(request):
    days, err = extras.end_freeze(request.user)
    if err:
        flash(request, messages.ERROR, err)
    else:
        flash(request, messages.SUCCESS, "unfreeze_ok", n=days)
    return redirect(local_back(request, "membership"))


@login_required
def renew_view(request):
    """One click from a reminder or the dashboard: the same plan, straight to the usual payment form."""
    plan = extras.renew_plan(request.user)
    if not plan:
        return redirect("plans")
    return redirect(f"{reverse('plans')}?renew={plan.code}#plan-{plan.code}")


# ---------------------------------------------------------------- 3. guest passes
@require_POST
@login_required
def guest_create(request):
    gp, err = extras.create_guest_pass(request.user, request.POST.get("name"), request.POST.get("phone"), safe_date(request.POST.get("date")))
    if err:
        flash(request, messages.ERROR, err)
    else:
        flash(request, messages.SUCCESS, "gp_created")
    return redirect("/membership/#guests")


@require_POST
@login_required
def guest_cancel(request, pk):
    if extras.cancel_guest_pass(request.user, pk):
        flash(request, messages.SUCCESS, "gp_cancelled_ok")
    return redirect("/membership/#guests")


def guest_public(request, code):
    """The page the member sends to the friend: who invited, the date, the one-time QR. No sign-in needed; the code is signed."""
    gp = extras.guest_from_code(code)
    if not gp:
        raise Http404()
    return render(request, "gym/guest_pass.html", {"gp": gp, "code": extras.guest_code(gp), "qr": _qr(extras.guest_code(gp)), "host": gp.owner})


# ---------------------------------------------------------------- 5. waitlist
@require_POST
@login_required
def waitlist_join(request, pk):
    gate = verify_gate(request)
    if gate:
        return gate
    c = get_object_or_404(GymClass, pk=pk, active=True)
    pos, err = extras.join_waitlist(request.user, c, c.next_date())
    if err:
        flash(request, messages.ERROR, err)
    else:
        flash(request, messages.SUCCESS, "wl_joined", n=pos)
    return redirect("classes")


@require_POST
@login_required
def waitlist_leave(request, pk):
    c = get_object_or_404(GymClass, pk=pk)
    extras.leave_waitlist(request.user, c, c.next_date())
    flash(request, messages.SUCCESS, "wl_left")
    return redirect("classes")


# ---------------------------------------------------------------- 6. trainer rating
@require_POST
@login_required
def trainer_rate(request, pk):
    tr = get_object_or_404(Trainer, pk=pk, active=True)
    review, err = extras.rate_trainer(request.user, tr, _int(request.POST.get("rating")), request.POST.get("comment"))
    flash(request, messages.ERROR if err else messages.SUCCESS, err or "tr_rate_ok")
    return redirect("trainer", pk=tr.pk)


# ---------------------------------------------------------------- 7. leaderboard opt-in
@require_POST
@login_required
def leaderboard_optin(request):
    on = request.POST.get("on") == "1"
    User.objects.filter(pk=request.user.pk).update(show_in_leaderboard=on)
    flash(request, messages.SUCCESS, "board_joined" if on else "board_left")
    return redirect("achievements")


# ---------------------------------------------------------------- 8. gift certificates
@login_required
def gift_view(request):
    gifts = [{"g": g, "state": g.state} for g in GiftCertificate.objects.filter(buyer=request.user).select_related("plan", "payment")[:20]]
    gs = GymSettings.load()
    return render(request, "gym/gift.html", {"plans": Plan.objects.filter(active=True), "methods": allowed_methods(gs), "gifts": gifts,
                                             "min": extras.GIFT_MIN, "max": extras.GIFT_MAX, "plans_json": {p.code: p.price for p in Plan.objects.filter(active=True)}})


@require_POST
@login_required
def gift_buy(request):
    gate = verify_gate(request)
    if gate:
        return gate
    method = request.POST.get("method")
    if method not in allowed_methods(GymSettings.load()):
        flash(request, messages.ERROR, "err_method")
        return redirect("gift")
    if not extras.consent_given(request):
        flash(request, messages.ERROR, "err_consent")
        return redirect("gift")
    plan = Plan.objects.filter(code=request.POST.get("plan"), active=True).first() if request.POST.get("plan") else None
    pay, gift, err = extras.buy_gift(request.user, plan, _int(request.POST.get("amount")), method)
    if err:
        flash(request, messages.ERROR, err)
        return redirect("gift")
    extras.stamp_consent(request.user, type(pay).objects.filter(pk=pay.pk))
    if method == "click":
        return redirect(click.pay_url(pay, request.build_absolute_uri(reverse("gift"))))
    if method == "card":
        return redirect("pay", pk=pay.pk)
    if pay.status == pay.Status.PENDING:
        telegram.alert_admin(f"Sovg'a sertifikati (tasdiq kutadi): {request.user.full_name} · {pay.amount} so'm")
    flash(request, messages.SUCCESS, "gift_bought_pending" if pay.status == pay.Status.PENDING else "gift_bought")
    return redirect("gift")


@require_POST
@login_required
def gift_redeem(request):
    key = f"rl:gift:{request.user.pk}"
    if not rl_check(key):
        flash(request, messages.ERROR, "err_rate")
        return redirect("gift")
    g = extras.find_gift(request.POST.get("code"))
    err = extras.gift_error(g)
    if err:
        rl_fail(key)
        flash(request, messages.ERROR, err)
    elif not g.plan_id:
        flash(request, messages.INFO, "gift_amount_ok", amount=f"{g.amount:,}".replace(",", " "), code=g.code)
    else:
        with transaction.atomic():
            m, err = extras.redeem_gift_plan(request.user, g)
        flash(request, messages.ERROR if err else messages.SUCCESS, err or "gift_redeemed", celebrate=not err)
    return redirect("gift")


# ---------------------------------------------------------------- 9. calendar
@login_required
def booking_ics(request, pk):
    b = get_object_or_404(Booking.objects.select_related("gym_class", "gym_class__trainer"), pk=pk, user=request.user)
    resp = HttpResponse(extras.ics_calendar([b], b.gym_class.name), content_type="text/calendar; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="class-{b.pk}.ics"'
    return resp


def calendar_feed(request, token):
    """The member's personal subscription: every booked class from last week on. The secret token in the address is the only key."""
    if len(token) < 20:
        raise Http404()
    u = User.objects.filter(calendar_token=token, is_active=True).first()
    if not u:
        raise Http404()
    since = timezone.localdate() - timedelta(days=7)
    rows = Booking.objects.filter(user=u, date__gte=since).select_related("gym_class", "gym_class__trainer").order_by("date")
    resp = HttpResponse(extras.ics_calendar(rows, "Fitnes Zal"), content_type="text/calendar; charset=utf-8")
    resp["Cache-Control"] = "private, max-age=600"
    return resp


@require_POST
@login_required
def calendar_reset(request):
    extras.rotate_calendar_token(request.user)
    flash(request, messages.SUCCESS, "cal_reset_ok")
    return redirect("classes")


# ---------------------------------------------------------------- 10-11. FAQ, legal pages
def faq_view(request):
    return render(request, "gym/faq.html", {"items": extras.faq_items(request.lang)})


def legal_view(request, slug):
    page = extras.get_legal(slug)
    if not page:
        raise Http404()
    return render(request, "gym/legal.html", {"page": page, "title": page.title(request.lang), "body": page.body(request.lang), "slug": slug})


@require_POST
@login_required
def account_delete(request):
    """Soft delete: after the password (or, for Google/Apple accounts without one, the member code) is confirmed the account is deactivated
    and anonymised; payments and orders stay for the books."""
    u = request.user
    key = f"rl:del:{u.pk}"
    if u.is_staff or u.is_superuser:
        flash(request, messages.ERROR, "del_staff")
        return redirect("profile")
    if not rl_check(key):
        flash(request, messages.ERROR, "err_rate")
        return redirect("profile")
    typed = request.POST.get("password", "")
    ok = u.check_password(typed) if u.has_usable_password() else typed.strip().upper() == u.member_code
    if not (ok and request.POST.get("sure")):
        rl_fail(key)
        flash(request, messages.ERROR, "del_wrong")
        return redirect("/profile/#security")
    from django.contrib.auth import logout
    extras.anonymize_user(u)
    logout(request)
    flash(request, messages.SUCCESS, "del_done")
    return redirect("home")


@login_required
def entry_history_view(request):
    """The member's own entries: date, time, way in. Thirty to a page, plus the count for the current month."""
    rows = extras.entry_history(request.user).select_related("guest_pass")
    today = timezone.localdate()
    month = rows.filter(ts__year=today.year, ts__month=today.month, result="ok").count()
    page = Paginator(rows, 30).get_page(request.GET.get("page"))
    return render(request, "gym/entries.html", {"page": page, "month": month, "total": rows.filter(result="ok").count()})
