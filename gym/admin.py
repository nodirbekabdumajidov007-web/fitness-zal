import csv

from django.contrib import admin, messages
from django.db.models import Count, F, Max, Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from . import extras, services, telegram
from .models_tracker import TrackerGoal, WorkoutSession
from .models import (Announcement, BodyLog, Booking, Category, ChatMessage, ChatReport, Exercise, GymClass, GymSettings, Membership, Order, OrderItem, Payment, PaymentCard, Plan,
                     AdminQuery, ClassWaitlist, EntryLog, FaqItem, GiftCertificate, GuestPass, LegalPage, MembershipFreeze, ReferralReward, TrainerReview,
                     AIMessage, FoodEntry, Notification, PersonalRecord, Product, PromoCode, PTSession, PushSubscription, Review, Trainer, User, UserFood, Visit, WorkoutPlan)


def export_csv(modeladmin, request, queryset, fields, name):
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{name}.csv"'
    resp.write("﻿")  # Excel-friendly UTF-8
    w = csv.writer(resp)
    w.writerow(fields)
    for obj in queryset:
        row = []
        for f in fields:
            v = getattr(obj, f)
            v = v() if callable(v) else v
            v = "" if v is None else str(v)
            row.append("'" + v if v[:1] in ("=", "+", "-", "@") else v)  # block spreadsheet formula injection
        w.writerow(row)
    return resp


TONES = {"#1d9a52": "ok", "#c0261a": "bad", "#b97d00": "warn", "#1f5bd6": "info"}  # old colour codes -> theme-aware pill classes


def badge(text, color):
    """A status pill; the colours come from admin.css so it stays readable in the dark theme too."""
    return format_html('<span class="fz-st {}">{}</span>', TONES.get(color, "mute"), text)


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    fields = ("plan", "starts", "expires", "freeze_used", "frozen_until")


class FreezeInline(admin.TabularInline):
    model = MembershipFreeze
    extra = 0
    can_delete = False
    fields = ("start_date", "end_date", "planned_days", "ended_early")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class BodyLogInline(admin.TabularInline):
    model = BodyLog
    extra = 0
    can_delete = False


class WorkoutSessionInline(admin.TabularInline):
    """The member's logged workouts (fitness tracker), read-only in the member card."""
    model = WorkoutSession
    fields = readonly_fields = ("date", "plan_day", "note", "volume")
    extra = 0
    can_delete = False
    max_num = 0
    ordering = ("-date",)
    show_change_link = False

    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("sets")


class TrackerGoalInline(admin.TabularInline):
    model = TrackerGoal
    extra = 0
    can_delete = False
    max_num = 0
    fields = readonly_fields = ("kind", "metric", "target", "target_date", "start_value")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("code", "username", "first_name", "last_name", "phone", "email", "state", "until", "created", "card")
    list_filter = ("is_active", "chat_banned", "is_staff", "phone_verified", "goal", "created")
    search_fields = ("username", "phone", "email", "first_name", "last_name", "referral_code")
    readonly_fields = ("last_login", "created", "referral_code", "referred_by", "referral_rewarded", "telegram_chat_id")
    # the password hash is never shown: it is useless to read and members change passwords on the site
    fieldsets = (
        ("Shaxsiy ma'lumotlar", {"fields": ("username", ("first_name", "last_name"), ("phone", "phone_verified"), "email")}),
        ("Holat", {"fields": ("is_active", ("chat_banned", "chat_visible"), "show_in_leaderboard", "staff_note")}),
        ("Maqsad", {"fields": (("goal", "target_weight"), ("birth_date", "sex"))}),
        ("Huquqlar", {"fields": (("is_staff", "is_superuser"),)}),
        ("Taklif va Telegram", {"fields": (("referral_code", "referred_by", "referral_rewarded"), "telegram_chat_id"), "classes": ("collapse",)}),
        ("Tizim", {"fields": (("created", "last_login"),), "classes": ("collapse",)}),
    )
    change_form_template = "admin/gym/user/change_form.html"

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        f = form.base_fields
        if "is_superuser" in f:
            f["is_superuser"].label, f["is_superuser"].help_text = "Bosh admin", "Barcha huquqlarga ega: sozlamalar, to'lovlar, xodimlar."
        if "is_staff" in f:
            f["is_staff"].help_text = "Qabulxona va admin panelga kira oladi (parol oxiriga .admin)."
        return form
    inlines = [MembershipInline, BodyLogInline, TrackerGoalInline, WorkoutSessionInline]
    actions = ["message", "extend_30", "block", "unblock", "csv"]
    list_per_page = 40

    @admin.action(description="Tanlanganlarga shaxsiy xabar yozish")
    def message(self, request, qs):
        from django.shortcuts import redirect
        from django.urls import reverse
        ids = ",".join(str(pk) for pk in qs.values_list("pk", flat=True)[:300])
        return redirect(f"{reverse('admin:message')}?ids={ids}")

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_until=Max("memberships__expires"))

    @admin.display(description="Raqam", ordering="id")
    def code(self, o):
        return o.member_code

    @admin.display(description="Holat")
    def state(self, o):
        if not o.is_active:
            return badge("Bloklangan", "#c0261a")
        return badge("Faol", "#1d9a52") if o._until and o._until > timezone.now() else badge("Abonementsiz", "#888")

    @admin.display(description="Abonement tugashi", ordering="_until")
    def until(self, o):
        return timezone.localtime(o._until).strftime("%d.%m.%Y") if o._until else "—"

    @admin.display(description="Kartochka")
    def card(self, o):
        from django.urls import reverse
        return format_html('<a class="fz-mini" href="{}">Ochish →</a>', reverse("admin:member", args=[o.pk]))

    def has_add_permission(self, request):
        return False  # accounts are created on the site, where passwords are hashed

    @admin.action(description="Tanlanganlarga +30 kun qo'shish")
    def extend_30(self, request, qs):
        n = sum(1 for u in qs.filter(is_superuser=False) if services.extend_member(u, 30))
        self.message_user(request, f"{n} ta a'zoga 30 kun qo'shildi.", messages.SUCCESS)

    @admin.action(description="Bloklash")
    def block(self, request, qs):
        self.message_user(request, f"{qs.filter(is_superuser=False).update(is_active=False)} ta a'zo bloklandi.")

    @admin.action(description="Blokdan chiqarish")
    def unblock(self, request, qs):
        self.message_user(request, f"{qs.update(is_active=True)} ta a'zo ochildi.")

    @admin.action(description="CSV ga yuklab olish")
    def csv(self, request, qs):
        return export_csv(self, request, qs, ["member_code", "first_name", "last_name", "phone", "email", "created"], "azolar")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("ref", "user", "kind", "plan", "amount", "discount", "method", "state", "proof", "created")
    list_filter = ("status", "kind", "method", "created")
    search_fields = ("user__phone", "user__first_name", "user__last_name", "promo", "sender_last4", "id")
    date_hierarchy = "created"
    actions = ["confirm", "reject", "cancel", "csv"]

    @admin.display(description="Kod", ordering="id")
    def ref(self, o):
        return o.reference

    @admin.display(description="A'zo xabari")
    def proof(self, o):
        if o.method != "card":
            return "—"
        return badge(f"••••{o.sender_last4} {timezone.localtime(o.proof_at):%d.%m %H:%M}", "#1d9a52") if o.proof_at else badge("xabar yo'q", "#888")

    @admin.action(description="Rad etish (pul tushmagan): buyurtma bo'lsa mahsulot omborga qaytadi")
    def reject(self, request, qs):
        n = sum(1 for p in qs if services.cancel_payment(p, notify=True))
        self.message_user(request, f"{n} ta to'lov rad etildi.")
    list_select_related = ("user", "plan")

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in Payment._meta.fields]  # money records are changed only through actions

    def has_add_permission(self, request):
        return False

    @admin.display(description="Holat", ordering="status")
    def state(self, o):
        return badge(o.get_status_display(), {"paid": "#1d9a52", "pending": "#b97d00"}.get(o.status, "#888"))

    @admin.action(description="To'lovni tasdiqlash (abonementni faollashtiradi)")
    def confirm(self, request, qs):
        n = sum(1 for p in qs if services.confirm_payment(p))
        self.message_user(request, f"{n} ta to'lov tasdiqlandi.", messages.SUCCESS)

    @admin.action(description="Kutilayotgan to'lovni bekor qilish")
    def cancel(self, request, qs):
        self.message_user(request, f"{qs.filter(status='pending').update(status='cancelled')} ta to'lov bekor qilindi.")

    @admin.action(description="CSV ga yuklab olish")
    def csv(self, request, qs):
        return export_csv(self, request, qs, ["id", "user", "kind", "plan", "amount", "discount", "promo", "method", "status", "created"], "tolovlar")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("product", "name", "price", "qty")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "total", "method", "how", "state", "created")
    list_filter = ("status", "delivery", "method", "created")
    list_select_related = ("user",)
    date_hierarchy = "created"
    search_fields = ("id", "user__phone", "user__first_name", "user__last_name", "address", "delivery_phone")
    inlines = [OrderItemInline]
    readonly_fields = ("user", "total", "delivery_fee", "method", "created", "shipped_at", "done_at")
    fieldsets = ((None, {"fields": ("user", ("total", "delivery_fee"), "method", "status", ("created", "shipped_at", "done_at"))}),
                 ("Yetkazib berish", {"fields": ("delivery", "address", "delivery_phone", "delivery_note")}))
    actions = ["shipped", "handed_over", "cancel"]

    def has_add_permission(self, request):
        return False

    @admin.display(description="Holat", ordering="status")
    def state(self, o):
        return badge(o.get_status_display(), {"new": "#b97d00", "shipping": "#1f5bd6", "done": "#1d9a52"}.get(o.status, "#888"))

    @admin.display(description="Olish", ordering="delivery")
    def how(self, o):
        return format_html("Kuryer: {}", o.address[:40]) if o.delivery == Order.Delivery.COURIER else "Zaldan olib ketadi"

    @admin.action(description="Yo'lga chiqdi (kuryer olib ketdi)")
    def shipped(self, request, qs):
        self.message_user(request, f"{sum(1 for o in qs if services.ship_order(o))} ta buyurtma yo'lga chiqdi.", messages.SUCCESS)

    @admin.action(description="Berildi deb belgilash (naqd to'lov qabul qilingan)")
    def handed_over(self, request, qs):
        self.message_user(request, f"{sum(1 for o in qs if services.hand_over(o))} ta buyurtma berildi.", messages.SUCCESS)

    @admin.action(description="Bekor qilish (mahsulot omborga qaytadi)")
    def cancel(self, request, qs):
        n = 0
        for o in qs.filter(status__in=(Order.Status.NEW, Order.Status.SHIPPING)):
            for it in o.items.exclude(product=None):
                Product.objects.filter(pk=it.product_id).update(stock=F("stock") + it.qty)
            o.payments.filter(status="pending").update(status="cancelled")
            o.status = Order.Status.CANCELLED
            o.save(update_fields=["status"])
            n += 1
        self.message_user(request, f"{n} ta buyurtma bekor qilindi.")


def thumb_html(src, size=48):
    return format_html('<img src="{}" alt="" style="height:{}px;width:{}px;object-fit:cover;border-radius:6px">', src, size, size) if src else "—"


class LowStockFilter(admin.SimpleListFilter):
    title = "Ombor"
    parameter_name = "zaxira"

    def lookups(self, request, model_admin):
        return [("low", "Kam qolgan"), ("out", "Tugagan")]

    def queryset(self, request, qs):
        if self.value() == "low":
            return qs.filter(stock__lte=GymSettings.load().low_stock_threshold)
        if self.value() == "out":
            return qs.filter(stock=0)
        return qs


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("thumb", "name", "category", "price", "stock", "need", "active")
    list_display_links = ("thumb", "name")
    list_editable = ("price", "stock", "active")
    list_filter = (LowStockFilter, "category", "active")
    search_fields = ("name",)
    actions = ["restock_to_need", "restock", "alert_now"]
    fields = ("name", "category", "price", "stock", "active", "image", "image_url", "preview", "description")
    readonly_fields = ("preview",)

    @admin.display(description="Rasm")
    def thumb(self, o):
        return thumb_html(o.image_src)

    @admin.display(description="Ko'rinishi")
    def preview(self, o):
        return thumb_html(o.image_src, 160) if o.pk else "—"

    def save_model(self, request, obj, form, change):
        if obj.stock > GymSettings.load().low_stock_threshold:
            obj.low_alert_on = None  # back on the shelf: the next shortage will be reported again
        super().save_model(request, obj, form, change)

    @admin.display(description="Olib kelish kerak")
    def need(self, o):
        if o.stock > GymSettings.load().low_stock_threshold:
            return format_html('<span class="fz-need ok">yetarli</span>')
        n, sold = services.restock_need(o)
        return format_html('<span class="fz-need" title="30 kunda {} ta sotildi">+{} ta</span>', sold, n)

    # a restock clears the "already alerted today" mark, so the next shortage is reported again
    @admin.action(description="Kerakli miqdorgacha to'ldirish (2 haftalik savdo)")
    def restock_to_need(self, request, qs):
        th, n = GymSettings.load().low_stock_threshold, 0
        for p in qs:
            if p.stock <= th:
                Product.objects.filter(pk=p.pk).update(stock=F("stock") + services.restock_need(p)[0], low_alert_on=None)
                n += 1
        self.message_user(request, f"{n} ta mahsulot to'ldirildi." if n else "Tanlanganlar orasida kam qolgani yo'q.", messages.SUCCESS if n else messages.INFO)

    @admin.action(description="Ombor +10")
    def restock(self, request, qs):
        qs.update(stock=F("stock") + 10, low_alert_on=None)

    @admin.action(description="Kam qolganlar haqida hozir SMS yuborish")
    def alert_now(self, request, qs):
        qs.update(low_alert_on=None)
        n = len(services.check_low_stock(list(qs)))
        self.message_user(request, f"{n} ta mahsulot haqida adminga xabar ketdi." if n else "Tanlanganlarning hammasi yetarli, xabar kerak emas.")


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    search_fields = ("name", "code")
    list_filter = ("active",)
    list_display = ("name", "code", "months", "price", "guest_passes", "active", "order")
    list_editable = ("price", "guest_passes", "active", "order")


@admin.register(PromoCode)
class PromoAdmin(admin.ModelAdmin):
    search_fields = ("code",)
    list_filter = ("active",)
    list_display = ("code", "percent", "valid_until", "used", "max_uses", "active")
    list_editable = ("active",)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("user", "rating", "short", "approved", "created")
    list_filter = ("approved", "rating")
    list_select_related = ("user",)
    search_fields = ("comment", "user__first_name", "user__last_name", "user__phone")
    actions = ["approve", "hide"]

    @admin.display(description="Fikr")
    def short(self, o):
        return o.comment[:60]

    @admin.action(description="Tasdiqlash (saytda chiqadi)")
    def approve(self, request, qs):
        qs.update(approved=True)

    @admin.action(description="Yashirish")
    def hide(self, request, qs):
        qs.update(approved=False)


@admin.register(GymClass)
class GymClassAdmin(admin.ModelAdmin):
    list_display = ("name", "trainer", "weekday", "start_time", "duration_min", "capacity", "active")
    list_filter = ("weekday", "trainer", "active")
    list_select_related = ("trainer",)
    search_fields = ("name",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("user", "gym_class", "date", "no_show", "checked_in_at", "created")
    list_filter = ("no_show", "date", "gym_class")
    actions = ["mark_noshow", "mark_came"]
    list_select_related = ("user", "gym_class")
    search_fields = ("user__phone", "user__first_name", "user__last_name", "gym_class__name")
    raw_id_fields = ("user",)
    date_hierarchy = "date"

    @admin.action(description="Kelmadi deb belgilash")
    def mark_noshow(self, request, qs):
        for b in qs:
            extras.mark_booking(b, "noshow")

    @admin.action(description="Keldi deb belgilash")
    def mark_came(self, request, qs):
        for b in qs:
            extras.mark_booking(b, "came")


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ("user", "ts")
    list_select_related = ("user",)
    date_hierarchy = "ts"
    search_fields = ("user__phone", "user__first_name", "user__last_name")
    readonly_fields = ("user", "ts")

    def has_add_permission(self, request):
        return False


GOOGLE_HELP = mark_safe(
    "<b>Google bilan kirishni ulash (bir marta, ~5 daqiqa):</b><ol style='margin:6px 0 0 18px'>"
    "<li><a href='https://console.cloud.google.com/apis/credentials' target='_blank' rel='noopener'>console.cloud.google.com → APIs &amp; Services → Credentials</a> ni oching (o'z Gmail akkauntingiz bilan).</li>"
    "<li>Birinchi marta bo'lsa: <i>OAuth consent screen</i> → External → ilova nomi «Fitnes Zal» → saqlang.</li>"
    "<li><i>Create credentials → OAuth client ID</i> → turi <b>Web application</b>.</li>"
    "<li><i>Authorized JavaScript origins</i> ga qo'shing: <code>http://localhost</code> va <code>http://localhost:8000</code> "
    "(internetga chiqqanda saytingiz manzilini ham, masalan <code>https://fitneszal.uz</code>).</li>"
    "<li>Chiqqan <b>Client ID</b> ni (…apps.googleusercontent.com) pastdagi maydonga qo'ying va saqlang.</li>"
    "<li>Saytni <b>http://localhost:8000</b> orqali oching (Google 127.0.0.1 manzilini qabul qilmaydi). Keyin «Faqat Google» ni yoqing.</li></ol>")


@admin.register(GymSettings)
class GymSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Zal", {"fields": (("open_time", "close_time"), "phone", "address", "instagram", "telegram", "telegram_bot")}),
        ("Bosh sahifa ko'rinishi", {"fields": ("hero_video",)}),
        ("Bosh sahifa: tanishuv videosi", {"fields": ("promo_video_url", "promo_video_poster"),
                                          "description": "Zal haqida qisqa video. Havolani qo'ying: YouTube (youtube.com/watch?v=..., /shorts/... yoki youtu.be/...), "
                                                         "Instagram (instagram.com/reel/... yoki /p/...) yoki to'g'ridan-to'g'ri .mp4 fayl havolasi. Havola bo'sh bo'lsa, bo'lim chiqmaydi."}),
        ("Kirish xavfsizligi", {"fields": ("google_client_id", "apple_client_id", "require_google", "login_sms_code", "require_phone_verify"), "description": GOOGLE_HELP}),
        ("Abonement va bonuslar", {"fields": (("freeze_min_days", "freeze_max_days"), "class_cancel_hours", "reminder_email", "referral_bonus_days", "referral_newcomer_percent", "revenue_goal", "gym_capacity"),
                                  "description": "Muzlatish: eng ko'p kun 0 bo'lsa, a'zolar muzlata olmaydi. Eslatmalar 7, 3 va 1 kun oldin avtomatik ketadi."}),
        ("Yetkazib berish", {"fields": ("delivery_on", ("delivery_fee", "free_delivery_from"), "delivery_area")}),
        ("Xaritada zal", {"fields": ("yandex_map_url", ("map_lat", "map_lng")),
                          "description": "Yandex Xaritada zalingizni oching → «Ulashish» → havolani nusxalab shu yerga qo'ying "
                                         "(masalan https://yandex.uz/maps/org/…/123456/). Bosh sahifada xarita va «Zalga yo'l» tugmasi chiqadi. "
                                         "Havola bo'lmasa, koordinatalar ishlatiladi."}),
        ("Ombor ogohlantirishi (SMS)", {"fields": ("low_stock_threshold", "alert_phone"),
                                        "description": "Mahsulot shu sondan kam qolsa, adminga SMS, Telegram va saytdagi xabar boradi: nima tugagani va nechta olib kelish kerakligi. "
                                                       "Har mahsulot uchun kuniga bir marta."}),
        ("Instagram Direct bot", {"fields": ("ig_auto_reply", "ig_staff_pause_hours"),
                                  "description": "Ulash bo'yicha qo'llanma: docs/INSTAGRAM.md. Xabarlar «Mijozlar bilan aloqa → Instagram xabarlari» bo'limida."}),
        ("Sinov", {"fields": ("demo_payments",), "classes": ("collapse",)}),
    )

    def has_add_permission(self, request):
        return not GymSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


class ExerciseInline(admin.TabularInline):
    model = Exercise
    extra = 3


@admin.register(WorkoutPlan)
class WorkoutPlanAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "trainer", "active", "created")
    list_filter = ("active", "trainer")
    list_select_related = ("user", "trainer")
    search_fields = ("title", "user__phone", "user__first_name", "user__last_name")
    autocomplete_fields = ("user",)
    inlines = [ExerciseInline]


@admin.register(PTSession)
class PTSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "trainer", "starts", "state", "note")
    list_filter = ("status", "trainer")
    list_select_related = ("user", "trainer")
    search_fields = ("user__phone", "user__first_name", "user__last_name", "trainer__name")
    date_hierarchy = "starts"
    actions = ["confirm", "cancel"]
    readonly_fields = ("user", "trainer", "starts", "note", "created")

    def has_add_permission(self, request):
        return False

    @admin.display(description="Holat", ordering="status")
    def state(self, o):
        return badge(o.get_status_display(), {"confirmed": "#1d9a52", "requested": "#b97d00"}.get(o.status, "#888"))

    @admin.action(description="Tasdiqlash (a'zoga Telegram xabari ketadi)")
    def confirm(self, request, qs):
        n = 0
        for s in qs.filter(status="requested").select_related("user", "trainer"):
            s.status = PTSession.Status.CONFIRMED
            s.save(update_fields=["status"])
            telegram.notify_user(s.user, "tg_pt_confirmed", trainer=s.trainer.name, time=timezone.localtime(s.starts).strftime("%d.%m %H:%M"))
            n += 1
        self.message_user(request, f"{n} ta mashg'ulot tasdiqlandi.", messages.SUCCESS)

    @admin.action(description="Bekor qilish")
    def cancel(self, request, qs):
        for s in qs.exclude(status="cancelled").select_related("user", "trainer"):
            s.status = PTSession.Status.CANCELLED
            s.save(update_fields=["status"])
            telegram.notify_user(s.user, "tg_pt_cancelled", trainer=s.trainer.name)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """Moderation view. Private conversations are NOT listed here unless someone reported a message in them, so staff cannot browse members' DMs."""
    list_display = ("id", "room_title", "sender", "short", "deleted", "reports_count", "created")
    list_filter = ("deleted", "room")
    search_fields = ("body", "sender__first_name", "sender__last_name", "sender__phone")
    readonly_fields = ("room", "sender", "body", "created")
    actions = ["hide", "ban_senders"]

    def get_queryset(self, request):
        return (super().get_queryset(request).filter(Q(room__kind="room") | Q(reports__isnull=False)).distinct()
                .select_related("room", "sender").annotate(_reports=Count("reports", distinct=True)))

    def has_add_permission(self, request):
        return False

    @admin.display(description="Xona")
    def room_title(self, o):
        return o.room.title if o.room.kind == "room" else "shaxsiy"

    @admin.display(description="Xabar")
    def short(self, o):
        if o.image and not o.deleted:
            return format_html('<a href="/chat/photo/{}/" target="_blank">[rasm]</a> {}', o.pk, o.body[:60])
        return o.body[:70]

    @admin.display(description="Shikoyat", ordering="_reports")
    def reports_count(self, o):
        return o._reports

    @admin.action(description="Xabarni yashirish (o'chirish)")
    def hide(self, request, qs):
        n = qs.update(deleted=True)
        ChatReport.objects.filter(message__in=qs).update(resolved=True)
        self.message_user(request, f"{n} ta xabar yashirildi.")

    @admin.action(description="Yuboruvchini chatdan chetlatish")
    def ban_senders(self, request, qs):
        n = User.objects.filter(pk__in=qs.values("sender")).exclude(is_superuser=True).update(chat_banned=True)
        self.message_user(request, f"{n} ta a'zo chatdan chetlatildi.")


@admin.register(ChatReport)
class ChatReportAdmin(admin.ModelAdmin):
    list_display = ("id", "reported", "reporter", "reason", "resolved", "created")
    list_filter = ("resolved",)
    list_select_related = ("message__sender", "reporter")
    search_fields = ("reason", "message__body", "reporter__first_name", "reporter__last_name")
    readonly_fields = ("message", "reporter", "reason", "created", "context")
    fields = ("resolved", "message", "reporter", "reason", "created", "context")
    actions = ["resolve", "resolve_and_hide", "resolve_and_ban"]

    def has_add_permission(self, request):
        return False

    @admin.display(description="Shikoyat qilingan")
    def reported(self, o):
        return f"{o.message.sender.full_name}: {o.message.body[:50]}"

    @admin.display(description="Suhbat (shikoyat qilingan xabar atrofi)")
    def context(self, o):
        rows = ChatMessage.objects.filter(room=o.message.room, id__gte=o.message_id - 6, id__lte=o.message_id + 3).select_related("sender").order_by("id")
        return format_html_join(mark_safe("<br>"), "{}<b>{}</b>: {}",
                                (("» " if m.id == o.message_id else "", m.sender.full_name, ("(o'chirilgan) " + m.body) if m.deleted else m.body) for m in rows))

    @admin.action(description="Ko'rib chiqildi deb belgilash")
    def resolve(self, request, qs):
        qs.update(resolved=True)

    @admin.action(description="Xabarni yashirish va belgilash")
    def resolve_and_hide(self, request, qs):
        ChatMessage.objects.filter(pk__in=qs.values("message")).update(deleted=True)
        qs.update(resolved=True)

    @admin.action(description="Yuboruvchini chetlatish, xabarni yashirish va belgilash")
    def resolve_and_ban(self, request, qs):
        senders = User.objects.filter(chat_messages__reports__in=qs).exclude(is_superuser=True)
        senders.update(chat_banned=True)
        ChatMessage.objects.filter(pk__in=qs.values("message")).update(deleted=True)
        qs.update(resolved=True)


@admin.register(PaymentCard)
class PaymentCardAdmin(admin.ModelAdmin):
    list_display = ("bank", "masked", "holder", "is_primary", "active")
    search_fields = ("bank", "holder")
    list_editable = ("is_primary", "active")
    fields = ("bank", "number", "holder", "is_primary", "active", "note")

    @admin.display(description="Karta")
    def masked(self, o):
        return f"{o.number[:4]} •••• •••• {o.last4}"

    def has_delete_permission(self, request, obj=None):
        return False  # old payments point to their card; switch cards by adding a new one and making it primary


@admin.register(AIMessage)
class AIMessageAdmin(admin.ModelAdmin):
    """Read-only log of coach assistant conversations (shows what members ask, so missing knowledge-base topics can be added)."""
    list_display = ("user", "role", "short", "created")
    list_filter = ("role", "created")
    list_select_related = ("user",)
    search_fields = ("content", "user__username", "user__first_name", "user__phone")
    date_hierarchy = "created"

    @admin.display(description="Matn")
    def short(self, o):
        return o.content[:90]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "sender", "created", "seen")
    list_filter = ("created", ("sender", admin.EmptyFieldListFilter))
    list_select_related = ("user", "sender")
    search_fields = ("title", "body", "user__phone", "user__first_name", "user__last_name")
    raw_id_fields = ("user", "sender")
    readonly_fields = ("created", "read_at")
    date_hierarchy = "created"

    @admin.display(description="O'qildi", boolean=True)
    def seen(self, o):
        return o.read_at is not None

    def has_add_permission(self, request):
        return False  # new messages are written on the «Shaxsiy xabar» page, which also sends Telegram/SMS


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "created", "user_agent")
    list_select_related = ("user",)
    search_fields = ("user__phone", "user__first_name", "user__last_name", "user_agent")
    raw_id_fields = ("user",)
    exclude = ("endpoint", "p256dh", "auth")  # the keys are secrets of the device: never shown

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(PersonalRecord)
class PersonalRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "lift", "weight", "reps", "rm", "date")
    list_filter = ("lift", "date")
    list_select_related = ("user",)
    search_fields = ("user__phone", "user__first_name", "user__last_name")
    raw_id_fields = ("user",)

    @admin.display(description="1RM ≈")
    def rm(self, o):
        return o.one_rm


@admin.register(Trainer)
class TrainerAdmin(admin.ModelAdmin):
    list_display = ("thumb", "name", "specialty", "experience_years", "pt_price", "account", "active")
    list_display_links = ("thumb", "name")
    list_editable = ("active",)
    list_select_related = ("user",)
    search_fields = ("name", "specialty")
    list_filter = ("active",)
    fields = ("name", "specialty", "experience_years", "pt_price", "active", "user", "photo", "preview", "photo_url", "bio")
    readonly_fields = ("preview",)
    raw_id_fields = ("user",)  # picks the member account by id/search instead of loading every member into a dropdown

    @admin.display(description="Kirish (murabbiy paneli)")
    def account(self, o):
        return format_html("Ulangan: {}", o.user.phone or o.user.email or o.user.username) if o.user_id else "—"

    @admin.display(description="Rasm")
    def thumb(self, o):
        return thumb_html(o.image_src)

    @admin.display(description="Ko'rinishi")
    def preview(self, o):
        return thumb_html(o.image_src, 160) if o.pk else "—"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "order")
    list_editable = ("order",)
    search_fields = ("name",)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "pinned", "active", "created")
    list_editable = ("pinned", "active")
    list_filter = ("active", "pinned", "created")
    search_fields = ("title", "body")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "starts", "expires", "state", "freeze_used")
    list_filter = ("plan", "freeze_used", "expires")
    list_select_related = ("user", "plan")
    search_fields = ("user__phone", "user__first_name", "user__last_name", "user__username")
    raw_id_fields = ("user",)  # a dropdown with every member would be slow and endless
    date_hierarchy = "expires"
    inlines = [FreezeInline]
    actions = ["end_freeze"]

    @admin.action(description="Muzlatishni tugatish (ishlatilmagan kunlar qaytariladi)")
    def end_freeze(self, request, qs):
        n = 0
        for m in qs:
            for fr in m.freezes.all():
                n += bool(extras.end_freeze_row(fr))
        self.message_user(request, f"Tugatilgan muzlatishlar: {n}")

    @admin.display(description="Holat")
    def state(self, o):
        now = timezone.now()
        if o.expires <= now:
            return badge("Tugagan", "#888")
        return badge("Faol", "#1d9a52") if o.starts <= now else badge("Boshlanmagan", "#b97d00")


@admin.register(BodyLog)
class BodyLogAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "weight", "height_cm", "waist", "body_fat", "note")
    list_filter = ("date",)
    list_select_related = ("user",)
    search_fields = ("user__phone", "user__first_name", "user__last_name", "note")
    raw_id_fields = ("user",)
    date_hierarchy = "date"


@admin.register(FoodEntry)
class FoodEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "meal", "name", "grams", "kcal")
    list_filter = ("meal", "date")
    list_select_related = ("user",)
    search_fields = ("name", "user__username", "user__first_name", "user__last_name")
    autocomplete_fields = ()
    raw_id_fields = ("user",)


@admin.register(UserFood)
class UserFoodAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "kcal", "protein", "fat", "carbs", "portion_g", "created")
    list_filter = ("created",)
    list_select_related = ("user",)
    search_fields = ("name", "user__username", "user__first_name", "user__last_name")
    raw_id_fields = ("user",)


# ---------------------------------------------------------------- retention features
@admin.register(MembershipFreeze)
class MembershipFreezeAdmin(admin.ModelAdmin):
    list_display = ("member", "start_date", "end_date", "planned_days", "state_pill", "ended_early")
    list_filter = ("ended_early", "start_date")
    search_fields = ("membership__user__first_name", "membership__user__last_name", "membership__user__phone", "membership__user__username")
    list_select_related = ("membership", "membership__user")
    date_hierarchy = "start_date"

    def has_add_permission(self, request):
        return False  # freezes move the end date, so they are made by the member (or the membership action), never by hand

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="A'zo")
    def member(self, o):
        return o.membership.user

    @admin.display(description="Holat")
    def state_pill(self, o):
        return badge({"active": "Faol", "scheduled": "Rejalashtirilgan", "done": "Tugagan", "cancelled": "Bekor"}[o.state], {"active": "#1f5bd6", "scheduled": "#b97d00"}.get(o.state, "#888"))


@admin.register(GuestPass)
class GuestPassAdmin(admin.ModelAdmin):
    list_display = ("guest_name", "guest_phone", "owner", "date", "state_pill", "used_at", "checked_by")
    list_filter = ("date", "used_at")
    search_fields = ("guest_name", "guest_phone", "owner__first_name", "owner__last_name", "owner__phone")
    list_select_related = ("owner", "checked_by")
    raw_id_fields = ("owner", "membership", "checked_by")
    actions = ["cancel_passes"]

    @admin.display(description="Holat")
    def state_pill(self, o):
        return badge({"valid": "Amal qiladi", "today": "Bugun", "used": "Ishlatilgan", "expired": "Muddati o'tgan", "cancelled": "Bekor"}[o.state],
                     {"valid": "#1d9a52", "today": "#1d9a52", "used": "#888"}.get(o.state, "#c0261a"))

    @admin.action(description="Bekor qilish")
    def cancel_passes(self, request, qs):
        qs.filter(used_at__isnull=True, cancelled_at__isnull=True).update(cancelled_at=timezone.now())


@admin.register(ReferralReward)
class ReferralRewardAdmin(admin.ModelAdmin):
    list_display = ("referrer", "referred", "days", "created")
    list_select_related = ("referrer", "referred")
    search_fields = ("referrer__first_name", "referrer__phone", "referred__first_name", "referred__phone")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ClassWaitlist)
class ClassWaitlistAdmin(admin.ModelAdmin):
    list_display = ("user", "gym_class", "date", "created")
    list_filter = ("date", "gym_class")
    list_select_related = ("user", "gym_class")
    raw_id_fields = ("user",)


@admin.register(TrainerReview)
class TrainerReviewAdmin(admin.ModelAdmin):
    list_display = ("trainer", "user", "rating", "short", "hidden", "updated")
    list_filter = ("hidden", "rating", "trainer")
    list_editable = ("hidden",)
    list_select_related = ("trainer", "user")
    search_fields = ("comment", "user__first_name", "user__last_name", "trainer__name")
    actions = ["hide", "show"]

    @admin.display(description="Fikr")
    def short(self, o):
        return o.comment[:60]

    @admin.action(description="Yashirish (saytda ko'rinmaydi)")
    def hide(self, request, qs):
        qs.update(hidden=True)

    @admin.action(description="Ko'rsatish")
    def show(self, request, qs):
        qs.update(hidden=False)


@admin.register(GiftCertificate)
class GiftCertificateAdmin(admin.ModelAdmin):
    list_display = ("code", "what", "buyer", "expires", "state_pill", "redeemed_by", "redeemed_at")
    list_filter = ("expires", "redeemed_at")
    search_fields = ("code", "buyer__first_name", "buyer__phone", "redeemed_by__phone", "note")
    list_select_related = ("plan", "buyer", "redeemed_by", "payment")
    raw_id_fields = ("buyer", "redeemed_by", "payment")
    fields = ("code", "plan", "amount", "expires", "note", "buyer", "payment", "redeemed_by", "redeemed_at")
    readonly_fields = ("code",)

    @admin.display(description="Nima uchun")
    def what(self, o):
        return o.plan.name if o.plan_id else f"{o.amount:,} so'm".replace(",", " ")

    @admin.display(description="Holat")
    def state_pill(self, o):
        return badge({"valid": "Amal qiladi", "redeemed": "Ishlatilgan", "expired": "Muddati o'tgan", "unpaid": "To'lov kutilmoqda"}[o.state],
                     {"valid": "#1d9a52", "unpaid": "#b97d00"}.get(o.state, "#888"))

    def get_changeform_initial_data(self, request):
        return {"expires": timezone.localdate() + timezone.timedelta(days=365)}

    def save_model(self, request, obj, form, change):
        if not obj.code:
            obj.code = extras.new_gift_code()
        super().save_model(request, obj, form, change)
        self.message_user(request, f"Sertifikat kodi: {obj.code}", messages.SUCCESS)


@admin.register(FaqItem)
class FaqItemAdmin(admin.ModelAdmin):
    list_display = ("question_uz", "category", "order", "active", "votes_yes", "votes_no")
    list_editable = ("order", "active")
    list_filter = ("category", "active")
    search_fields = ("question_uz", "question_ru", "question_en", "question_tr", "question_ky", "question_tg")
    fieldsets = (("O'zbekcha", {"fields": ("question_uz", "answer_uz")}), ("Ruscha", {"fields": ("question_ru", "answer_ru")}),
                 ("Inglizcha", {"fields": ("question_en", "answer_en")}),
                 ("Turkcha", {"fields": ("question_tr", "answer_tr")}), ("Qirg'izcha", {"fields": ("question_ky", "answer_ky")}),
                 ("Tojikcha", {"fields": ("question_tg", "answer_tg")}), ("Ko'rinishi", {"fields": ("category", "order", "active")}))

    def get_queryset(self, request):  # "Was this helpful?" votes from the support widget
        return super().get_queryset(request).annotate(_yes=Count("feedback", filter=Q(feedback__helpful=True)),
                                                      _no=Count("feedback", filter=Q(feedback__helpful=False)))

    @admin.display(description="Foydali (ha)", ordering="_yes")
    def votes_yes(self, obj):
        return obj._yes

    @admin.display(description="Foydasiz (yo'q)", ordering="_no")
    def votes_no(self, obj):
        return obj._no

    def render_change_form(self, request, context, *a, **kw):
        messages.info(request, "Javobda {hours}, {phone}, {address}, {freeze_min}, {freeze_max}, {bonus}, {cancel_hours} yozsangiz, ular sozlamalardan avtomatik to'ldiriladi.")
        return super().render_change_form(request, context, *a, **kw)


@admin.register(LegalPage)
class LegalPageAdmin(admin.ModelAdmin):
    list_display = ("title_uz", "slug", "placeholders_left", "updated")
    fieldsets = (("Sahifa", {"fields": ("slug",)}), ("O'zbekcha", {"fields": ("title_uz", "body_uz")}), ("Ruscha", {"fields": ("title_ru", "body_ru")}),
                 ("Inglizcha", {"fields": ("title_en", "body_en")}))

    @admin.display(description="To'ldirilmagan [JOYLAR]")
    def placeholders_left(self, o):
        left = o.placeholders()
        return badge(f"{len(left)} ta", "#c0261a") if left else badge("Tayyor", "#1d9a52")

    def _warn(self, request):
        left = extras.legal_placeholders()
        if left:
            messages.warning(request, "DIQQAT: huquqiy matnlarda hali to'ldirilmagan joylar bor: " + ", ".join(left) +
                             ". Haqiqiy kompaniya ma'lumotlari bilan almashtiring, aks holda sayt oferta va maxfiylik siyosatida shablon matnni ko'rsatadi. Yurist ko'rigidan o'tkazing.")

    def changelist_view(self, request, extra_context=None):
        self._warn(request)
        return super().changelist_view(request, extra_context)

    def render_change_form(self, request, context, *a, **kw):
        self._warn(request)
        return super().render_change_form(request, context, *a, **kw)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EntryLog)
class EntryLogAdmin(admin.ModelAdmin):
    list_display = ("ts", "who", "method", "result_pill", "reason", "staff")
    list_filter = ("result", "method", "reason", "ts")
    search_fields = ("user__first_name", "user__last_name", "user__phone", "user__username", "guest_pass__guest_name")
    list_select_related = ("user", "staff", "guest_pass")
    date_hierarchy = "ts"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="Kim")
    def who(self, o):
        if o.guest_pass_id:
            return f"Mehmon: {o.guest_pass.guest_name} ({o.user})"
        return o.user or "—"

    @admin.display(description="Natija", ordering="result")
    def result_pill(self, o):
        return badge(o.get_result_display(), {"ok": "#1d9a52", "repeat": "#1f5bd6"}.get(o.result, "#c0261a"))


@admin.register(AdminQuery)
class AdminQueryAdmin(admin.ModelAdmin):
    """What the admins asked the AI assistant, and whether it was understood: the list to read when teaching it new phrases."""
    list_display = ("created", "text", "intent", "matched", "user")
    list_filter = ("matched", "intent", "created")
    search_fields = ("text", "intent")
    list_select_related = ("user",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(WorkoutSession)
class WorkoutSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "plan_day", "note")
    list_filter = ("date",)
    list_select_related = ("user",)
    search_fields = ("user__phone", "user__first_name", "user__last_name", "note")
    raw_id_fields = ("user",)
    date_hierarchy = "date"


@admin.register(TrackerGoal)
class TrackerGoalAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "metric", "target", "target_date")
    list_filter = ("kind",)
    list_select_related = ("user",)
    raw_id_fields = ("user",)
