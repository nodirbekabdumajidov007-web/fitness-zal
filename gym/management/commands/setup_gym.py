import os
import secrets
from datetime import time

from django.core.management.base import BaseCommand

from gym import seed_lessons
from gym.models import (Announcement, Category, GymClass, GymSettings, Lesson, Plan, Product, PromoCode, Trainer, User, WorkoutType)

ADMIN_PHONE = "+998908775505"
ADMIN_USERNAME = "admin1"


def admin_password_from_env():
    """FZ_ADMIN_PASSWORD without a trailing ".admin": that suffix is what one types at sign-in to open the admin panel,
    so a password that itself ended in ".admin" could never be used there (people naturally write "2012.admin" here)."""
    pw = os.environ.get("FZ_ADMIN_PASSWORD", "").strip()
    return pw[:-len(".admin")] if pw.endswith(".admin") else pw

PLANS = [("d1", "1 kunlik", 1, 1, 50000, 0), ("m1", "1 oylik", 1, 0, 400000, 1), ("m3", "3 oylik", 3, 0, 1000000, 2)]  # code, name, months, days, price, order
PRODUCTS = [
    ("Ichimliklar", [("Suv 0.5 l", 5000, 120), ("Suv 1.5 l", 8000, 80), ("Energetik ichimlik", 18000, 60), ("Izotonik ichimlik", 15000, 50),
                     ("Sovuq choy 0.5 l", 9000, 60), ("Proteinli sut 330 ml", 22000, 40)]),
    ("Protein", [("Protein kokteyl", 25000, 40), ("Whey protein 900 g", 450000, 12), ("Proteinli batonchik", 20000, 70),
                 ("Kazein protein 900 g", 480000, 8), ("Geyner 1 kg", 280000, 10), ("Proteinli pechenye", 18000, 50)]),
    ("Qo'shimchalar", [("Kreatin 300 g", 220000, 15), ("BCAA 200 g", 180000, 10), ("Shaker", 45000, 25),
                       ("Glutamin 300 g", 170000, 10), ("L-karnitin 500 ml", 160000, 12), ("Omega-3, 90 kapsula", 150000, 15),
                       ("Vitamin kompleks, 60 tabletka", 120000, 15), ("Mashqdan oldingi kompleks 300 g", 250000, 8)]),
    ("Aksessuarlar", [("Sport sochig'i", 60000, 30), ("Mashq qo'lqopi", 90000, 20), ("Bilak bintlari", 70000, 20), ("Atletik kamar", 250000, 8),
                      ("Sport butilkasi 0.75 l", 55000, 25), ("Skakalka", 40000, 20), ("Fitnes rezinasi", 50000, 25)]),
]
# Added on 2026-11-17: migration 0044 adds exactly these to shops that were seeded before that date.
NEW_2026_11 = {"Sovuq choy 0.5 l", "Proteinli sut 330 ml", "Kazein protein 900 g", "Geyner 1 kg", "Proteinli pechenye", "Glutamin 300 g", "L-karnitin 500 ml",
               "Omega-3, 90 kapsula", "Vitamin kompleks, 60 tabletka", "Mashqdan oldingi kompleks 300 g", "Sport sochig'i", "Mashq qo'lqopi", "Bilak bintlari",
               "Atletik kamar", "Sport butilkasi 0.75 l", "Skakalka", "Fitnes rezinasi"}


class Command(BaseCommand):
    help = "Seeds plans, shop and settings, and creates the admin on first run. Use --demo for sample trainers, classes and announcements."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="add sample trainers, classes, announcement and a promo code")

    def handle(self, *args, **opts):
        GymSettings.load()
        for code, name, months, days, price, order in PLANS:
            Plan.objects.get_or_create(code=code, defaults=dict(name=name, months=months, days=days, price=price, order=order))
        if not Product.objects.exists():
            for i, (cat, items) in enumerate(PRODUCTS):
                c = Category.objects.create(name=cat, order=i)
                Product.objects.bulk_create(Product(category=c, name=n, price=p, stock=s) for n, p, s in items)
        if opts["demo"] and not Trainer.objects.exists():
            a = Trainer.objects.create(name="Sardor Rahimov", specialty="Pauerlifting", experience_years=9, bio="Namuna ma'lumot. Admin paneldan o'zgartiring.")
            b = Trainer.objects.create(name="Bekzod Yusupov", specialty="Yoga va stretching", experience_years=6)
            c = Trainer.objects.create(name="Jasur Toshmatov", specialty="Boks va funksional", experience_years=7)
            for wd in (0, 2, 4):
                GymClass.objects.create(name="Funksional", trainer=c, weekday=wd, start_time=time(18, 30), capacity=15)
                GymClass.objects.create(name="Yoga", trainer=b, weekday=wd, start_time=time(10, 0), capacity=12)
            GymClass.objects.create(name="Pauerlifting", trainer=a, weekday=1, start_time=time(19, 0), capacity=8)
            GymClass.objects.create(name="Boks", trainer=c, weekday=5, start_time=time(10, 0), capacity=14)
            Announcement.objects.create(title="Yangi zal ochildi!", body="Birinchi mashg'ulot bepul. Qabulxonaga murojaat qiling.", pinned=True)
            PromoCode.objects.get_or_create(code="YANGI10", defaults={"percent": 10})
        if opts["demo"] and not WorkoutType.objects.exists():
            types = [WorkoutType.objects.create(name=n, description=d, order=i) for i, (n, d) in enumerate(seed_lessons.TYPES)]
            for i, (ti, wd, level, mins, _vip, title, summary, steps, muscles, equipment, tips) in enumerate(seed_lessons.LESSONS):
                Lesson.objects.create(workout_type=types[ti], weekday=wd, level=level, duration_min=mins, title=title, summary=summary,
                                      steps=steps, muscles=muscles, equipment=equipment, tips=tips, order=i)
        # Hosting without a shell (Render free): FZ_ADMIN_RESET=1 + FZ_ADMIN_PASSWORD sets the owner's password on the next
        # deploy. Only on purpose, so a password changed inside the site is not overwritten by every deploy.
        reset_pw = admin_password_from_env()
        if os.environ.get("FZ_ADMIN_RESET") == "1" and reset_pw:
            admin = User.objects.filter(is_superuser=True).order_by("pk").first()
            if admin:
                admin.set_password(reset_pw)
                admin.is_active = True
                admin.save(update_fields=["password", "is_active"])
                self.stdout.write("=" * 60)
                self.stdout.write(f" ADMIN paroli FZ_ADMIN_PASSWORD ga almashtirildi. Login: {admin.username}")
                self.stdout.write(" Kirgach Render'dan FZ_ADMIN_RESET ni o'chiring.")
                self.stdout.write("=" * 60)
        if not User.objects.filter(is_superuser=True).exists():
            pw = admin_password_from_env() or secrets.token_urlsafe(9)
            User.objects.create_superuser(ADMIN_USERNAME, pw, phone=ADMIN_PHONE, first_name="Admin", last_name="Fitnes Zal")
            self.stdout.write("=" * 60)
            self.stdout.write(f" ADMIN yaratildi. Login: {ADMIN_USERNAME}  (telefon profilda: {ADMIN_PHONE})")
            self.stdout.write(f" Parol: {pw}   (admin panel uchun parol oxiriga .admin qo'shing)")
            self.stdout.write(" Bu parol faqat bir marta ko'rsatiladi. Kirgach o'zgartiring.")
            self.stdout.write("=" * 60)
