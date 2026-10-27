"""AI coach (chat) and AI workout-plan generator, both on the Claude API.

Switched on by the ANTHROPIC_API_KEY environment variable; without it the pages explain that the feature is not connected.
Every call is a paid API request, so each member has a daily message limit (FZ_AI_DAILY_LIMIT, default 30).
"""
import json
import logging
import os
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone

log = logging.getLogger(__name__)

MODEL = os.environ.get("FZ_AI_MODEL", "claude-opus-5-5")
LANG_NAMES = {"uz": "Uzbek (Latin script)", "ru": "Russian", "en": "English"}
WEEKDAYS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
HISTORY = 20          # messages of earlier conversation sent with each question
MAX_QUESTION = 1500   # characters a member may type


class AIError(Exception):
    """Carries a translation key the page shows to the member."""
    def __init__(self, key):
        super().__init__(key)
        self.key = key


def enabled():
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def daily_limit():
    try:
        return max(1, int(os.environ.get("FZ_AI_DAILY_LIMIT", "30")))
    except ValueError:
        return 30


def _quota_key(user):
    return f"ai:quota:{user.pk}:{timezone.localdate():%Y%m%d}"


def used_today(user):
    return cache.get(_quota_key(user), 0)


def _take_quota(user):
    key = _quota_key(user)
    used = cache.get(key, 0)
    if used >= daily_limit():
        raise AIError("ai_limit")
    cache.set(key, used + 1, 60 * 60 * 26)


def member_profile(user):
    """What the coach knows about the member: only training-related facts, never phone numbers or payments."""
    from . import services
    lines = [f"First name: {user.first_name or 'member'}"]
    if user.goal:
        lines.append(f"Goal: {user.get_goal_display()}")
    if user.birth_date:
        today = timezone.localdate()
        lines.append(f"Age: {today.year - user.birth_date.year - ((today.month, today.day) < (user.birth_date.month, user.birth_date.day))}")
    last = user.bodylogs.order_by("-date", "-id").first()
    if last:
        lines.append(f"Latest weight: {last.weight} kg" + (f", height {last.height_cm} cm" if last.height_cm else ""))
    if user.target_weight:
        lines.append(f"Target weight: {user.target_weight} kg")
    m = services.active_membership(user)
    lines.append("Has an active gym membership" if m else "No active gym membership")
    visits = user.visits.filter(ts__gte=timezone.now() - timedelta(days=28)).count()
    lines.append(f"Gym visits in the last 4 weeks: {visits}")
    plan = user.workout_plans.filter(active=True).prefetch_related("exercises").first()
    if plan:
        ex = "; ".join(f"{WEEKDAYS_EN[e.weekday]}: {e.name} {e.sets}x{e.reps}" for e in plan.exercises.all()[:30])
        lines.append(f"Current workout plan \"{plan.title}\"" + (" (made by their trainer)" if plan.trainer_id else "") + f": {ex}")
    best = {}
    for r in user.records.order_by("-date")[:60]:
        if r.lift not in best or r.one_rm > best[r.lift].one_rm:
            best[r.lift] = r
    if best:
        lines.append("Best lifts: " + "; ".join(f"{r.get_lift_display()} {r.weight} kg x {r.reps}" for r in best.values()))
    return "\n".join(lines)


def _system(lang, gym_name="Fitnes Zal"):
    return (
        f"You are the AI coach of {gym_name}, a gym in Uzbekistan, talking to one of its members on the gym's website. "
        f"Always answer in {LANG_NAMES.get(lang, 'Uzbek (Latin script)')}, whatever language the question is in. "
        "Help with training technique, workout programming, recovery, and everyday nutrition. Be practical and specific "
        "to this member, using the profile you are given; keep answers short (a few sentences or a short list) unless they ask for detail. "
        "You are not a doctor: for pain, injuries, illness, pregnancy, medication or eating disorders, give general safety advice "
        "and tell them to see a doctor and to speak with a trainer at the front desk. Never recommend steroids or other banned substances. "
        "Do not invent gym prices, schedules or staff names; for those, point them to the website pages or the front desk. "
        "Plain text only, no Markdown headings."
    )


def _call(**kwargs):
    """One request, with the server-side fallback switched on so a declined request is retried on another model."""
    import anthropic
    if not enabled():
        raise AIError("ai_off")
    client = anthropic.Anthropic(timeout=90.0, max_retries=2)
    try:
        resp = client.beta.messages.create(
            model=MODEL,
            betas=["server-side-fallback-2026-06-01"],
            fallbacks=[{"model": "claude-opus-4-8"}],
            **kwargs,
        )
    except anthropic.AuthenticationError:
        log.error("AI: ANTHROPIC_API_KEY was rejected")
        raise AIError("ai_off")
    except anthropic.RateLimitError:
        raise AIError("ai_busy")
    except anthropic.BadRequestError as e:
        log.error("AI bad request: %s", e.message)
        raise AIError("ai_error")
    except anthropic.APIStatusError as e:
        log.error("AI API error %s", e.status_code)
        raise AIError("ai_busy" if e.status_code >= 500 else "ai_error")
    except anthropic.APIConnectionError:
        raise AIError("ai_busy")
    if resp.stop_reason == "refusal":
        raise AIError("ai_refused")
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    if not text:
        raise AIError("ai_error")
    return text


def ask(user, question, lang="uz"):
    """Answers a member's question; the conversation is stored so the coach remembers it."""
    from .models import AIMessage
    question = (question or "").strip()[:MAX_QUESTION]
    if not question:
        raise AIError("ai_empty")
    _take_quota(user)
    past = list(user.ai_messages.order_by("-id")[:HISTORY])[::-1]
    messages = [{"role": m.role, "content": m.content} for m in past]
    while messages and messages[0]["role"] != "user":  # the API wants the history to start with the member
        messages.pop(0)
    messages.append({"role": "user", "content": f"<member_profile>\n{member_profile(user)}\n</member_profile>\n\n{question}"})
    answer = _call(
        max_tokens=4000,
        system=_system(lang),
        output_config={"effort": "low"},
        messages=messages,
    )
    AIMessage.objects.create(user=user, role="user", content=question)
    return AIMessage.objects.create(user=user, role="assistant", content=answer)


PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "notes": {"type": "string"},
        "exercises": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "weekday": {"type": "integer"},
                    "name": {"type": "string"},
                    "sets": {"type": "integer"},
                    "reps": {"type": "string"},
                    "note": {"type": "string"},
                },
                "required": ["weekday", "name", "sets", "reps", "note"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "notes", "exercises"],
    "additionalProperties": False,
}
LEVELS = {"beginner": "beginner (under 6 months of training)", "intermediate": "intermediate (6 months to 2 years)",
          "advanced": "advanced (2+ years)"}


def make_plan(user, level, days, minutes, notes="", lang="uz"):
    """Builds a weekly plan with structured output and saves it as the member's current plan.
    A plan written by the member's trainer is never replaced (same rule as the ready-made programs)."""
    from .models import WorkoutPlan
    if user.workout_plans.filter(active=True, trainer__isnull=False).exists():
        raise AIError("program_trainer")
    _take_quota(user)
    request = (
        f"Create a weekly gym workout plan for this member.\n<member_profile>\n{member_profile(user)}\n</member_profile>\n"
        f"Experience: {LEVELS.get(level, LEVELS['beginner'])}. Training days per week: {days}. About {minutes} minutes per session.\n"
        + (f"Member's own notes (equipment, injuries, wishes): {notes[:300]}\n" if notes.strip() else "")
        + "Rules: weekday is 0=Monday ... 6=Sunday; use exactly the requested number of different days with rest days between hard sessions; "
        "4-7 exercises per day that fit in the time; reps like \"8-10\", \"12\" or \"30 s\"; sets 2-5. "
        "Exercise names in the member's language with the common English gym name in brackets, e.g. \"O'tirib turish (Squat)\". "
        "note: one short technique or rest tip. title: short and motivating. notes: 2-3 sentences on how to progress and warm up. "
        f"Write title, names, notes in {LANG_NAMES.get(lang, 'Uzbek (Latin script)')}."
    )
    raw = _call(
        max_tokens=8000,
        system=_system(lang),
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": PLAN_SCHEMA}},
        messages=[{"role": "user", "content": request}],
    )
    try:
        data = json.loads(raw)
    except ValueError:
        raise AIError("ai_error")
    rows = []
    for e in data.get("exercises", [])[:42]:  # the model follows the rules, but nothing it returns is trusted blindly
        try:
            wd, sets = int(e["weekday"]), int(e["sets"])
        except (KeyError, TypeError, ValueError):
            continue
        name = str(e.get("name", "")).strip()[:80]
        if 0 <= wd <= 6 and name:
            rows.append((wd, name, max(1, min(sets, 10)), str(e.get("reps", "10")).strip()[:20] or "10", str(e.get("note", "")).strip()[:120]))
    if not rows:
        raise AIError("ai_error")
    user.workout_plans.filter(active=True).update(active=False)
    plan = WorkoutPlan.objects.create(user=user, title=("✦ " + str(data.get("title", "")).strip())[:80] or "✦ AI",
                                      notes=str(data.get("notes", "")).strip()[:2000], active=True)
    for i, (wd, name, sets, reps, note) in enumerate(sorted(rows, key=lambda r: r[0])):
        plan.exercises.create(weekday=wd, name=name, sets=sets, reps=reps, note=note, order=i)
    return plan
