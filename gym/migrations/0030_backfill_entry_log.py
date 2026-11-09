from django.db import migrations


def backfill(apps, schema_editor):
    """Entries recorded before the entry history existed: one accepted row per old visit, with the way marked as unknown ("old")."""
    Visit, Log = apps.get_model("gym", "Visit"), apps.get_model("gym", "EntryLog")
    if Log.objects.exists():
        return
    Log.objects.bulk_create([Log(user_id=uid, method="old", result="ok", ts=ts) for uid, ts in Visit.objects.values_list("user_id", "ts").iterator()], batch_size=500)


class Migration(migrations.Migration):
    dependencies = [("gym", "0029_entry_log")]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
