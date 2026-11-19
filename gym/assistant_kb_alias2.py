"""More everyday phrasings for the most asked questions (same format as assistant_kb_alias.py: {entry id: (uz, ru, en)}, "|" between keywords).
Only keywords: every answer stays in its own knowledge-base row. Merged by assistant_kb."""

ALIAS2 = {
    "hours": ("ish vaqtingiz qanaqa|ish vaqtingiz qanday|ish vaqtingiz|ish vaqti|ish tartibi|ishlash vaqti|soat nechida ochiladi|soat nechida ochasizlar|soat nechada yopiladi|soat nechada yopasizlar|nechigacha ishlaysizlar|nechigacha ochiq|nechadan nechagacha ishlaysiz",
              "график работы|когда открываетесь|когда закрываетесь|до скольки открыто|часы работы|во сколько закрываетесь",
              "opening hours|working hours|what are your hours|when do you close|what time do you close|are you open"),
    "open_now": ("qachon ochiq|hozir ochiqmi|hozir ishlayaptimi|hozir ochiqmisiz|bugun ochiqmi|bugun ishlaysizlarmi",
                 "сейчас открыто|открыты ли вы сейчас|работаете сегодня", "open now|are you open now|open today"),
    "prices": ("narxlar qancha|narxlar|narx qancha|abonement qancha turadi|abonement qancha|obuna narxi|narxlari qanday|narxlaringiz",
               "сколько стоит|какие цены|цены|стоимость абонемента|сколько стоит абонемент",
               "how much does it cost|how much is a membership|prices|price list|membership price|cost of membership"),
}
