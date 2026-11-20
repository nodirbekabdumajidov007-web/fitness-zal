from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gym", "0051_about_defaults"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatmessage",
            name="voice",
            field=models.FileField(blank=True, upload_to="chat/voice/%Y/%m/", verbose_name="Ovozli xabar"),
        ),
        migrations.AddField(
            model_name="chatmessage",
            name="voice_secs",
            field=models.PositiveSmallIntegerField(default=0, verbose_name="Ovoz davomiyligi (soniya)"),
        ),
    ]
