from django.db import migrations

ABOUT = "Fitnes Zal — zamonaviy jihozlar, tajribali murabbiylar va o'z natijangizni ko'rib boradigan shaxsiy kabinet, hammasi bitta zalda.\n\nZal har kuni ochiq. Birinchi marta kelayotganlar 1 kunlik abonementdan boshlashi, mashqni esa murabbiy bilan boshlashi mumkin. Ish vaqti, manzil va yo'l pastda ko'rsatilgan."


def fill(apps, schema_editor):
    """The public map pin of the gym = the point the owner gave for deliveries (the Tashkent gym), and a short text for the «Zal haqida» page,
    each only where the owner has not written anything yet."""
    G = apps.get_model("gym", "GymSettings")
    G.objects.filter(map_lat__isnull=True, map_lng__isnull=True, delivery_lat__isnull=False, delivery_lng__isnull=False).update(
        map_lat="41.293341", map_lng="69.222725")
    G.objects.filter(about_text="").update(about_text=ABOUT)


class Migration(migrations.Migration):

    dependencies = [
        ("gym", "0050_gym_photos_about"),
    ]

    operations = [
        migrations.RunPython(fill, migrations.RunPython.noop),
    ]
