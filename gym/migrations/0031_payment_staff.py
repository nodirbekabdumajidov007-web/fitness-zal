import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gym", "0030_backfill_entry_log"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="staff",
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+",
                                    to=settings.AUTH_USER_MODEL, verbose_name="Kim rasmiylashtirdi (qabulxona)"),
        ),
    ]
