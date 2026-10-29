from django.db import migrations


def rename(apps, schema_editor):
    """The owner signs in as `admin1`: an existing superuser called `admin` is renamed (only if `admin1` is free)."""
    User = apps.get_model("gym", "User")
    if User.objects.filter(username__iexact="admin1").exists():
        return
    u = User.objects.filter(is_superuser=True, username="admin").order_by("pk").first()
    if u:
        u.username = "admin1"
        u.save(update_fields=["username"])


class Migration(migrations.Migration):
    dependencies = [("gym", "0022_strip_namuna")]
    operations = [migrations.RunPython(rename, migrations.RunPython.noop)]
