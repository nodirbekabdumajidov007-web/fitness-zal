"""Adds the 17 products of 2026-11-17 (and the «Aksessuarlar» category) to shops that already have products.
A fresh database is left alone: `setup_gym` seeds the full list there. Runs once, so a product the gym later deletes stays deleted."""
from django.db import migrations


def add(apps, schema_editor):
    from gym.management.commands.setup_gym import NEW_2026_11, PRODUCTS
    Category, Product = apps.get_model("gym", "Category"), apps.get_model("gym", "Product")
    if not Product.objects.exists():
        return
    have = set(Product.objects.values_list("name", flat=True))
    for i, (cat, items) in enumerate(PRODUCTS):
        todo = [(n, p, s) for n, p, s in items if n in NEW_2026_11 and n not in have]
        if not todo:
            continue
        c = Category.objects.filter(name=cat).first() or Category.objects.create(name=cat, order=i)
        Product.objects.bulk_create(Product(category=c, name=n, price=p, stock=s) for n, p, s in todo)


class Migration(migrations.Migration):
    dependencies = [("gym", "0043_plan_days")]
    operations = [migrations.RunPython(add, migrations.RunPython.noop)]
