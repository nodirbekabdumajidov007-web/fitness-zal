"""Sign-up moves to Django's usual shape: a username, an e-mail and a password.

Existing accounts get a username automatically: "admin" for the owner, otherwise from the e-mail, the first name or the phone."""
import re

import django.core.validators
from django.db import migrations, models


def fill_usernames(apps, schema_editor):
    User = apps.get_model("gym", "User")
    taken = set()
    for u in User.objects.order_by("pk"):
        if u.is_superuser and "admin" not in taken:
            base = "admin"
        else:
            base = (u.email or "").split("@")[0] or u.first_name or ("u" + (u.phone or "")[-4:])
            base = re.sub(r"[^A-Za-z0-9_.]", "", base.lower())[:20] or "user"
            if len(base) < 3:
                base = (base + "user")[:20]
        name, n = base, 1
        while name.lower() in taken:
            n += 1
            name = f"{base}{n}"
        taken.add(name.lower())
        User.objects.filter(pk=u.pk).update(username=name)


class Migration(migrations.Migration):

    dependencies = [
        ("gym", "0017_ai_messages"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="username",
            field=models.CharField(max_length=30, null=True, verbose_name="Login"),
        ),
        migrations.RunPython(fill_usernames, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="username",
            field=models.CharField(help_text="3-30 belgi: lotin harflari, raqamlar, _ va .", max_length=30, unique=True,
                                   validators=[django.core.validators.RegexValidator("^[A-Za-z0-9_.]{3,30}$", "err_username")],
                                   verbose_name="Login"),
        ),
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(blank=True, max_length=254, null=True, unique=True, verbose_name="Email"),
        ),
        migrations.AlterField(
            model_name="user",
            name="first_name",
            field=models.CharField(blank=True, max_length=40, verbose_name="Ism"),
        ),
        migrations.AlterField(
            model_name="user",
            name="last_name",
            field=models.CharField(blank=True, max_length=40, verbose_name="Familiya"),
        ),
    ]
