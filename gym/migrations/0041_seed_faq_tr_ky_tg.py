from django.db import migrations


def translate_seed(apps, schema_editor):
    """Adds the Turkish / Kyrgyz / Tajik text to the starting FAQ rows that were never edited (their Uzbek question and answer still equal the seed).
    Rows an admin changed or added are left alone, and a language that already has text is never overwritten."""
    from gym.faq_seed import FAQ
    from gym.faq_seed_x import FAQ_X
    Faq = apps.get_model("gym", "FaqItem")
    for seed, extra in zip(FAQ, FAQ_X):
        row = Faq.objects.filter(question_uz=seed[0], answer_uz=seed[3]).first()
        if row is None:
            continue
        for lg, q, a in zip(("tr", "ky", "tg"), extra[:3], extra[3:]):
            if not getattr(row, "question_" + lg) and not getattr(row, "answer_" + lg):
                setattr(row, "question_" + lg, q)
                setattr(row, "answer_" + lg, a)
        row.save()


class Migration(migrations.Migration):
    dependencies = [("gym", "0040_faq_tr_ky_tg")]
    operations = [migrations.RunPython(translate_seed, migrations.RunPython.noop)]
