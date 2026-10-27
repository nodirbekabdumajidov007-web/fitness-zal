from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone

from .media import validate_image, validate_video_file, validate_video_url, video_storage

PHONE_VALIDATOR = RegexValidator(r"^\+998\d{9}$", "+998 bilan boshlanib, 9 ta raqam bo'lishi kerak")


def image_url(kind, obj):
    """URL of an uploaded picture, with a version so browsers refetch it after a change."""
    import zlib
    f = {"product": "image", "trainer": "photo", "avatar": "avatar"}[kind]
    f = getattr(obj, f)
    return f"/img/{kind}/{obj.pk}/?v={zlib.crc32(f.name.encode())}" if f else ""


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, username=None, password=None, **extra):
        user = self.model(username=username or unique_username(extra.get("email"), extra.get("phone"), extra.get("first_name")), **extra)
        user.set_password(password) if password else user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(username, password, **extra)

    def get_by_natural_key(self, username):
        return self.get(username__iexact=username)


USERNAME_VALIDATOR = RegexValidator(r"^[A-Za-z0-9_.]{3,30}$", "err_username")


def unique_username(email=None, phone=None, first_name=None):
    """A login for accounts made without one (Google, Apple, or created by staff): from the e-mail, the name or the phone."""
    import re
    import secrets
    base = (email or "").split("@")[0] or (first_name or "") or ("u" + (phone or "")[-4:])
    base = re.sub(r"[^A-Za-z0-9_.]", "", base.lower())[:20] or "user"
    if len(base) < 3:
        base = (base + "user")[:20]
    name = base
    while User.objects.filter(username__iexact=name).exists():
        name = f"{base}{secrets.randbelow(9000) + 1000}"
    return name


class User(AbstractBaseUser, PermissionsMixin):
    """Member or staff. Signs up with a username, e-mail and password (Django's usual shape); can sign in with the username,
    the e-mail or the phone number."""
    username = models.CharField("Login", max_length=30, unique=True, validators=[USERNAME_VALIDATOR],
                                help_text="3-30 belgi: lotin harflari, raqamlar, _ va .")
    phone = models.CharField("Telefon", max_length=13, unique=True, null=True, blank=True, validators=[PHONE_VALIDATOR])
    email = models.EmailField("Email", unique=True, null=True, blank=True)
    first_name = models.CharField("Ism", max_length=40, blank=True)
    last_name = models.CharField("Familiya", max_length=40, blank=True)
    is_active = models.BooleanField("Faol (bloklanmagan)", default=True)
    is_staff = models.BooleanField("Xodim", default=False)
    staff_note = models.TextField("Xodim izohi", blank=True)
    created = models.DateTimeField("Ro'yxatdan o'tgan", auto_now_add=True)
    phone_verified = models.BooleanField("Telefon tasdiqlangan", default=False)
    lang = models.CharField(max_length=2, default="uz")
    referral_code = models.CharField("Taklif kodi", max_length=8, unique=True, null=True, blank=True, editable=False)
    referred_by = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="referrals", editable=False, verbose_name="Kim taklif qilgan")
    referral_rewarded = models.BooleanField("Taklif bonusi berilgan", default=False, editable=False)
    telegram_chat_id = models.BigIntegerField("Telegram chat", null=True, blank=True, editable=False)
    tg_link_code = models.CharField(max_length=12, blank=True, editable=False)
    show_in_leaderboard = models.BooleanField("Reytingda ko'rinsin", default=True)
    chat_visible = models.BooleanField("Chatda qidiruvda ko'rinsin", default=True)
    chat_banned = models.BooleanField("Chatda yozishdan chetlatilgan", default=False)
    last_seen = models.DateTimeField("Oxirgi faollik (chat)", null=True, blank=True, editable=False)
    GOALS = [("lose", "Ozish"), ("keep", "Formani saqlash"), ("gain", "Massa olish"), ("strength", "Kuch"), ("health", "Sog'liq")]
    avatar = models.FileField("Profil rasmi (jpg, png, webp)", upload_to="avatars/", blank=True, validators=[validate_image])
    birth_date = models.DateField("Tug'ilgan kun", null=True, blank=True)
    goal = models.CharField("Maqsad", max_length=10, choices=GOALS, blank=True)
    target_weight = models.DecimalField("Maqsad vazni (kg)", max_digits=5, decimal_places=1, null=True, blank=True,
                                        validators=[MinValueValidator(Decimal("30")), MaxValueValidator(250)])

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]
    objects = UserManager()

    class Meta:
        verbose_name, verbose_name_plural = "A'zo", "A'zolar"

    def save(self, *args, **kwargs):
        if not self.referral_code:
            import secrets
            for _ in range(10):
                code = secrets.token_hex(4).upper()
                if not User.objects.filter(referral_code=code).exists():
                    self.referral_code = code
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} (FZ-{self.pk:04d})" if self.pk else self.full_name

    @property
    def member_code(self):
        return f"FZ-{self.pk:04d}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username

    @property
    def avatar_src(self):
        return image_url("avatar", self)

    @property
    def initials(self):
        if self.first_name:
            return (self.first_name[:1] + self.last_name[:1]).upper()
        return self.username[:2].upper()

    def get_short_name(self):
        return self.first_name or self.username

    def get_full_name(self):
        return self.full_name.strip()


class GymSettings(models.Model):
    """Single row, edited in the admin."""
    open_time = models.TimeField("Ochilish vaqti", default="06:00")
    close_time = models.TimeField("Yopilish vaqti", default="23:00")
    phone = models.CharField("Telefon (9 raqam)", max_length=20, default="90 877 55 05")
    instagram = models.CharField("Instagram", max_length=30, default="abdulloh.001uzb", validators=[RegexValidator(r"^[A-Za-z0-9._]+$")])
    telegram = models.URLField("Telegram havola", default="https://t.me/+998908775505",
                               validators=[RegexValidator(r"^https://(t\.me|telegram\.me)/", "Faqat https://t.me/... havolasi")])
    address = models.CharField("Manzil", max_length=200, blank=True)
    freeze_max_days = models.PositiveSmallIntegerField("Muzlatish: eng ko'p kun", default=14)
    demo_payments = models.BooleanField("Sinov to'lovlari (Payme/Click/Uzum) yoqilgan", default=False,
                                        help_text="Faqat sinash uchun: tanlansa to'lov pulsiz 'to'landi' bo'ladi. Internetda (DEBUG=0) bu hech qachon ishlamaydi.")
    referral_bonus_days = models.PositiveSmallIntegerField("Do'st taklif qilish: bonus kunlar", default=7,
                                                           help_text="Taklif qilingan do'st birinchi abonementini olganda ikkalasiga qo'shiladi.")
    require_phone_verify = models.BooleanField("Xarid va bron uchun telefon tasdig'i shart", default=False,
                                               help_text="Faqat SMS xizmati ulangandan keyin yoqing.")
    reminder_days = models.PositiveSmallIntegerField("Abonement tugashidan necha kun oldin eslatish", default=3)
    login_sms_code = models.BooleanField("Kirishda telefonga SMS kod yuborilsin", default=False,
                                         help_text="Parol (yoki Google) to'g'ri bo'lsa ham, telefonga kelgan 6 xonali kodsiz kirib bo'lmaydi. SMS xizmati ulanishi kerak.")
    require_google = models.BooleanField("Faqat Google akkaunt orqali kirish va ro'yxatdan o'tish", default=False,
                                         help_text="Telefon+parol bilan faqat zal egasi (bosh admin) kira oladi. Avval Google Client ID ni kiriting.")
    google_client_id = models.CharField("Google Client ID", max_length=120, blank=True,
                                        validators=[RegexValidator(r"^[\w.-]+\.apps\.googleusercontent\.com$", "Client ID ...apps.googleusercontent.com bilan tugaydi")],
                                        help_text="Bu ochiq identifikator (sahifada baribir ko'rinadi), maxfiy kalit emas. Serverdagi GOOGLE_CLIENT_ID bo'lsa, o'shanisi ishlatiladi.")
    revenue_goal = models.BigIntegerField("Oylik tushum maqsadi (so'm)", default=20_000_000, validators=[MinValueValidator(0)])
    hero_video = models.FileField("Bosh sahifa videosi (mp4 yoki webm)", upload_to="hero/", blank=True, validators=[validate_video_file], storage=video_storage,
                                  help_text="Bir marta o'ynaydi va oxirgi kadrda to'xtab qoladi. 5–10 soniyali, 1920px gacha, ovozsiz video eng yaxshi. "
                                            "Bo'sh bo'lsa, zal surati animatsiya bilan ko'rsatiladi.")
    yandex_map_url = models.URLField("Yandex xaritadagi zal havolasi", max_length=300, blank=True,
                                     validators=[RegexValidator(r"^https://yandex\.(uz|ru|com)/maps/", "Yandex Maps havolasi (https://yandex.uz/maps/...)")],
                                     help_text="Yandex xaritada zalingizni oching va manzil satridagi havolani shu yerga qo'ying: saytda xarita chiqadi.")
    low_stock_threshold = models.PositiveSmallIntegerField("Omborda shundan kam qolsa ogohlantirish", default=5)
    alert_phone = models.CharField("Ogohlantirish SMS keladigan telefon (9 raqam)", max_length=20, blank=True,
                                   help_text="Bo'sh bo'lsa, zal telefoniga yuboriladi.")
    delivery_on = models.BooleanField("Mahsulotlarni yetkazib berish yoqilgan", default=True)
    delivery_fee = models.BigIntegerField("Yetkazish narxi (so'm)", default=15000, validators=[MinValueValidator(0)])
    free_delivery_from = models.BigIntegerField("Shu summadan bepul yetkaziladi (so'm, 0 = hech qachon)", default=300000, validators=[MinValueValidator(0)])
    delivery_area = models.CharField("Yetkazish hududi", max_length=120, default="Shahar ichida, 1–2 soatda")
    map_lat = models.DecimalField("Zal joylashuvi: kenglik (lat)", max_digits=9, decimal_places=6, null=True, blank=True,
                                  help_text="Google xaritada zalni bosing → koordinatalar chiqadi (masalan 41.311081). Bo'sh bo'lsa, manzil bo'yicha qidiriladi.")
    map_lng = models.DecimalField("Zal joylashuvi: uzunlik (lng)", max_digits=9, decimal_places=6, null=True, blank=True)
    gym_capacity = models.PositiveSmallIntegerField("Zal sig'imi (bir vaqtda necha kishi qulay)", default=40,
                                                    help_text="Bosh sahifadagi «Hozir zal: bo'sh / o'rtacha / gavjum» o'lchagichi uchun.")
    apple_client_id = models.CharField("Apple Services ID (iCloud bilan kirish)", max_length=120, blank=True,
                                       help_text="Apple Developer → Identifiers → Services ID (masalan uz.fitneszal.web). Faqat https domenda ishlaydi.")
    hero_word = models.CharField("Bosh sahifadagi ulkan so'z", max_length=12, default="KUCH", help_text="Video ortida turadigan katta harflar.")
    telegram_bot = models.CharField("Telegram bot (username, @siz)", max_length=40, blank=True)

    class Meta:
        verbose_name = verbose_name_plural = "Zal sozlamalari"

    def google_id(self):
        from django.conf import settings
        return settings.GOOGLE_CLIENT_ID or self.google_client_id

    def apple_id(self):
        import os
        return os.environ.get("APPLE_CLIENT_ID", "").strip() or self.apple_client_id

    def routes(self):
        """Links that open a driving route to the gym in Yandex and Google maps (by coordinates, or by the address)."""
        from urllib.parse import quote
        out = {}
        if self.map_lat is not None and self.map_lng is not None:
            ll = f"{self.map_lat},{self.map_lng}"
            out = {"yandex": f"https://yandex.uz/maps/?rtext=~{ll}&rtt=auto", "google": f"https://www.google.com/maps/dir/?api=1&destination={ll}",
                   "taxi": f"https://3.redirect.appmetrica.yandex.com/route?end-lat={self.map_lat}&end-lon={self.map_lng}&appmetrica_tracking_id=1178268795219780156"}
        elif self.address:
            q = quote(self.address)
            out = {"yandex": f"https://yandex.uz/maps/?text={q}", "google": f"https://www.google.com/maps/dir/?api=1&destination={q}"}
        if self.yandex_map_url:
            out["yandex"] = self.yandex_map_url  # the gym's own Yandex card has the route button and photos
            out.setdefault("google", "https://www.google.com/maps/search/?api=1&query=" + quote(self.address or "Fitnes Zal"))
        return out

    def map_embed(self):
        """URL for the embedded Yandex map: the organisation card if a Yandex link is set, else a pin at the coordinates."""
        import re
        m = re.search(r"/org/([\w-]*)/(\d+)", self.yandex_map_url or "")
        if m:  # Yandex's own "embed this place" form: the map opens with the gym's card, like on Yandex Maps itself
            return f"https://yandex.uz/map-widget/v1/org/{m.group(1) or 'gym'}/{m.group(2)}/?z=17"
        if self.map_lat is not None and self.map_lng is not None:
            return f"https://yandex.uz/map-widget/v1/?ll={self.map_lng},{self.map_lat}&z=17&pt={self.map_lng},{self.map_lat},pm2rdm"
        return ""

    def delivery_cost(self, subtotal):
        if self.free_delivery_from and subtotal >= self.free_delivery_from:
            return 0
        return self.delivery_fee

    def clean(self):
        """Refuse switches that would lock everyone out because the service behind them is not connected."""
        from django.conf import settings
        from django.core.exceptions import ValidationError
        from . import sms
        errors = {}
        if self.require_google and not self.google_id():
            errors["require_google"] = "Google ulanmagan: avval «Google Client ID» ni kiriting, aks holda hech kim kira olmaydi."
        if self.login_sms_code and not (sms.real_backend() or settings.DEBUG):
            errors["login_sms_code"] = "SMS xizmati ulanmagan (SMS_BACKEND=eskiz): kod hech kimga bormaydi va hech kim kira olmaydi."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        return cls.objects.get_or_create(pk=1)[0]

    def __str__(self):
        return "Zal sozlamalari"


class Plan(models.Model):
    code = models.SlugField("Kod", unique=True)
    name = models.CharField("Nomi", max_length=60)
    months = models.PositiveSmallIntegerField("Oylar soni", default=1)
    price = models.BigIntegerField("Narx (so'm)")
    perks = models.TextField("Imkoniyatlar (har qatorda bittadan)", blank=True)
    active = models.BooleanField("Sotuvda", default=True)
    order = models.PositiveSmallIntegerField("Tartib", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name, verbose_name_plural = "Abonement turi", "Abonement turlari"

    def __str__(self):
        return f"{self.name} ({self.price:,} so'm)".replace(",", " ")


class Membership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    starts = models.DateTimeField("Boshlanishi")
    expires = models.DateTimeField("Tugashi")
    freeze_used = models.BooleanField("Muzlatilgan", default=False)
    frozen_until = models.DateTimeField(null=True, blank=True)
    reminded = models.BooleanField(default=False, editable=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-expires"]
        verbose_name, verbose_name_plural = "Abonement", "Abonementlar"

    def __str__(self):
        return f"{self.user} · {self.plan.name} · {timezone.localtime(self.expires):%d.%m.%Y}"

    @property
    def is_active(self):
        now = timezone.now()
        return self.starts <= now < self.expires

    @property
    def is_frozen(self):
        return bool(self.frozen_until and self.frozen_until > timezone.now())


class PromoCode(models.Model):
    code = models.CharField("Kod", max_length=20, unique=True)
    percent = models.PositiveSmallIntegerField("Chegirma %", validators=[MinValueValidator(1), MaxValueValidator(100)])
    valid_until = models.DateField("Amal qilish muddati", null=True, blank=True)
    max_uses = models.PositiveIntegerField("Eng ko'p ishlatish", null=True, blank=True)
    used = models.PositiveIntegerField("Ishlatilgan", default=0)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name, verbose_name_plural = "Promokod", "Promokodlar"

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} (-{self.percent}%)"

    def is_valid(self):
        if not self.active:
            return False
        if self.valid_until and self.valid_until < timezone.localdate():
            return False
        return self.max_uses is None or self.used < self.max_uses


class Category(models.Model):
    name = models.CharField("Nomi", max_length=40)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name, verbose_name_plural = "Kategoriya", "Kategoriyalar"

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="products")
    name = models.CharField("Nomi", max_length=60)
    price = models.BigIntegerField("Narx")
    stock = models.PositiveIntegerField("Omborda", default=0)
    active = models.BooleanField("Sotuvda", default=True)
    image = models.FileField("Rasm (jpg, png, webp)", upload_to="products/", blank=True, validators=[validate_image])
    image_url = models.URLField("Yoki rasm havolasi (https)", max_length=500, blank=True,
                                validators=[RegexValidator(r"^https://", "Faqat https:// havola")],
                                help_text="Boshqa saytdagi rasm. U o'chirilsa yoki o'zgarsa, bu yerda ham yo'qoladi; ishonchliroq yo'l: rasmni yuklash.")
    description = models.TextField("Tavsif", blank=True)
    low_alert_on = models.DateField("Oxirgi «tugayapti» ogohlantirishi", null=True, blank=True, editable=False)

    class Meta:
        ordering = ["category__order", "id"]
        verbose_name, verbose_name_plural = "Mahsulot", "Mahsulotlar"

    def __str__(self):
        return self.name

    @property
    def image_src(self):
        return image_url("product", self) or self.image_url

    @property
    def illustration(self):
        """A drawn picture used until a real photo is uploaded."""
        n = self.name.lower()
        for keys, pic in ((("shaker",), "shaker"), (("kokteyl",), "shaker"), (("suv", "water"), "bottle"),
                          (("energetik", "izotonik", "energy"), "can"), (("batonchik", "bar"), "bar"),
                          (("whey", "protein", "kreatin", "bcaa", "gainer"), "tub")):
            if any(k in n for k in keys):
                return f"img/products/{pic}.svg"
        return "img/products/box.svg"


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Yangi"
        SHIPPING = "shipping", "Yo'lda"
        DONE = "done", "Berildi"
        CANCELLED = "cancelled", "Bekor qilindi"

    class Delivery(models.TextChoices):
        PICKUP = "pickup", "Zaldan olib ketadi"
        COURIER = "courier", "Yetkazib berish"

    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="orders")
    total = models.BigIntegerField("Jami")
    method = models.CharField("To'lov usuli", max_length=8)
    status = models.CharField("Holat", max_length=10, choices=Status.choices, default=Status.NEW)
    delivery = models.CharField("Olish usuli", max_length=8, choices=Delivery.choices, default=Delivery.PICKUP)
    address = models.CharField("Manzil", max_length=200, blank=True)
    delivery_phone = models.CharField("Qabul qiluvchi telefoni", max_length=13, blank=True)
    delivery_note = models.CharField("Kuryerga izoh", max_length=200, blank=True)
    delivery_fee = models.BigIntegerField("Yetkazish narxi", default=0)
    shipped_at = models.DateTimeField("Yo'lga chiqdi", null=True, blank=True)
    done_at = models.DateTimeField("Topshirildi", null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    @property
    def subtotal(self):
        return self.total - self.delivery_fee

    class Meta:
        ordering = ["-created"]
        verbose_name, verbose_name_plural = "Buyurtma", "Buyurtmalar"

    def __str__(self):
        return f"Buyurtma #{self.pk}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=60)
    price = models.BigIntegerField()
    qty = models.PositiveSmallIntegerField()

    @property
    def subtotal(self):
        return self.price * self.qty


def luhn_ok(digits):
    total, flip = 0, False
    for ch in reversed(digits):
        n = int(ch)
        if flip:
            n = n * 2 - 9 if n * 2 > 9 else n * 2
        total += n
        flip = not flip
    return total % 10 == 0


def validate_card_number(value):
    digits = "".join(c for c in str(value) if c.isdigit())
    if len(digits) != 16 or not luhn_ok(digits):
        from django.core.exceptions import ValidationError
        raise ValidationError("Karta raqami noto'g'ri: 16 ta raqam bo'lishi va tekshiruv raqami mos kelishi kerak.")


class PaymentCard(models.Model):
    """A card that receives members' transfers. Add a new one and mark it primary to switch; old payments keep the card they were made to."""
    bank = models.CharField("Bank / tizim", max_length=30, default="Uzcard")
    number = models.CharField("Karta raqami (16 raqam)", max_length=19, validators=[validate_card_number])
    holder = models.CharField("Karta egasi", max_length=60)
    active = models.BooleanField("Faol", default=True)
    is_primary = models.BooleanField("Asosiy karta (to'lovlar shu kartaga)", default=False)
    note = models.CharField("Izoh", max_length=120, blank=True)

    class Meta:
        ordering = ["-is_primary", "-active", "id"]
        verbose_name, verbose_name_plural = "To'lov kartasi", "To'lov kartalari"

    def save(self, *args, **kwargs):
        self.number = "".join(c for c in self.number if c.isdigit())
        super().save(*args, **kwargs)
        if self.is_primary:
            PaymentCard.objects.exclude(pk=self.pk).update(is_primary=False)

    @property
    def last4(self):
        return self.number[-4:]

    @property
    def spaced(self):
        return " ".join(self.number[i:i + 4] for i in range(0, len(self.number), 4))

    def __str__(self):
        return f"{self.bank} •••• {self.last4} · {self.holder}" + (" (asosiy)" if self.is_primary else "")


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Tasdiq kutilmoqda"
        PAID = "paid", "To'langan"
        CANCELLED = "cancelled", "Bekor qilingan"

    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="payments")
    kind = models.CharField("Turi", max_length=8)  # plan | shop
    plan = models.ForeignKey(Plan, null=True, blank=True, on_delete=models.SET_NULL)
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL, related_name="payments")
    amount = models.BigIntegerField("Summa")
    discount = models.BigIntegerField("Chegirma", default=0)
    promo = models.CharField("Promokod", max_length=20, blank=True)
    method = models.CharField("Usul", max_length=8)
    status = models.CharField("Holat", max_length=10, choices=Status.choices)
    gateway_ref = models.CharField("Gateway tranzaksiya", max_length=40, blank=True)
    pay_card = models.ForeignKey(PaymentCard, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Qaysi kartaga")
    card_last4 = models.CharField("Karta oxirgi 4 raqami", max_length=4, blank=True)
    sender_last4 = models.CharField("Jo'natuvchi kartasi (oxirgi 4)", max_length=4, blank=True)
    proof_at = models.DateTimeField("A'zo to'lov qildim degan vaqt", null=True, blank=True)
    created = models.DateTimeField("Sana", auto_now_add=True)

    class Meta:
        ordering = ["-created"]
        verbose_name, verbose_name_plural = "To'lov", "To'lovlar"

    @property
    def reference(self):
        return f"P{self.pk}"

    def __str__(self):
        return f"To'lov #{self.pk} · {self.amount:,}".replace(",", " ")


class Visit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="visits")
    ts = models.DateTimeField("Vaqt", auto_now_add=True)

    class Meta:
        ordering = ["-ts"]
        verbose_name, verbose_name_plural = "Tashrif", "Tashriflar"


class Trainer(models.Model):
    name = models.CharField("Ism", max_length=60)
    specialty = models.CharField("Yo'nalish", max_length=80)
    bio = models.TextField("Tanishtiruv", blank=True)
    experience_years = models.PositiveSmallIntegerField("Tajriba (yil)", default=1)
    photo = models.FileField("Rasm (jpg, png, webp)", upload_to="trainers/", blank=True, validators=[validate_image])
    photo_url = models.URLField("Yoki rasm havolasi (https)", blank=True, validators=[RegexValidator(r"^https://", "Faqat https:// havola")])
    pt_price = models.BigIntegerField("Shaxsiy mashg'ulot narxi (so'm)", default=0)
    active = models.BooleanField(default=True)
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="trainer_profile",
                                verbose_name="Saytdagi akkaunti",
                                help_text="Shu a'zo «Murabbiy» bo'lib kirsa, murabbiy paneli ochiladi: mijozlari, mashg'ulotlari, reja tuzish.")

    class Meta:
        verbose_name, verbose_name_plural = "Murabbiy", "Murabbiylar"

    def __str__(self):
        return self.name

    @property
    def image_src(self):
        return image_url("trainer", self) or self.photo_url


class GymClass(models.Model):
    WEEKDAYS = [(0, "Dushanba"), (1, "Seshanba"), (2, "Chorshanba"), (3, "Payshanba"), (4, "Juma"), (5, "Shanba"), (6, "Yakshanba")]
    name = models.CharField("Mashg'ulot", max_length=60)
    trainer = models.ForeignKey(Trainer, null=True, blank=True, on_delete=models.SET_NULL)
    weekday = models.PositiveSmallIntegerField("Hafta kuni", choices=WEEKDAYS)
    start_time = models.TimeField("Boshlanish")
    duration_min = models.PositiveSmallIntegerField("Davomiyligi (daqiqa)", default=60)
    capacity = models.PositiveSmallIntegerField("Joylar soni", default=15)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["weekday", "start_time"]
        verbose_name, verbose_name_plural = "Guruh mashg'uloti", "Guruh mashg'ulotlari"

    def __str__(self):
        return f"{self.name} · {self.get_weekday_display()} {self.start_time:%H:%M}"

    def next_date(self):
        now = timezone.localtime()
        days = (self.weekday - now.weekday()) % 7
        if days == 0 and self.start_time <= now.time():
            days = 7
        return now.date() + timedelta(days=days)


class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings")
    gym_class = models.ForeignKey(GymClass, on_delete=models.CASCADE, related_name="bookings")
    date = models.DateField("Sana")
    reminded = models.BooleanField(default=False, editable=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "gym_class", "date")]
        ordering = ["date"]
        verbose_name, verbose_name_plural = "Bron", "Bronlar"


class Announcement(models.Model):
    title = models.CharField("Sarlavha", max_length=100)
    body = models.TextField("Matn")
    pinned = models.BooleanField("Tepada turadi", default=False)
    active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-pinned", "-created"]
        verbose_name, verbose_name_plural = "E'lon", "E'lonlar"

    def __str__(self):
        return self.title


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField("Baho", validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField("Fikr", max_length=500, blank=True)
    approved = models.BooleanField("Tasdiqlangan", default=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
        verbose_name, verbose_name_plural = "Fikr", "Fikrlar"


class BodyLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bodylogs")
    date = models.DateField("Sana", default=timezone.localdate)
    weight = models.DecimalField("Vazn (kg)", max_digits=5, decimal_places=1, validators=[MinValueValidator(Decimal("20")), MaxValueValidator(400)])
    height_cm = models.PositiveSmallIntegerField("Bo'y (sm)", null=True, blank=True, validators=[MinValueValidator(100), MaxValueValidator(250)])
    note = models.CharField("Izoh", max_length=120, blank=True)

    class Meta:
        ordering = ["date", "id"]
        verbose_name, verbose_name_plural = "Tana o'lchami", "Tana o'lchamlari"

    @property
    def bmi(self):
        if not self.height_cm:
            return None
        return round(float(self.weight) / ((self.height_cm / 100) ** 2), 1)


class OtpCode(models.Model):
    """One-time SMS codes. Only a hash is stored; codes expire after 10 minutes and allow 5 attempts."""
    phone = models.CharField(max_length=13, db_index=True)
    purpose = models.CharField(max_length=8)  # reset | verify
    code_hash = models.CharField(max_length=64)
    attempts = models.PositiveSmallIntegerField(default=0)
    used = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]


class WorkoutPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="workout_plans")
    trainer = models.ForeignKey(Trainer, null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField("Reja nomi", max_length=80)
    notes = models.TextField("Izoh", blank=True)
    active = models.BooleanField("Joriy reja", default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-active", "-created"]
        verbose_name, verbose_name_plural = "Mashq rejasi", "Mashq rejalari"

    def __str__(self):
        return f"{self.title} · {self.user.full_name}"


class Exercise(models.Model):
    plan = models.ForeignKey(WorkoutPlan, on_delete=models.CASCADE, related_name="exercises")
    weekday = models.PositiveSmallIntegerField("Hafta kuni", choices=GymClass.WEEKDAYS)
    name = models.CharField("Mashq", max_length=80)
    sets = models.PositiveSmallIntegerField("Yondashuv", default=3)
    reps = models.CharField("Takror", max_length=20, default="10")
    note = models.CharField("Izoh", max_length=120, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["weekday", "order", "id"]
        verbose_name, verbose_name_plural = "Mashq", "Mashqlar"

    def __str__(self):
        return self.name


class ExerciseLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="exercise_logs")
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name="logs")
    date = models.DateField(default=timezone.localdate)

    class Meta:
        unique_together = [("exercise", "date")]


class PTSession(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "So'ralgan"
        CONFIRMED = "confirmed", "Tasdiqlangan"
        CANCELLED = "cancelled", "Bekor qilingan"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pt_sessions")
    trainer = models.ForeignKey(Trainer, on_delete=models.CASCADE, related_name="pt_sessions")
    starts = models.DateTimeField("Vaqt")
    note = models.CharField("Izoh", max_length=200, blank=True)
    status = models.CharField("Holat", max_length=10, choices=Status.choices, default=Status.REQUESTED)
    reminded = models.BooleanField(default=False, editable=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["starts"]
        verbose_name, verbose_name_plural = "Shaxsiy mashg'ulot", "Shaxsiy mashg'ulotlar"


class WorkoutType(models.Model):
    """A kind of training (strength, cardio, yoga, ...). Lessons belong to one."""
    name = models.CharField("Nomi", max_length=40)
    description = models.CharField("Qisqacha tavsif", max_length=200, blank=True)
    order = models.PositiveSmallIntegerField("Tartib", default=0)
    active = models.BooleanField("Ko'rinadi", default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name, verbose_name_plural = "Mashg'ulot turi", "Mashg'ulot turlari"

    def __str__(self):
        return self.name


class Lesson(models.Model):
    """A training lesson: a video and/or step-by-step instructions, tied to a weekday (or every day)."""
    LEVELS = [("beginner", "Boshlang'ich"), ("intermediate", "O'rta"), ("advanced", "Yuqori")]
    title = models.CharField("Sarlavha", max_length=100)
    workout_type = models.ForeignKey(WorkoutType, null=True, blank=True, on_delete=models.SET_NULL, related_name="lessons", verbose_name="Turi")
    weekday = models.PositiveSmallIntegerField("Hafta kuni", null=True, blank=True, choices=GymClass.WEEKDAYS,
                                               help_text="Bo'sh qoldirsangiz, dars har kuni ko'rinadi.")
    level = models.CharField("Daraja", max_length=12, choices=LEVELS, default="beginner")
    duration_min = models.PositiveSmallIntegerField("Davomiyligi (daqiqa)", default=20)
    summary = models.CharField("Qisqacha", max_length=200, blank=True)
    video_url = models.URLField("Video havolasi (YouTube, Vimeo yoki .mp4, https)", blank=True, validators=[validate_video_url])
    video_file = models.FileField("Video fayl (mp4 yoki webm)", upload_to="lessons/", blank=True, validators=[validate_video_file], storage=video_storage,
                                  help_text="Saytga yuklanadi va faqat ruxsati borlarga ko'rsatiladi. Katta fayl uchun YouTube havolasi qulayroq.")
    steps = models.TextField("Qanday bajariladi (har qatorda bitta qadam)", blank=True)
    muscles = models.CharField("Ishlaydigan mushaklar", max_length=120, blank=True)
    equipment = models.CharField("Jihoz", max_length=120, blank=True)
    tips = models.TextField("Xatolar va maslahatlar (har qatorda bittadan)", blank=True)
    active = models.BooleanField("Ko'rinadi", default=True)
    order = models.PositiveSmallIntegerField("Tartib", default=0)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name, verbose_name_plural = "Dars", "Darslar"

    def __str__(self):
        return self.title

    @property
    def has_video(self):
        return bool(self.video_file or self.video_url)

    @property
    def step_list(self):
        return [ln.strip() for ln in self.steps.splitlines() if ln.strip()]

    @property
    def tip_list(self):
        return [ln.strip() for ln in self.tips.splitlines() if ln.strip()]


class Notification(models.Model):
    """A personal message to one member: written by the admin, or sent by the system (birthday, plan, low stock...)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    sender = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="Kimdan")
    title = models.CharField("Sarlavha", max_length=120)
    body = models.TextField("Matn", max_length=2000, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField("O'qilgan", null=True, blank=True)

    class Meta:
        ordering = ["-created"]
        verbose_name, verbose_name_plural = "Shaxsiy xabar", "Shaxsiy xabarlar"

    def __str__(self):
        return self.title


class PersonalRecord(models.Model):
    """A member's best lift on a day; the estimated one-rep max (Epley) lets different rep counts be compared."""
    LIFTS = [("bench", "Jim yotib itarish (Bench press)"), ("squat", "O'tirib turish (Squat)"), ("deadlift", "Stanovoy (Deadlift)"),
             ("ohp", "Yelka uchun itarish (OHP)"), ("pullup", "Turnikda tortilish (Pull-up)"), ("row", "Shtanga bilan eshkak (Row)")]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="records")
    lift = models.CharField("Mashq", max_length=10, choices=LIFTS)
    weight = models.DecimalField("Og'irlik (kg)", max_digits=5, decimal_places=1, validators=[MinValueValidator(Decimal("0")), MaxValueValidator(500)])
    reps = models.PositiveSmallIntegerField("Takror", default=1, validators=[MinValueValidator(1), MaxValueValidator(30)])
    date = models.DateField("Sana", default=timezone.localdate)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name, verbose_name_plural = "Shaxsiy rekord", "Shaxsiy rekordlar"

    @property
    def one_rm(self):
        w = float(self.weight)
        return round(w if self.reps == 1 else w * (1 + self.reps / 30), 1)


class WaterLog(models.Model):
    """Glasses of water a member ticked off on a day (the dashboard's water tracker)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="water_logs")
    date = models.DateField(default=timezone.localdate)
    glasses = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = [("user", "date")]
        verbose_name, verbose_name_plural = "Suv hisobi", "Suv hisoblari"


class ChatRoom(models.Model):
    """A public room or a private conversation between two members (user_a.pk < user_b.pk)."""
    class Kind(models.TextChoices):
        ROOM = "room", "Xona"
        DIRECT = "direct", "Shaxsiy"

    kind = models.CharField(max_length=8, choices=Kind.choices)
    slug = models.SlugField(null=True, blank=True, unique=True)
    title = models.CharField(max_length=60, blank=True)
    user_a = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name="+")
    user_b = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name="+")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user_a", "user_b")]
        verbose_name, verbose_name_plural = "Chat xonasi", "Chat xonalari"

    def __str__(self):
        return self.title or f"{self.user_a} / {self.user_b}"

    def other(self, user):
        return self.user_b if self.user_a_id == user.pk else self.user_a


class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_messages")
    body = models.TextField("Xabar", max_length=1000, blank=True)
    image = models.FileField("Rasm", upload_to="chat/%Y/%m/", blank=True, validators=[validate_image])
    deleted = models.BooleanField("O'chirilgan", default=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["room", "id"])]
        verbose_name, verbose_name_plural = "Chat xabari", "Chat xabarlari"

    def __str__(self):
        return f"{self.sender}: {self.body[:40]}"


class ChatRead(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="+")
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="+")
    last_id = models.BigIntegerField(default=0)

    class Meta:
        unique_together = [("user", "room")]


class ChatBlock(models.Model):
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_blocks")
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name="+")

    class Meta:
        unique_together = [("blocker", "blocked")]


class ChatReport(models.Model):
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="+")
    reason = models.CharField("Sabab", max_length=200, blank=True)
    resolved = models.BooleanField("Ko'rib chiqilgan", default=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("message", "reporter")]
        ordering = ["resolved", "-created"]
        verbose_name, verbose_name_plural = "Chat shikoyati", "Chat shikoyatlari"


class AIMessage(models.Model):
    """One turn of a member's conversation with the AI coach (kept so the coach remembers earlier questions)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ai_messages")
    role = models.CharField(max_length=10, choices=[("user", "A'zo"), ("assistant", "AI")])
    content = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        verbose_name, verbose_name_plural = "AI xabar", "AI xabarlar"


class FoodEntry(models.Model):
    """One thing a member ate (calorie tracker). The numbers are for the whole portion, not per 100 g."""
    MEALS = [("breakfast", "Nonushta"), ("lunch", "Tushlik"), ("dinner", "Kechki ovqat"), ("snack", "Perekus")]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="food_entries")
    date = models.DateField("Sana", default=timezone.localdate, db_index=True)
    meal = models.CharField("Ovqat vaqti", max_length=10, choices=MEALS, default="snack")
    name = models.CharField("Nomi", max_length=80)
    grams = models.PositiveIntegerField("Gramm", validators=[MinValueValidator(1), MaxValueValidator(5000)])
    kcal = models.DecimalField("Kaloriya", max_digits=7, decimal_places=1, default=0)
    protein = models.DecimalField("Oqsil (g)", max_digits=6, decimal_places=1, default=0)
    fat = models.DecimalField("Yog' (g)", max_digits=6, decimal_places=1, default=0)
    carbs = models.DecimalField("Uglevod (g)", max_digits=6, decimal_places=1, default=0)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "id"]
        verbose_name, verbose_name_plural = "Ovqat yozuvi", "Ovqat yozuvlari"

    def __str__(self):
        return f"{self.name} {self.grams} g"
