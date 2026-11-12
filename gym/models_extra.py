"""Models of the member-retention features: freezes, reminders, guest passes, referral ledger, class waitlist, trainer reviews,
gift certificates, FAQ and the legal pages. Imported at the bottom of models.py so Django registers them with the `gym` app."""
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from .models import GymClass, Membership, Payment, Plan, Trainer, User

__all__ = ["MembershipFreeze", "ExpiryReminder", "GuestPass", "ReferralReward", "ClassWaitlist", "TrainerReview", "GiftCertificate", "FaqItem", "LegalPage", "EntryLog", "AdminQuery"]


class MembershipFreeze(models.Model):
    """One pause of a membership. The membership's end date was moved forward by `planned_days` when the freeze was made; ending
    it early moves the date back by the unused days. The member is outside from start_date up to (not including) end_date."""
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="freezes", verbose_name="Abonement")
    start_date = models.DateField("Boshlanishi")
    end_date = models.DateField("Tugashi (shu kuni qaytadi)")
    planned_days = models.PositiveSmallIntegerField("Rejadagi kunlar", default=0)
    ended_early = models.BooleanField("Muddatidan oldin tugatilgan", default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField("Yaratilgan", auto_now_add=True)

    class Meta:
        ordering = ["-start_date", "-id"]
        verbose_name, verbose_name_plural = "Muzlatish", "Muzlatishlar"

    def __str__(self):
        return f"{self.membership.user} · {self.start_date:%d.%m.%Y} – {self.end_date:%d.%m.%Y}"

    @property
    def days(self):
        return max(0, (self.end_date - self.start_date).days)

    @property
    def state(self):
        today = timezone.localdate()
        if self.days == 0:
            return "cancelled"
        if self.end_date <= today:
            return "done"
        return "active" if self.start_date <= today else "scheduled"


class ExpiryReminder(models.Model):
    """Proof that the "membership ends in N days" message was already handled: one row per membership, end date and threshold,
    so the command can run every hour without repeating itself (and a renewed membership gets fresh reminders)."""
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="expiry_reminders")
    expires_on = models.DateField()
    days_before = models.PositiveSmallIntegerField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("membership", "expires_on", "days_before")]
        verbose_name, verbose_name_plural = "Eslatma yozuvi", "Eslatma yozuvlari"


class GuestPass(models.Model):
    """A friend's one-day entry given by a member. The QR carries a signed code (see extras.guest_code); it works once, on its date."""
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="guest_passes", verbose_name="A'zo")
    membership = models.ForeignKey(Membership, null=True, blank=True, on_delete=models.SET_NULL, related_name="guest_passes")
    guest_name = models.CharField("Mehmon ismi", max_length=60)
    guest_phone = models.CharField("Mehmon telefoni", max_length=13, blank=True)
    date = models.DateField("Qaysi kunga")
    used_at = models.DateTimeField("Kirgan vaqti", null=True, blank=True)
    checked_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="Kim qabul qildi")
    cancelled_at = models.DateTimeField("Bekor qilingan", null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name, verbose_name_plural = "Mehmon taklifnomasi", "Mehmon taklifnomalari"

    def __str__(self):
        return f"{self.guest_name} ← {self.owner} · {self.date:%d.%m.%Y}"

    @property
    def state(self):
        if self.cancelled_at:
            return "cancelled"
        if self.used_at:
            return "used"
        today = timezone.localdate()
        return "expired" if self.date < today else ("today" if self.date == today else "valid")


class ReferralReward(models.Model):
    """One row per invited friend who paid for a first membership: the proof that the referrer was paid the bonus days exactly once."""
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="referral_rewards", verbose_name="Taklif qilgan")
    referred = models.OneToOneField(User, on_delete=models.CASCADE, related_name="referral_reward", verbose_name="Taklif qilingan")
    days = models.PositiveSmallIntegerField("Bonus kunlar", default=0)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
        verbose_name, verbose_name_plural = "Taklif bonusi", "Taklif bonuslari"

    def __str__(self):
        return f"{self.referrer} ← {self.referred} (+{self.days})"


class ClassWaitlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="waitlist")
    gym_class = models.ForeignKey(GymClass, on_delete=models.CASCADE, related_name="waitlist")
    date = models.DateField("Sana")
    created = models.DateTimeField("Navbatga turgan vaqti", auto_now_add=True)

    class Meta:
        unique_together = [("user", "gym_class", "date")]
        ordering = ["created", "id"]
        verbose_name, verbose_name_plural = "Navbat (kutish ro'yxati)", "Navbat (kutish ro'yxati)"

    def __str__(self):
        return f"{self.user} → {self.gym_class} {self.date:%d.%m}"


class TrainerReview(models.Model):
    trainer = models.ForeignKey(Trainer, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="trainer_reviews")
    rating = models.PositiveSmallIntegerField("Baho", validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField("Fikr", max_length=500, blank=True)
    hidden = models.BooleanField("Yashirilgan (saytda ko'rinmaydi)", default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("trainer", "user")]
        ordering = ["-updated"]
        verbose_name, verbose_name_plural = "Murabbiy bahosi", "Murabbiy baholari"

    def __str__(self):
        return f"{self.trainer} · {self.rating}/5 · {self.user}"


class GiftCertificate(models.Model):
    """A one-time code worth a whole plan or a sum. Made by the admin, or bought by a member (then it works once the payment is paid)."""
    code = models.CharField("Kod", max_length=20, unique=True, blank=True)
    plan = models.ForeignKey(Plan, null=True, blank=True, on_delete=models.PROTECT, related_name="gifts", verbose_name="Abonement turi",
                             help_text="Abonement uchun sertifikat. Yoki pastda summani kiriting.")
    amount = models.BigIntegerField("Summa (so'm)", default=0, validators=[MinValueValidator(0)],
                                    help_text="Abonement tanlanmasa: shu summa chegirma bo'ladi (bir martalik, qoldiq qaytarilmaydi).")
    buyer = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="gifts_bought", verbose_name="Sotib olgan a'zo")
    payment = models.ForeignKey(Payment, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="To'lov")
    expires = models.DateField("Amal qilish muddati")
    redeemed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="gifts_redeemed", verbose_name="Kim ishlatdi")
    redeemed_at = models.DateTimeField("Ishlatilgan vaqt", null=True, blank=True)
    note = models.CharField("Izoh", max_length=120, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
        verbose_name, verbose_name_plural = "Sovg'a sertifikati", "Sovg'a sertifikatlari"

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.plan_id and not self.amount:
            raise ValidationError("Abonement yoki summani kiriting.")

    def __str__(self):
        return f"{self.code} · {self.plan.name if self.plan_id else str(self.amount) + ' so`m'}"

    @property
    def state(self):
        if self.payment_id and self.payment.status != Payment.Status.PAID:
            return "unpaid"
        if self.redeemed_at:
            return "redeemed"
        if self.expires < timezone.localdate():
            return "expired"
        return "valid"


class FaqItem(models.Model):
    """A question on /faq/. The answer may use {hours}, {phone}, {address}, {freeze_min}, {freeze_max}, {bonus}, {cancel_hours}: they are filled from the settings."""
    question_uz = models.CharField("Savol (o'zbekcha)", max_length=200)
    question_ru = models.CharField("Savol (ruscha)", max_length=200, blank=True)
    question_en = models.CharField("Savol (inglizcha)", max_length=200, blank=True)
    answer_uz = models.TextField("Javob (o'zbekcha)")
    answer_ru = models.TextField("Javob (ruscha)", blank=True)
    answer_en = models.TextField("Javob (inglizcha)", blank=True)
    question_tr = models.CharField("Savol (turkcha)", max_length=200, blank=True)
    question_ky = models.CharField("Savol (qirg'izcha)", max_length=200, blank=True)
    question_tg = models.CharField("Savol (tojikcha)", max_length=200, blank=True)
    answer_tr = models.TextField("Javob (turkcha)", blank=True)
    answer_ky = models.TextField("Javob (qirg'izcha)", blank=True)
    answer_tg = models.TextField("Javob (tojikcha)", blank=True)
    CATEGORIES = [("general", "Umumiy"), ("membership", "Abonement"), ("payment", "To'lov"), ("classes", "Mashg'ulotlar"), ("shop", "Do'kon"), ("account", "Akkaunt")]
    category = models.CharField("Bo'lim", max_length=12, choices=CATEGORIES, blank=True,
                                help_text="Bo'sh qoldirsangiz, savol matniga qarab avtomatik aniqlanadi (yordam oynasidagi bo'limlar uchun).")
    order = models.PositiveSmallIntegerField("Tartib", default=0)
    active = models.BooleanField("Ko'rinadi", default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name, verbose_name_plural = "Savol-javob (FAQ)", "Savol-javoblar (FAQ)"

    def __str__(self):
        return self.question_uz

    def q(self, lang):
        """The question in `lang`; an empty one falls back along the language chain (tr -> en, ky / tg -> ru, then Uzbek)."""
        return self._chain("question", lang)

    def a(self, lang):
        return self._chain("answer", lang)

    def _chain(self, field, lang):
        from .i18n import CHAIN
        for lg in CHAIN.get(lang, ("uz",)):
            got = getattr(self, f"{field}_{lg}", "")
            if got:
                return got
        return getattr(self, f"{field}_uz")


class LegalPage(models.Model):
    """Public offer, privacy policy, refund rules. Plain text: a blank line starts a paragraph, "# " a heading, "- " a list item.
    Placeholders in [SQUARE BRACKETS] must be replaced with the company's real data before the site goes live."""
    SLUGS = [("oferta", "Ommaviy oferta"), ("privacy", "Maxfiylik siyosati"), ("refund", "Qaytarish qoidalari")]
    slug = models.SlugField("Sahifa", max_length=20, unique=True, choices=SLUGS)
    title_uz = models.CharField("Sarlavha (o'zbekcha)", max_length=120)
    title_ru = models.CharField("Sarlavha (ruscha)", max_length=120, blank=True)
    title_en = models.CharField("Sarlavha (inglizcha)", max_length=120, blank=True)
    body_uz = models.TextField("Matn (o'zbekcha)")
    body_ru = models.TextField("Matn (ruscha)", blank=True)
    body_en = models.TextField("Matn (inglizcha)", blank=True)
    updated = models.DateTimeField("O'zgartirilgan", auto_now=True)

    class Meta:
        ordering = ["id"]
        verbose_name, verbose_name_plural = "Huquqiy sahifa", "Huquqiy sahifalar"

    def __str__(self):
        return self.title_uz

    def title(self, lang):
        return getattr(self, f"title_{lang}", "") or self.title_uz

    def body(self, lang):
        return getattr(self, f"body_{lang}", "") or self.body_uz

    def placeholders(self):
        from .legal_defaults import find_placeholders
        return find_placeholders(self.body_uz, self.body_ru, self.body_en)


class EntryLog(models.Model):
    """Every attempt to get in: accepted (a Visit was or already is recorded) or turned away, with the way it was done and the reason."""
    METHODS = [("qr", "QR-kod"), ("manual", "Qabulxona (qo'lda)"), ("self", "A'zo o'zi belgiladi"), ("guest", "Mehmon taklifnomasi"), ("old", "Eski yozuv")]
    RESULTS = [("ok", "Kirdi"), ("repeat", "Bugun allaqachon kirgan"), ("rejected", "Rad etildi")]
    REASONS = [("invalid", "Kod noto'g'ri"), ("no_membership", "Abonement yo'q"), ("expired", "Abonement tugagan"), ("frozen", "Abonement muzlatilgan"),
               ("blocked", "Akkaunt bloklangan"), ("guest_used", "Taklifnoma ishlatilgan"), ("guest_expired", "Taklifnoma muddati o'tgan"),
               ("guest_cancelled", "Taklifnoma bekor qilingan"), ("guest_early", "Taklifnoma boshqa kunga"), ("guest_owner_out", "Taklif qilgan a'zo kira olmaydi")]
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="entry_logs", verbose_name="A'zo")
    guest_pass = models.ForeignKey(GuestPass, null=True, blank=True, on_delete=models.SET_NULL, related_name="entries", verbose_name="Taklifnoma")
    method = models.CharField("Usul", max_length=8, choices=METHODS)
    result = models.CharField("Natija", max_length=8, choices=RESULTS)
    reason = models.CharField("Sabab", max_length=16, choices=REASONS, blank=True)
    staff = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="Kim qabul qildi")
    ts = models.DateTimeField("Vaqt", default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-ts", "-id"]
        verbose_name, verbose_name_plural = "Kirish tarixi", "Kirish tarixi"

    def __str__(self):
        return f"{self.user or self.guest_pass or '?'} · {self.get_result_display()}"


class AdminQuery(models.Model):
    """A question typed into the admin's AI assistant, kept only to improve it: the text (long digit runs masked) and which intent matched."""
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="Kim so'radi")
    text = models.CharField("Savol", max_length=200)
    intent = models.CharField("Aniqlangan maqsad", max_length=40, blank=True)
    matched = models.BooleanField("Tushunildi", default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created", "-id"]
        verbose_name, verbose_name_plural = "AI savol", "AI savollar"

    def __str__(self):
        return f"{self.text[:40]} → {self.intent or '?'}"
