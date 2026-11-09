from django.db import migrations


def seed(apps, schema_editor):
    from gym.faq_seed import FAQ
    from gym.legal_defaults import DEFAULTS
    Faq, Legal, User = apps.get_model("gym", "FaqItem"), apps.get_model("gym", "LegalPage"), apps.get_model("gym", "User")
    if not Faq.objects.exists():
        for i, (qu, qr, qe, au, ar, ae) in enumerate(FAQ, 1):
            Faq.objects.create(question_uz=qu, question_ru=qr, question_en=qe, answer_uz=au, answer_ru=ar, answer_en=ae, order=i * 10)
    for slug, data in DEFAULTS.items():
        Legal.objects.get_or_create(slug=slug, defaults=data)
    # the monthly leaderboard is opt-in now: nobody agreed to it before, so everyone starts hidden
    User.objects.filter(show_in_leaderboard=True).update(show_in_leaderboard=False)


class Migration(migrations.Migration):
    dependencies = [("gym", "0027_retention_features")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
