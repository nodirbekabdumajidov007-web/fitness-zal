"""The gym is in Tashkent: delivery distance is measured from the city centre until the owner enters exact coordinates.
Only an untouched setting is filled in (no city and no coordinates yet), so anything the owner set is never overwritten."""
from django.db import migrations


def set_city(apps, schema_editor):
    G = apps.get_model("gym", "GymSettings")
    G.objects.filter(delivery_origin="", map_lat__isnull=True, map_lng__isnull=True).update(delivery_origin="tashkent")


class Migration(migrations.Migration):
    dependencies = [("gym", "0045_delivery_by_distance")]
    operations = [migrations.RunPython(set_city, migrations.RunPython.noop)]
