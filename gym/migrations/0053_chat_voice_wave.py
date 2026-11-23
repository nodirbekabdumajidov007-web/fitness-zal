from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gym", "0052_chat_voice"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatmessage",
            name="voice_wave",
            field=models.CharField(blank=True, max_length=64, verbose_name="Ovoz to'lqini"),
        ),
    ]
