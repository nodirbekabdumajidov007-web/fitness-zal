"""Fills a THROWAWAY copy of the database with realistic, fake demo data for the promo videos (tools/make_videos.py).

Never runs against the real db.sqlite3: FZ_DB must point at a copy outside the project folder.
Usage:  set FZ_DB=%TEMP%\\fzvideo\\demo.sqlite3 & set FZ_MEDIA_DIR=%TEMP%\\fzvideo\\media
        .venv\\Scripts\\python.exe tools\\video_seed.py <member_password> <admin_password>
"""
import os
import random
import sys
from datetime import datetime, time, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = os.environ.get("FZ_DB", "")
if not DB or Path(DB).resolve().parent == ROOT or ROOT in Path(DB).resolve().parents:
    sys.exit("FZ_DB must point at a temporary COPY outside the project folder")
if not os.environ.get("FZ_MEDIA_DIR"):
    sys.exit("FZ_MEDIA_DIR must point at a temporary media folder")
CODE = Path(os.environ.get("FZ_CODE_ROOT") or ROOT)  # make_videos.py seeds with the committed snapshot it serves
sys.path.insert(0, str(CODE))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402

django.setup()
from django.core.files.base import ContentFile  # noqa: E402
from django.db import transaction  # noqa: E402
from django.utils import timezone  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

from gym.models import (AIMessage, Announcement, Booking, BodyLog, ChatMessage, ChatRoom, FoodEntry, GymClass, GymSettings,  # noqa: E402
                        Membership, MessageReaction, Notification, Order, OrderItem, Payment, PersonalRecord, Plan,
                        Product, Trainer, User, Visit, WaterLog)
from gym.models_extra import EntryLog  # noqa: E402
from gym.models_instagram import IgMessage, IgThread  # noqa: E402
from gym.models_support import SupportMessage, SupportThread  # noqa: E402
from gym.models_tracker import TrackerGoal, WorkoutSession, WorkoutSet  # noqa: E402

R = random.Random(7)
TZ = timezone.get_current_timezone()
NOW = timezone.localtime()
TODAY = NOW.date()
FIRST = ["Aziz", "Dilnoza", "Javlon", "Madina", "Otabek", "Sevara", "Timur", "Nilufar", "Bobur", "Shahzoda", "Sherzod", "Kamola",
         "Farrux", "Zarina", "Ulug'bek", "Malika", "Jahongir", "Gulnoza", "Akmal", "Feruza", "Rustam", "Laylo", "Diyor", "Mohira",
         "Sanjar", "Nodira", "Islom", "Shoira", "Eldor", "Munisa", "Behruz", "Lola", "Asadbek", "Ziyoda", "Muhammadali", "Kumush",
         "Doniyor", "Hilola", "Sardorbek", "Robiya", "Abror", "Yulduz"]
LAST = ["Karimov", "Rashidova", "Ergashev", "Yo'ldosheva", "Nurmatov", "Qodirova", "Xolmatov", "Saidova", "Alimov", "Rahimova",
        "Umarov", "Ismoilova", "Jo'rayev", "Abdullayeva", "Tursunov", "Hamidova", "Qosimov", "Mirzayeva", "Sobirov", "Nazarova",
        "Ochilov", "Fayzullayeva", "Rahmonov", "Usmonova", "Valiyev", "Sharipova", "Komilov", "Ahmedova", "Hakimov", "Zokirova",
        "Raufov", "Mahmudova", "Botirov", "Ibragimova", "Yoqubov", "Olimova", "Haydarov", "Salimova", "Murodov", "Tojiyeva",
        "Shukurov", "Ortiqova"]


def at(day, hh, mm=0):
    return datetime.combine(day, time(hh, mm), tzinfo=TZ)


def set_created(model, pk, field, value):
    model.objects.filter(pk=pk).update(**{field: value})


def portrait(name, hue):
    """A clean, stylised trainer portrait (silhouette on a gradient) - no real person's photo."""
    w, h = 600, 600
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    c1, c2 = [(240, 80, 61), (34, 40, 52)], [(52, 120, 246), (20, 26, 36)]
    a, b = (c1 if hue == 0 else c2 if hue == 1 else [(46, 184, 120), (18, 30, 28)])
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3)))
    sil = Image.new("L", (w, h), 0)
    s = ImageDraw.Draw(sil)
    s.ellipse([215, 120, 385, 300], fill=255)  # head
    s.rounded_rectangle([110, 320, 490, 700], radius=150, fill=255)  # shoulders
    s.rectangle([265, 285, 335, 340], fill=255)  # neck
    sil = sil.filter(ImageFilter.GaussianBlur(2))
    img.paste(Image.new("RGB", (w, h), (16, 19, 24)), (0, 0), sil.point(lambda v: int(v * 0.82)))
    f = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 64)
    ini = "".join(p[0] for p in name.split()[:2])
    d.text((w // 2, 470), ini, font=f, fill=(255, 255, 255), anchor="mm")
    buf = BytesIO()
    img.save(buf, "JPEG", quality=88)
    return buf.getvalue()


@transaction.atomic
def run(member_pw, admin_pw):
    gs = GymSettings.load()
    gs.login_sms_code = False  # copy only: one-step sign-in for the recording
    gs.require_google = False
    gs.demo_payments = True
    gs.phone = "71 200 00 00"
    gs.instagram = "fitneszal.demo"
    gs.telegram = ""
    gs.address = "Toshkent, Chilonzor tumani"
    gs.revenue_goal = 60000000
    gs.save()

    # --- anonymise every existing account in the copy (the videos are public) ---
    ChatMessage.objects.all().delete()
    Announcement.objects.exclude(title__startswith="Yangi zal").delete()  # test leftovers
    Announcement.objects.get_or_create(title="Yangi guruh: Kross-trening", defaults={"body": "Har kuni 19:30 da. Joylar soni cheklangan - oldindan band qiling!", "active": True})
    Notification.objects.all().delete()
    AIMessage.objects.all().delete()
    Order.objects.update(address="", delivery_phone="", delivery_note="")
    used = set()
    for i, u in enumerate(User.objects.order_by("pk")):
        if u.is_superuser:
            u.first_name, u.last_name, u.username = "Admin", "Fitnes Zal", "admin"
            u.phone, u.email = "+998710000001", "admin@example.com"
            u.set_password(admin_pw)
        else:
            u.first_name, u.last_name = FIRST[(i + 20) % len(FIRST)], LAST[(i + 20) % len(LAST)]
            u.username, u.phone, u.email = f"azo{u.pk}", f"+9989300{u.pk:05d}", f"azo{u.pk}@example.com"
            u.set_unusable_password()
        u.avatar = ""
        u.telegram_chat_id = None
        u.save()
        used.add(u.pk)

    plans = {p.code: p for p in Plan.objects.all()}
    Plan.objects.filter(code="vip").update(active=True, perks="Shaxsiy murabbiy maslahati\nSauna va dush\n2 ta mehmon taklifnomasi",
                                           guest_passes=2)
    Plan.objects.filter(code="m1").update(perks="Zal 06:00-23:00\nGuruh mashg'ulotlari\nShaxsiy kuzatuv (tracker)")
    Plan.objects.filter(code="m3").update(perks="3 oy - 17% tejang\nGuruh mashg'ulotlari\nMuzlatish 14 kungacha")
    plans = {p.code: p for p in Plan.objects.all()}
    admin = User.objects.filter(is_superuser=True).first()

    # --- trainers: fake names, generated portraits, PT prices ---
    tdata = [("Sardor Rahimov", "Pauerlifting", 9, 150000, "Kuch va texnika bo'yicha 9 yillik tajriba. Shtanga, o'lik tortish, jim yotib."),
             ("Kamila Usmonova", "Yoga va stretching", 6, 120000, "Moslashuvchanlik, nafas va to'g'ri qomat. Boshlovchilar uchun ideal."),
             ("Jasur Toshmatov", "Boks va funksional", 7, 130000, "Kardio, chidamlilik va boks texnikasi. Yog' yoqish dasturlari.")]
    trainers = list(Trainer.objects.order_by("pk"))
    while len(trainers) < 3:
        trainers.append(Trainer.objects.create(name="x", specialty="x"))
    for i, (t, (nm, sp, yrs, pt, bio)) in enumerate(zip(trainers, tdata)):
        t.name, t.specialty, t.experience_years, t.pt_price, t.bio, t.active = nm, sp, yrs, pt, bio, True
        t.photo_url = ""
        t.photo.save(f"trainer{i}.jpg", ContentFile(portrait(nm, i)), save=False)
        t.save()

    # --- classes: a full schedule, several of them today ---
    GymClass.objects.all().delete()
    sched = [("Yoga", 1, time(8, 0)), ("Funksional", 2, time(10, 30)), ("Pauerlifting", 0, time(12, 0)),
             ("Boks", 2, time(17, 0)), ("Stretching", 1, time(18, 30)), ("Kross-trening", 2, time(19, 30))]
    classes_today = []
    for wd in range(7):
        for k, (nm, ti, st) in enumerate(sched):
            if wd == 6 and k > 2:
                continue
            gc = GymClass.objects.create(name=nm, trainer=trainers[ti], weekday=wd, start_time=st, duration_min=60,
                                         capacity=[12, 15, 8, 12, 14, 16][k], active=True)
            if wd == TODAY.weekday():
                classes_today.append(gc)

    # --- products: in stock, nicer descriptions ---
    stock = {"Suv 0.5 l": 60, "Suv 1.5 l": 40, "Energetik ichimlik": 25, "Izotonik ichimlik": 30, "Protein kokteyl": 18,
             "Whey protein 900 g": 12, "Proteinli batonchik": 45, "Kreatin 300 g": 9, "BCAA 200 g": 3, "Shaker": 20}
    products = list(Product.objects.all())
    for p in products:
        p.stock = stock.get(p.name, 20)
        p.save(update_fields=["stock"])

    # --- members ---
    demo = User.objects.create_user(username="aziz", email="aziz@example.com", password=member_pw, first_name="Aziz",
                                    last_name="Karimov", phone="+998900000101")
    demo.goal, demo.sex, demo.target_weight, demo.birth_date = "lose", "m", Decimal("76.0"), datetime(1998, 4, 12).date()
    demo.show_in_leaderboard = True
    demo.save()
    members = [demo]
    for i in range(46):
        fn, ln = FIRST[i % len(FIRST)], LAST[(i * 7 + 3) % len(LAST)]
        if fn == "Aziz":
            fn = "Anvar"
        u = User.objects.create_user(username=f"demo{i:02d}", email=f"demo{i:02d}@example.com", password=None, first_name=fn,
                                     last_name=ln, phone=f"+99890001{i:04d}")
        u.set_unusable_password()
        u.show_in_leaderboard = i % 3 == 0
        u.save()
        set_created(User, u.pk, "created", NOW - timedelta(days=R.randint(1, 75), hours=R.randint(0, 12)))
        members.append(u)
    set_created(User, demo.pk, "created", NOW - timedelta(days=70))

    # memberships + payments spread over 60 days
    def pay(user, plan, when, method):
        p = Payment.objects.create(user=user, kind="plan", plan=plan, amount=plan.price, method=method, status="paid", staff=admin)
        set_created(Payment, p.pk, "created", when)

    methods = ["cash", "click", "payme", "card", "click", "payme", "uzum"]
    for i, u in enumerate(members):
        code = "m3" if u is demo else R.choice(["m1", "m1", "m1", "m3", "m3", "vip"])
        plan = plans[code]
        start = at(TODAY - timedelta(days=R.randint(0, 55) if u is not demo else 34), R.randint(7, 21), R.choice([0, 15, 30, 45]))
        if i % 9 == 8:  # a few expiring soon / expired, for retention widgets
            start = at(TODAY - timedelta(days=28 + R.randint(0, 6)), 18)
            plan = plans["m1"]
        m = Membership.objects.create(user=u, plan=plan, starts=start, expires=start + timedelta(days=30 * plan.months))
        set_created(Membership, m.pk, "created", start)
        pay(u, plan, start, R.choice(methods))
        if code == "m1" and start.date() > TODAY - timedelta(days=25) and R.random() < 0.6:  # renewals earlier in the window
            prev = start - timedelta(days=30)
            Membership.objects.create(user=u, plan=plan, starts=prev, expires=start)
            pay(u, plan, prev, R.choice(methods))

    # shop orders over 60 days
    for d in range(60):
        for _ in range(R.randint(1, 4)):
            u = R.choice(members)
            items = R.sample(products, R.randint(1, 3))
            total = 0
            o = Order.objects.create(user=u, total=0, method=R.choice(["cash", "click", "payme"]), status="done", delivery="pickup")
            for p in items:
                q = R.randint(1, 3)
                OrderItem.objects.create(order=o, product=p, name=p.name, price=p.price, qty=q)
                total += p.price * q
            when = at(TODAY - timedelta(days=d), R.randint(8, 21), R.randint(0, 59))
            Order.objects.filter(pk=o.pk).update(total=total, created=when)
            pp = Payment.objects.create(user=u, kind="shop", order=o, amount=total, method=o.method, status="paid")
            set_created(Payment, pp.pk, "created", when)

    # visits (+ entry log) over 60 days: busier evenings, quieter weekends, gentle growth
    hours = [6, 7, 7, 8, 9, 10, 12, 16, 17, 17, 18, 18, 18, 19, 19, 19, 20, 20, 21]
    visits = []
    for d in range(60, -1, -1):
        day = TODAY - timedelta(days=d)
        n = int((22 + (60 - d) * 0.25) * (0.65 if day.weekday() == 6 else 1.0) * R.uniform(0.85, 1.15))
        if d == 0:
            n = 14
        for u in R.sample(members, min(n, len(members))):
            ts = at(day, R.choice(hours), R.randint(0, 59))
            if ts > NOW:
                continue
            visits.append((u, ts))
    for u, ts in visits:
        v = Visit.objects.create(user=u)
        set_created(Visit, v.pk, "ts", ts)
        if (NOW - ts).days < 3:
            EntryLog.objects.create(user=u, method=R.choice(["qr", "qr", "manual"]), result="ok", staff=admin, ts=ts)

    # bookings for today's classes
    for gc in classes_today:
        for u in R.sample(members[1:], R.randint(4, max(5, gc.capacity - 3))):
            Booking.objects.create(user=u, gym_class=gc, date=TODAY)
    if classes_today:
        Booking.objects.create(user=demo, gym_class=classes_today[-1], date=TODAY)

    # --- the demo member's own tracker data ---
    w = 84.6
    for k in range(0, 63, 3):
        day = TODAY - timedelta(days=62 - k)
        w = w - R.uniform(0.05, 0.45)
        BodyLog.objects.create(user=demo, date=day, weight=Decimal(f"{w:.1f}"), height_cm=180,
                               waist=Decimal(f"{94 - k * 0.11:.1f}"), chest=Decimal(f"{104 - k * 0.03:.1f}"),
                               arm=Decimal(f"{35 + k * 0.02:.1f}"), body_fat=Decimal(f"{22.5 - k * 0.07:.1f}"),
                               resting_hr=72 - k // 10)
    TrackerGoal.objects.create(user=demo, kind="weight", metric="weight", target=Decimal("76.0"),
                               target_date=TODAY + timedelta(days=45), start_value=Decimal("84.6"),
                               start_date=TODAY - timedelta(days=62))
    plan_ex = [("Shtanga bilan o'tirib turish (squat)", 60, 2.5), ("Jim yotib (bench press)", 50, 1.5),
               ("O'lik tortish (deadlift)", 80, 2.5), ("Turnikda tortilish", 0, 0), ("Gantel bilan yelka jimi", 14, 0.5)]
    for s_i, d in enumerate(range(60, -1, -3)):
        day = TODAY - timedelta(days=d)
        ses = WorkoutSession.objects.create(user=demo, date=day, note=R.choice(["", "Yaxshi kayfiyat", "Og'ir kun", ""]))
        for o, (ex, base, inc) in enumerate(R.sample(plan_ex, 3)):
            for st in range(3):
                WorkoutSet.objects.create(session=ses, exercise=ex, order=o * 3 + st, reps=R.choice([8, 8, 10, 6, 12]),
                                          weight=Decimal(f"{base + inc * (s_i // 2):.1f}"))
    for lift, wt, reps, ago in [("bench", 72.5, 5, 4), ("squat", 105, 5, 2), ("deadlift", 130, 3, 7), ("pullup", 0, 14, 10)]:
        PersonalRecord.objects.create(user=demo, lift=lift, weight=Decimal(str(wt)), reps=reps, date=TODAY - timedelta(days=ago))
    WaterLog.objects.create(user=demo, date=TODAY, glasses=5)
    for meal, nm, g, kc, pr, fa, ca in [("breakfast", "Suli bo'tqasi (sutda)", 250, 310, 11, 9, 46),
                                        ("breakfast", "Tuxum (qaynatilgan)", 100, 155, 13, 11, 1),
                                        ("lunch", "Tovuq go'shti (qaynatilgan)", 180, 297, 54, 7, 0),
                                        ("lunch", "Guruch (qaynatilgan)", 200, 260, 5, 1, 57),
                                        ("snack", "Olma", 180, 94, 0, 0, 25)]:
        FoodEntry.objects.create(user=demo, date=TODAY, meal=meal, name=nm, grams=g, kcal=kc, protein=pr, fat=fa, carbs=ca)
    for d in range(1, 8):
        for meal, nm, g, kc in [("breakfast", "Tvorog", 200, 240), ("lunch", "Mastava", 350, 320), ("dinner", "Tovuq va sabzavot", 350, 420)]:
            FoodEntry.objects.create(user=demo, date=TODAY - timedelta(days=d), meal=meal, name=nm, grams=g, kcal=kc + R.randint(-40, 60),
                                     protein=30, fat=12, carbs=40)

    # --- general chat with reactions ---
    room = ChatRoom.objects.filter(kind="room").first() or ChatRoom.objects.create(kind="room", slug="general", title="Umumiy xona")
    room.title = "Umumiy xona"
    room.save()
    convo = [(members[3], "Salom hammaga! Bugun kechki Kross-treningga kim boradi? 💪"),
             (members[5], "Men boraman, 19:30 da ko'rishamiz"),
             (demo, "Men ham! Bugun squat'da yangi rekord qo'ydim: 105 kg 🔥"),
             (members[7], "Zo'r! Tabriklayman 👏"),
             (members[3], "Kim protein kokteyl tavsiya qiladi? Do'konda shokoladlisi bormi?"),
             (members[9], "Bor, kecha oldim, mazasi zo'r 😋"),
             (demo, "Murabbiy Jasur aka bugun boks darsini o'tadimi?"),
             (members[5], "Ha, 17:00 da. Joylar tez tugaydi, oldindan band qiling")]
    msgs = []
    for k, (u, body) in enumerate(convo):
        m = ChatMessage.objects.create(room=room, sender=u, body=body)
        set_created(ChatMessage, m.pk, "created", NOW - timedelta(minutes=(len(convo) - k) * 7 + 3))
        msgs.append(m)
    for m, emo, who in [(msgs[2], "🔥", [3, 5, 7, 9, 11]), (msgs[2], "👏", [2, 4]), (msgs[0], "💪", [5, 6]), (msgs[5], "😋", [3]),
                        (msgs[7], "👍", [0, 3])]:
        for i in who:
            MessageReaction.objects.create(message=m, user=members[i], emoji=emo)

    # --- support desk ---
    th = SupportThread.objects.create(user=members[4], status="open", last_message_at=NOW - timedelta(minutes=12), unread_by_staff=1)
    for k, (staff, txt) in enumerate([(False, "Assalomu alaykum! Abonementni 1 haftaga muzlatsa bo'ladimi?"),
                                      (True, "Va alaykum assalom! Ha, 'Abonement' bo'limida 7-14 kunga muzlatishingiz mumkin."),
                                      (False, "Rahmat, tushunarli. Mehmon olib kelsam ham bo'ladimi?")]):
        sm = SupportMessage.objects.create(thread=th, sender_user=admin if staff else members[4], is_staff=staff, text=txt)
        set_created(SupportMessage, sm.pk, "created", NOW - timedelta(minutes=40 - k * 14))
    th2 = SupportThread.objects.create(guest_name="Mehmon", guest_phone="+998900009999", status="pending",
                                       last_message_at=NOW - timedelta(hours=2), unread_by_staff=0)
    SupportMessage.objects.create(thread=th2, is_staff=False, text="Zal yakshanba kuni ham ishlaydimi?")
    SupportMessage.objects.create(thread=th2, sender_user=admin, is_staff=True, text="Ha, har kuni 06:00 dan 23:00 gacha ishlaymiz.")

    # --- Instagram inbox ---
    for k, (uname, name, lines) in enumerate([
        ("sport.lover_01", "Bekzod", [("in", "user", "Salom, oylik abonement narxi qancha?"),
                                      ("out", "bot", "Salom! 1 oylik - 400 000 so'm, 3 oylik - 1 000 000 so'm. Saytda onlayn to'lash mumkin."),
                                      ("in", "user", "Ish vaqti qanaqa?"),
                                      ("out", "bot", "Har kuni 06:00 dan 23:00 gacha ochiqmiz.")]),
        ("malika.fit", "Malika", [("in", "user", "Ayollar uchun yoga darsi bormi?"),
                                  ("out", "bot", "Ha! Yoga har kuni 08:00 da, murabbiy Kamila Usmonova."),
                                  ("in", "user", "Sinov darsi bepulmi?")]),
        ("timur_box", "Timur", [("in", "user", "Boks darsiga yozilmoqchiman"),
                                ("out", "staff", "Albatta! Saytda 'Darslar' bo'limidan band qiling yoki zalga keling.")])]):
        t = IgThread.objects.create(igsid=f"demo{k}", username=uname, name=name, unread=1 if lines[-1][0] == "in" else 0,
                                    needs_human=k == 1, last_message_at=NOW - timedelta(minutes=5 + k * 25),
                                    last_user_message_at=NOW - timedelta(minutes=5 + k * 25))
        for j, (dr, kind, txt) in enumerate(lines):
            IgMessage.objects.create(thread=t, mid=f"demo{k}-{j}", direction=dr, kind=kind, text=txt, attachments=[],
                                     created=NOW - timedelta(minutes=5 + k * 25 + (len(lines) - j) * 3), sent_ok=True, processed=True,
                                     author=admin if kind == "staff" else None)
    print("seeded:", User.objects.count(), "users,", Payment.objects.filter(status="paid").count(), "paid payments,",
          Visit.objects.count(), "visits; demo member:", demo.username, "admin:", admin.username if admin else None)


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
