"""Fitness tracker models: workout sessions with their sets, and body / strength goals. Body measurements live on BodyLog and
personal records on PersonalRecord (models.py). Imported at the bottom of models.py so Django registers them with the `gym` app."""
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from .models import User

__all__ = ["WorkoutSession", "WorkoutSet", "TrackerGoal"]


class WorkoutSession(models.Model):
    """One training day a member logged: a date, optionally the weekday of the plan it follows, and a note."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="workout_sessions", verbose_name="A'zo")
    date = models.DateField("Sana", default=timezone.localdate, db_index=True)
    plan_day = models.PositiveSmallIntegerField("Reja kuni", null=True, blank=True, validators=[MaxValueValidator(6)])
    note = models.CharField("Izoh", max_length=200, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [models.Index(fields=["user", "date"], name="wsession_user_date_idx")]
        verbose_name, verbose_name_plural = "Mashg'ulot (kundalik)", "Mashg'ulotlar (kundalik)"

    def __str__(self):
        return f"{self.user_id} {self.date}"

    @property
    def volume(self):
        return round(sum(float(s.weight) * s.reps for s in self.sets.all()), 1)


class WorkoutSet(models.Model):
    """One set of one exercise: reps x weight (kg; 0 for body weight), optional RPE (1-10) and note."""
    session = models.ForeignKey(WorkoutSession, on_delete=models.CASCADE, related_name="sets")
    exercise = models.CharField("Mashq", max_length=80)
    order = models.PositiveSmallIntegerField(default=0)
    reps = models.PositiveSmallIntegerField("Takror", validators=[MinValueValidator(1), MaxValueValidator(100)])
    weight = models.DecimalField("Og'irlik (kg)", max_digits=5, decimal_places=1, default=Decimal("0"),
                                 validators=[MinValueValidator(Decimal("0")), MaxValueValidator(500)])
    rpe = models.DecimalField("RPE", max_digits=3, decimal_places=1, null=True, blank=True,
                              validators=[MinValueValidator(Decimal("1")), MaxValueValidator(10)])
    note = models.CharField("Izoh", max_length=120, blank=True)

    class Meta:
        ordering = ["session_id", "order", "id"]
        indexes = [models.Index(fields=["exercise"], name="wset_exercise_idx")]
        verbose_name, verbose_name_plural = "Yondashuv", "Yondashuvlar"

    @property
    def one_rm(self):
        w = float(self.weight)
        return round(w if self.reps == 1 else w * (1 + self.reps / 30), 1)


class TrackerGoal(models.Model):
    """A member's goal: body weight, a body measurement (cm / %) or a lift's estimated one-rep max. `start_value` is where the
    member was when the goal was set (the progress bar goes from it to `target`)."""
    class Kind(models.TextChoices):
        WEIGHT = "weight", "Vazn"
        MEASURE = "measure", "O'lcham"
        STRENGTH = "strength", "Kuch"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tracker_goals", verbose_name="A'zo")
    kind = models.CharField(max_length=10, choices=Kind.choices, verbose_name="Turi")
    metric = models.CharField("Ko'rsatkich", max_length=80, help_text="weight | BodyLog maydoni | mashq nomi")
    target = models.DecimalField("Maqsad", max_digits=6, decimal_places=1)
    target_date = models.DateField("Muddat", null=True, blank=True)
    start_value = models.DecimalField("Boshlang'ich qiymat", max_digits=6, decimal_places=1, null=True, blank=True)
    start_date = models.DateField(default=timezone.localdate, verbose_name="Boshlanish sanasi")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["kind", "metric"]
        constraints = [models.UniqueConstraint(fields=["user", "kind", "metric"], name="uniq_trackergoal_user_kind_metric")]
        verbose_name, verbose_name_plural = "Tracker maqsadi", "Tracker maqsadlari"
