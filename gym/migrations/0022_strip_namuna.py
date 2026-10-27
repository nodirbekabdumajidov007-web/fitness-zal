from django.db import migrations

SUFFIX = " (namuna)"


def strip_suffix(apps, schema_editor):
    """Demo data used to carry a " (namuna)" tag in the names; the tag is dropped from the existing rows."""
    for model, field in (("Trainer", "name"), ("Announcement", "title"), ("GymClass", "name")):
        M = apps.get_model("gym", model)
        for obj in M.objects.filter(**{field + "__icontains": "(namuna)"}):
            old = getattr(obj, field)
            new = old.replace(SUFFIX, "").replace(SUFFIX.title(), "").replace("(namuna)", "").strip()
            if new and new != old:
                setattr(obj, field, new)
                obj.save(update_fields=[field])


class Migration(migrations.Migration):
    dependencies = [("gym", "0021_food_entry")]
    operations = [migrations.RunPython(strip_suffix, migrations.RunPython.noop)]
