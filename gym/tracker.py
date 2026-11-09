"""Fitness tracker logic (no views): body fat, Epley 1RM, trend / goal projection, saving workout sessions with personal-record
detection, the chart data behind /progress/, before/after comparison and CSV rows. Everything is computed for one member."""
import math
import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from .models import BodyLog, ExerciseLog, FoodEntry, PersonalRecord, User
from .models_tracker import TrackerGoal, WorkoutSession, WorkoutSet

PERIODS = {"1m": 30, "3m": 90, "6m": 180, "1y": 365, "all": None}
DEFAULT_PERIOD = "3m"
MEASURES = BodyLog.CIRCUMFERENCES  # waist, chest, hips, neck, arm, thigh, calf (cm)
COMPARE_KEYS = ["weight", "bmi", "body_fat"] + MEASURES + ["resting_hr"]
GOAL_MEASURES = MEASURES + ["body_fat"]
TREND_DAYS = 28  # the weight trend (and the projected date) uses the last four weeks
MAX_ROWS, MAX_ROW_LEN = 120, 80


# ---------------------------------------------------------------- small math
def epley(weight, reps):
    """Estimated one-rep max (Epley): w * (1 + reps / 30); a single rep is the weight itself."""
    w = float(weight)
    return round(w if reps == 1 else w * (1 + reps / 30), 1)


def navy_body_fat(sex, height_cm, waist, neck, hips=None):
    """US Navy body-fat estimate in % (all lengths in cm), or None when the numbers do not make sense."""
    try:
        h, w, n = float(height_cm), float(waist), float(neck)
        if sex == "m":
            diff = w - n
            if diff <= 0:
                return None
            val = 495 / (1.0324 - 0.19077 * math.log10(diff) + 0.15456 * math.log10(h)) - 450
        elif sex == "f":
            if not hips:
                return None
            diff = w + float(hips) - n
            if diff <= 0:
                return None
            val = 495 / (1.29579 - 0.35004 * math.log10(diff) + 0.22100 * math.log10(h)) - 450
        else:
            return None
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    return round(val, 1) if 2 <= val <= 75 else None


def linreg(points):
    """Least-squares line through [(date, value)]: (slope per day, mean x as ordinal, mean y), or None for fewer than 2 distinct days."""
    pts = [(d.toordinal(), float(v)) for d, v in points]
    n = len(pts)
    if n < 2:
        return None
    mx, my = sum(x for x, _ in pts) / n, sum(y for _, y in pts) / n
    den = sum((x - mx) ** 2 for x, _ in pts)
    if den == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in pts) / den, mx, my


def moving_average(points, days=7):
    """[(date, value)] -> [(date, mean of the values within the last `days` days up to that date)]."""
    out = []
    for i, (d, _) in enumerate(points):
        win = [float(v) for dd, v in points[: i + 1] if (d - dd).days < days]
        out.append((d, round(sum(win) / len(win), 2)))
    return out


def goal_progress(points, target, start=None, target_date=None, today=None, window=TREND_DAYS):
    """Where a member stands against a goal. `points` = [(date, value)] oldest first. Returns a dict with the current value, the
    remaining amount, the progress bar percent, the trend per week (linear regression over the last `window` days), the projected date
    of reaching the target and `state`: nodata | reached | on_track | off_track | no_trend."""
    today = today or timezone.localdate()
    target = float(target)
    if not points:
        return {"state": "nodata", "target": target, "pct": 0, "remaining": None, "current": None, "start": None, "projected": None, "per_week": None}
    cur = float(points[-1][1])
    start = float(start) if start is not None else float(points[0][1])
    up = target >= start
    reached = cur >= target if up else cur <= target
    total = target - start
    pct = 100 if reached else (max(0, min(100, round((cur - start) / total * 100))) if total else 0)
    recent = [(d, v) for d, v in points if (today - d).days <= window]
    fit = linreg(recent) if len(recent) >= 2 and (recent[-1][0] - recent[0][0]).days >= 3 else None
    slope = fit[0] if fit else None
    need = target - cur
    projected = None
    if slope and slope * need > 0:
        days = need / slope
        if days <= 3650:
            projected = today + timedelta(days=math.ceil(round(days, 6)))
    if reached:
        state = "reached"
    elif slope is None:
        state = "no_trend"
    elif projected and (target_date is None or projected <= target_date):
        state = "on_track"
    else:
        state = "off_track"
    return {"state": state, "target": target, "current": cur, "start": start, "pct": pct, "remaining": round(abs(need), 1) if not reached else 0,
            "per_week": round(slope * 7, 2) if slope is not None else None, "projected": projected}


# ---------------------------------------------------------------- exercise names -> the six personal-record lifts
LIFT_WORDS = [
    ("pullup", ("pull-up", "pull up", "pullup", "chin-up", "chin up", "turnik", "tortilish", "подтягив")),
    ("deadlift", ("deadlift", "stanovoy", "становая", "румын")),
    ("squat", ("squat", "o'tirib tur", "otirib tur", "присед")),
    ("ohp", ("overhead press", "military press", "shoulder press", "ohp", "yelka", "жим стоя", "жим над головой", "армейский")),
    ("row", ("barbell row", "bent-over row", "bent over row", "shtanga bilan eshkak", "тяга штанги в наклоне", "тяга в наклоне", "row")),
    ("bench", ("bench press", "bench", "jim yotib", "yotib itarish", "жим лёжа", "жим лежа")),
]


def norm_name(name):
    return re.sub(r"\s+", " ", (name or "").strip()).lower()


def lift_for(name):
    """The PersonalRecord lift key an exercise name stands for (bench, squat, ...), or None."""
    n = norm_name(name)
    if not n:
        return None
    for key, words in LIFT_WORDS:
        if any(w in n for w in words):
            if key == "squat" and ("split" in n or "bulgar" in n or "goblet" in n):
                continue
            return key
    return None


# ---------------------------------------------------------------- body logs
def dec(raw, lo, hi, places=1):
    """Decimal from user text ('72,5'), None when empty; raises ValueError when not a number or outside [lo, hi]."""
    s = str(raw if raw is not None else "").replace(",", ".").strip()
    if not s:
        return None
    try:
        d = Decimal(s)
    except InvalidOperation:
        raise ValueError("bad")
    if not d.is_finite() or not (Decimal(str(lo)) <= d <= Decimal(str(hi))):
        raise ValueError("range")
    return d.quantize(Decimal(1).scaleb(-places))


def latest_height(user, upto=None):
    qs = user.bodylogs.exclude(height_cm=None)
    if upto:
        qs = qs.filter(date__lte=upto)
    h = qs.order_by("-date", "-id").first()
    return h.height_cm if h else None


def auto_body_fat(user, log):
    """Fills log.body_fat from the US Navy formula when it is empty and the sex, height, waist and neck (hips for women) are known."""
    if log.body_fat is not None or not user.sex or not (log.waist and log.neck):
        return
    h = log.height_cm or latest_height(user, log.date)
    bf = navy_body_fat(user.sex, h, log.waist, log.neck, log.hips) if h else None
    if bf is not None:
        log.body_fat = Decimal(str(bf))


def save_body_entry(user, data, pk=None):
    """Validates the quick-entry form (`data` is request.POST) and saves it. One row per day: saving a date again updates that row.
    Returns (log, error_key); error_key is an i18n key or None."""
    try:
        day = date.fromisoformat((data.get("date") or "").strip() or timezone.localdate().isoformat())
        weight = dec(data.get("weight"), 20, 400)
        height = data.get("height_cm", "")
        height = int(str(height).strip()) if str(height).strip() else None
        fields = {k: dec(data.get(k), *r) for k, r in {"waist": (40, 250), "chest": (50, 250), "hips": (50, 250), "neck": (20, 80), "arm": (10, 80),
                                                       "thigh": (25, 130), "calf": (15, 80), "body_fat": (2, 75)}.items()}
        hr = str(data.get("resting_hr", "")).strip()
        hr = int(hr) if hr else None
    except (ValueError, TypeError):
        return None, "ftr_err_range"
    if weight is None:
        return None, "err_fields"
    if height is not None and not 100 <= height <= 250:
        return None, "ftr_err_range"
    if hr is not None and not 30 <= hr <= 220:
        return None, "ftr_err_range"
    if day > timezone.localdate() or day < date(2000, 1, 1):
        return None, "ftr_err_date"
    sex = (data.get("sex") or "").strip()
    note = (data.get("note") or "").strip()[:120]
    with transaction.atomic():
        log = BodyLog.objects.filter(pk=pk, user=user).first() if pk else None
        if pk and not log:
            return None, "ftr_err_notfound"
        if not log:
            log = user.bodylogs.filter(date=day).order_by("-id").first() or BodyLog(user=user)
        if sex in ("m", "f") and user.sex != sex:
            user.sex = sex
            user.save(update_fields=["sex"])
        log.date, log.weight, log.height_cm, log.note, log.resting_hr = day, weight, height or log.height_cm or latest_height(user, day), note, hr
        for k, v in fields.items():
            setattr(log, k, v)
        auto_body_fat(user, log)
        log.save()
    return log, None


# ---------------------------------------------------------------- workout sessions
def parse_sets(post):
    """Rows posted by the workout forms (parallel lists name / reps / weight / rpe / note). Returns (rows, error_key). A row with
    nothing in it is skipped; a half-filled or out-of-range row is an error (nothing is saved then)."""
    names, reps, weights = post.getlist("name"), post.getlist("reps"), post.getlist("weight")
    rpes, notes = post.getlist("rpe"), post.getlist("snote")
    rows = []
    for i, name in enumerate(names[:MAX_ROWS]):
        name = re.sub(r"\s+", " ", name.strip())
        r = reps[i].strip() if i < len(reps) else ""
        w = weights[i].strip() if i < len(weights) else ""
        rp = rpes[i].strip() if i < len(rpes) else ""
        if not r and not w and not rp:
            continue  # an empty set line
        try:
            if not name or len(name) > MAX_ROW_LEN:
                raise ValueError
            reps_i = int(r)
            if not 1 <= reps_i <= 100:
                raise ValueError
            weight = dec(w, 0, 500) or Decimal("0.0")
            rpe = dec(rp, 1, 10)
        except (ValueError, TypeError):
            return [], "ftr_err_set"
        rows.append({"name": name, "reps": reps_i, "weight": weight, "rpe": rpe, "note": (notes[i].strip()[:120] if i < len(notes) else "")})
    return rows, None


def _best_by_exercise(rows):
    best = {}
    for r in rows:
        if r["weight"] <= 0:
            continue
        k = norm_name(r["name"])
        v = epley(r["weight"], r["reps"])
        if k not in best or v > best[k][0]:
            best[k] = (v, r)
    return best


@transaction.atomic
def save_session(user, day, rows, plan_day=None, note="", session=None, replace_exercise=None):
    """Stores sets in a session and detects new personal records. With `replace_exercise` only the sets of that exercise in the
    session are replaced (the 'log sets' box under a plan exercise). Returns (session, records) where records =
    [{"exercise", "one_rm", "prev"}] for every exercise whose estimated 1RM beat everything logged before."""
    if session is None:
        session = WorkoutSession.objects.create(user=user, date=day, plan_day=plan_day, note=note[:200])
    else:
        if note:
            session.note = note[:200]
            session.save(update_fields=["note"])
    if replace_exercise:
        session.sets.filter(exercise__iexact=replace_exercise).delete()
    # the best earlier estimate per exercise, taken BEFORE the new sets go in
    best_new = _best_by_exercise(rows)
    prior = {}
    for ex, w, r in WorkoutSet.objects.filter(session__user=user).exclude(session=session).values_list("exercise", "weight", "reps"):
        if w > 0:
            k = norm_name(ex)
            prior[k] = max(prior.get(k, 0), epley(w, r))
    order = session.sets.count()
    WorkoutSet.objects.bulk_create([WorkoutSet(session=session, exercise=r["name"], order=order + i, reps=r["reps"], weight=r["weight"], rpe=r["rpe"], note=r["note"])
                                    for i, r in enumerate(rows)])
    records, seen = [], set()
    lifts = {}
    for k, (val, r) in best_new.items():
        prev = prior.get(k)
        lift = lift_for(r["name"])
        if lift:
            lifts[lift] = max(lifts.get(lift, (0, None)), (val, r), key=lambda t: t[0])
        if prev is not None and val > prev:
            records.append({"exercise": r["name"], "one_rm": val, "prev": prev})
            seen.add(k)
    # PersonalRecord (the records page): a lift's best estimate is stored when it beats every stored record of that lift
    for lift, (val, r) in lifts.items():
        old = max((x.one_rm for x in PersonalRecord.objects.filter(user=user, lift=lift)), default=None)
        if (old is None or val > old) and r["reps"] <= 30:
            PersonalRecord.objects.create(user=user, lift=lift, weight=r["weight"], reps=r["reps"], date=day)
            if old is not None and norm_name(r["name"]) not in seen:
                records.append({"exercise": r["name"], "one_rm": val, "prev": old})
    return session, records


def plan_log(user, ex, day, rows):
    """Logs sets for one plan exercise `ex` on `day`, marks the exercise done and returns (session, records)."""
    sess = WorkoutSession.objects.filter(user=user, date=day, plan_day=ex.weekday).order_by("id").first()
    sess, recs = save_session(user, day, rows, plan_day=ex.weekday, session=sess, replace_exercise=ex.name)
    ExerciseLog.objects.get_or_create(user=user, exercise=ex, date=day)
    return sess, recs


def exercise_names(user, q="", lang="uz", limit=20):
    """Autocomplete: the member's plan exercises, what they logged before and the ready-made programs' exercises matching `q`."""
    from . import programs as P
    from .models import Exercise
    q = norm_name(q)
    seen, out = set(), []

    def add(n):
        k = norm_name(n)
        if k and k not in seen and (not q or q in k):
            seen.add(k)
            out.append(n)
    for n in Exercise.objects.filter(plan__user=user).values_list("name", flat=True).distinct():
        add(n)
    for n in WorkoutSet.objects.filter(session__user=user).values_list("exercise", flat=True).distinct()[:300]:
        add(n)
    for prog in P.PROGRAMS.values():
        for _wd, n, *_ in P.rows(prog, lang):
            add(n)
    return out[:limit]


# ---------------------------------------------------------------- chart data
def period_start(period, today=None):
    today = today or timezone.localdate()
    days = PERIODS.get(period, PERIODS[DEFAULT_PERIOD])
    return today - timedelta(days=days) if days else None


def _pts(points):
    return [{"d": d.isoformat(), "v": round(float(v), 2)} for d, v in points]


def _weeks(start, today):
    monday = today - timedelta(days=today.weekday())
    first = start - timedelta(days=start.weekday())
    first = max(first, monday - timedelta(days=7 * 103))
    out, w = [], first
    while w <= monday:
        out.append(w)
        w += timedelta(days=7)
    return out


def weight_points(user, since=None):
    qs = user.bodylogs.order_by("date", "id")
    if since:
        qs = qs.filter(date__gte=since)
    by_day = {}
    for l in qs:
        by_day[l.date] = l.weight  # the last entry of a day wins
    return sorted(by_day.items())


def weight_goal(user):
    """(TrackerGoal or None, target, target_date, start_value) for the weight goal; the profile's target weight counts when no goal row exists."""
    g = user.tracker_goals.filter(kind=TrackerGoal.Kind.WEIGHT).first()
    if g:
        return g, float(g.target), g.target_date, g.start_value
    if user.target_weight:
        return None, float(user.target_weight), None, None
    return None, None, None, None


def chart_data(user, period=DEFAULT_PERIOD, today=None):
    from . import calories, extras, services
    today = today or timezone.localdate()
    period = period if period in PERIODS else DEFAULT_PERIOD
    since = period_start(period, today)
    out = {"period": period, "from": since.isoformat() if since else None, "to": today.isoformat()}

    # weight: points, 7-day moving average, goal line, projection
    all_w = weight_points(user)
    shown = [(d, v) for d, v in all_w if not since or d >= since]
    ma = moving_average(all_w)
    ma = [(d, v) for d, v in ma if not since or d >= since]
    _g, target, target_date, start_v = weight_goal(user)
    proj = None
    if target is not None and all_w:
        gp = goal_progress(all_w, target, start_v, target_date, today)
        if gp["projected"]:
            proj = {"d0": all_w[-1][0].isoformat(), "v0": float(all_w[-1][1]), "d1": gp["projected"].isoformat(), "v1": target}
    out["weight"] = {"points": _pts(shown), "ma": _pts(ma), "unit": "kg", "projection": proj,
                     "goal": {"target": target, "date": target_date.isoformat() if target_date else None} if target is not None else None}

    # measurements and body fat
    logs = list(user.bodylogs.filter(date__gte=since) if since else user.bodylogs.all())
    series = {}
    for k in MEASURES:
        pts = [(l.date, getattr(l, k)) for l in logs if getattr(l, k) is not None]
        if pts:
            series[k] = _pts(pts)
    out["measures"] = {"series": series, "unit": "cm"}
    out["body_fat"] = {"points": _pts([(l.date, l.body_fat) for l in logs if l.body_fat is not None]), "unit": "%"}
    out["resting_hr"] = {"points": _pts([(l.date, l.resting_hr) for l in logs if l.resting_hr is not None]), "unit": "bpm"}

    # workouts: strength per exercise, weekly volume, workouts per week
    sets = WorkoutSet.objects.filter(session__user=user)
    if since:
        sets = sets.filter(session__date__gte=since)
    rows = list(sets.values_list("session_id", "session__date", "exercise", "weight", "reps"))
    per_ex, names, vol_w, sess_w = {}, {}, {}, {}
    for sid, d, ex, w, r in rows:
        k = norm_name(ex)
        names.setdefault(k, ex)
        wk = d - timedelta(days=d.weekday())
        vol_w[wk] = vol_w.get(wk, 0) + float(w) * r
        sess_w.setdefault(wk, set()).add(sid)
        if w > 0:
            cur = per_ex.setdefault(k, {})
            cur[d] = max(cur.get(d, 0), epley(w, r))
    strength = {names[k]: _pts(sorted(v.items())) for k, v in per_ex.items()}
    lift_has = {lift_for(n) for n in strength} - {None}
    prs = PersonalRecord.objects.filter(user=user, date__gte=since) if since else PersonalRecord.objects.filter(user=user)
    by_lift = {}
    for r in prs:
        if r.lift not in lift_has:
            cur = by_lift.setdefault(r.lift, {})
            cur[r.date] = max(cur.get(r.date, 0), r.one_rm)
    for lift, v in by_lift.items():
        strength[dict(PersonalRecord.LIFTS)[lift].split(" (")[0]] = _pts(sorted(v.items()))
    order = sorted(strength, key=lambda n: -len(strength[n]))[:30]
    out["strength"] = {"exercises": order, "series": {n: strength[n] for n in order}, "unit": "kg"}

    first = since or min([d for d, _ in all_w] + [r[1] for r in rows] + [today - timedelta(days=84)])
    weeks = _weeks(first, today)
    vdays = services.visit_days(user)
    visits_w = {}
    for d in vdays:
        wk = d - timedelta(days=d.weekday())
        visits_w[wk] = visits_w.get(wk, 0) + 1
    out["volume"] = [{"w": w.isoformat(), "v": round(vol_w.get(w, 0))} for w in weeks]
    out["activity"] = [{"w": w.isoformat(), "workouts": len(sess_w.get(w, ())), "visits": visits_w.get(w, 0)} for w in weeks]

    # calories vs target
    cstart = since or today - timedelta(days=365)
    kcal = {}
    for d, k in FoodEntry.objects.filter(user=user, date__gte=cstart).values_list("date", "kcal"):
        kcal[d] = kcal.get(d, 0) + float(k)
    ctarget = calories.daily_target(user)[0]
    within = sum(1 for v in kcal.values() if abs(v - ctarget) <= ctarget * 0.1)
    out["calories"] = {"days": [{"d": d.isoformat(), "kcal": round(v), "target": ctarget} for d, v in sorted(kcal.items())], "target": ctarget,
                       "logged_days": len(kcal), "within_days": within, "adherence": round(within * 100 / len(kcal)) if kcal else None}

    wk = extras.weekly_streak(user)
    out["streak"] = {"days": services.visit_stats(user)["streak"], "weeks": wk["weeks"], "this_week": wk["this_week"], "need": wk["need"]}
    return out


# ---------------------------------------------------------------- goals
def goal_series(user, g):
    """[(date, value)] the progress of a goal is measured on."""
    if g.kind == TrackerGoal.Kind.WEIGHT:
        return weight_points(user)
    if g.kind == TrackerGoal.Kind.MEASURE:
        return [(l.date, getattr(l, g.metric)) for l in user.bodylogs.order_by("date", "id") if getattr(l, g.metric, None) is not None]
    best = {}
    k = norm_name(g.metric)
    for d, ex, w, r in WorkoutSet.objects.filter(session__user=user, weight__gt=0).values_list("session__date", "exercise", "weight", "reps"):
        if norm_name(ex) == k:
            best[d] = max(best.get(d, 0), epley(w, r))
    lift = lift_for(g.metric)
    if lift:
        for r in PersonalRecord.objects.filter(user=user, lift=lift):
            best[r.date] = max(best.get(r.date, 0), r.one_rm)
    return sorted(best.items())


def goals_overview(user, today=None):
    """One dict per goal (the weight goal first) with its progress; the profile's target weight shows as a weight goal without a date."""
    today = today or timezone.localdate()
    out = []
    goals = list(user.tracker_goals.all())
    if not any(g.kind == TrackerGoal.Kind.WEIGHT for g in goals) and user.target_weight:
        goals.insert(0, TrackerGoal(user=user, kind="weight", metric="weight", target=user.target_weight))
    for g in sorted(goals, key=lambda g: (g.kind != "weight", g.kind, g.metric)):
        pts = goal_series(user, g)
        p = goal_progress(pts, g.target, g.start_value, g.target_date, today, window=TREND_DAYS if g.kind != "strength" else 90)
        p.update(pk=g.pk, kind=g.kind, metric=g.metric, target_date=g.target_date, saved=g.pk is not None)
        out.append(p)
    return out


def save_goal(user, data):
    """Creates or updates a goal from the form. Returns (goal, error_key)."""
    kind = data.get("kind", "")
    metric = (data.get("metric") or "").strip()[:80]
    try:
        target = dec(data.get("target"), 0.5, 1000)
        td = data.get("target_date", "").strip()
        target_date = date.fromisoformat(td) if td else None
    except ValueError:
        return None, "ftr_err_range"
    if target is None:
        return None, "err_fields"
    if kind == "weight":
        metric = "weight"
        if not Decimal("30") <= target <= Decimal("250"):
            return None, "ftr_err_range"
    elif kind == "measure":
        if metric not in GOAL_MEASURES:
            return None, "ftr_err_range"
    elif kind == "strength":
        if not metric:
            return None, "err_fields"
    else:
        return None, "ftr_err_range"
    if target_date and target_date <= timezone.localdate():
        return None, "ftr_err_date"
    with transaction.atomic():
        g = user.tracker_goals.filter(kind=kind, metric=metric).first() or TrackerGoal(user=user, kind=kind, metric=metric)
        restart = g.pk is None or g.target != target
        g.target, g.target_date = target, target_date
        if restart:
            pts = goal_series(user, g)
            g.start_value = Decimal(str(pts[-1][1])).quantize(Decimal("0.1")) if pts else None
            g.start_date = timezone.localdate()
        g.save()
        if kind == "weight":
            user.target_weight = target
            user.save(update_fields=["target_weight"])
    return g, None


# ---------------------------------------------------------------- before / after
def _value_at(logs, key, d):
    """The value of `key` from the latest entry on or before `d` (else the first one after it), or None."""
    have = [l for l in logs if getattr(l, key, None) is not None]
    before = [l for l in have if l.date <= d]
    pick = before[-1] if before else (have[0] if have else None)
    return getattr(pick, key) if pick else None


def compare(user, a, b):
    """Differences between the states on two dates: weight, BMI, body fat, each measurement and the resting pulse."""
    logs = list(user.bodylogs.order_by("date", "id"))
    rows = []
    for key in COMPARE_KEYS:
        if key == "bmi":
            vals = []
            for d in (a, b):
                w, h = _value_at(logs, "weight", d), _value_at(logs, "height_cm", d)
                vals.append(round(float(w) / ((h / 100) ** 2), 1) if w is not None and h else None)
        else:
            vals = [_value_at(logs, key, d) for d in (a, b)]
            vals = [float(v) if v is not None else None for v in vals]
        va, vb = vals
        rows.append({"key": key, "a": va, "b": vb, "diff": round(vb - va, 1) if va is not None and vb is not None else None})
    return {"a": a.isoformat(), "b": b.isoformat(), "rows": rows}


# ---------------------------------------------------------------- CSV
def csv_safe(v):
    """A text cell that a spreadsheet would run as a formula gets a leading apostrophe (CSV injection)."""
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


def body_csv_rows(user):
    head = ["date", "weight_kg", "height_cm", "bmi"] + [f"{k}_cm" for k in MEASURES] + ["body_fat_pct", "resting_hr", "note"]
    rows = [head]
    for l in user.bodylogs.order_by("date", "id"):
        rows.append([l.date.isoformat(), l.weight, l.height_cm or "", l.bmi or ""] + [getattr(l, k) if getattr(l, k) is not None else "" for k in MEASURES]
                    + [l.body_fat if l.body_fat is not None else "", l.resting_hr or "", csv_safe(l.note)])
    return rows


def workout_csv_rows(user):
    rows = [["date", "plan_day", "exercise", "set", "reps", "weight_kg", "rpe", "est_1rm_kg", "set_note", "session_note"]]
    for s in user.workout_sessions.order_by("date", "id").prefetch_related("sets"):
        counter = {}
        for st in s.sets.all():
            k = norm_name(st.exercise)
            counter[k] = counter.get(k, 0) + 1
            rows.append([s.date.isoformat(), "" if s.plan_day is None else s.plan_day, csv_safe(st.exercise), counter[k], st.reps, st.weight,
                         st.rpe if st.rpe is not None else "", st.one_rm if st.weight else "", csv_safe(st.note), csv_safe(s.note)])
    return rows


# ---------------------------------------------------------------- dashboard
def dashboard_summary(user, today=None):
    """Goal progress of the weight goal and this week's logged workouts for the dashboard tile."""
    today = today or timezone.localdate()
    monday = today - timedelta(days=today.weekday())
    week = user.workout_sessions.filter(date__gte=monday, date__lte=today).count()
    goal = next((g for g in goals_overview(user, today) if g["kind"] == "weight"), None)
    return {"week_workouts": week, "goal": goal}
