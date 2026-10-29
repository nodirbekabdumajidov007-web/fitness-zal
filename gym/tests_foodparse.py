"""Regression tests for the free-text food recognition: one phrase must never pick two variants of the same food, and a note in the
brackets of a name ("xom", "yangi", "shakarsiz", "10%") only counts together with the food it describes."""
from django.test import SimpleTestCase

from . import calories, food_db


def names(text):
    return [x["name"] for x in calories.parse_text(text)]


class FoodParseTests(SimpleTestCase):
    def test_qualifier_with_base_gives_one_food(self):
        self.assertEqual(names("men pishirilgan guruch yedim"), ["Guruch (pishirilgan)"])
        self.assertEqual(names("qaynatilgan kartoshka"), ["Kartoshka (qaynatilgan)"])
        self.assertEqual(names("grechka pishirilgan"), ["Grechka (pishirilgan)"])
        self.assertEqual(names("shakarsiz choy"), ["Choy (shakarsiz)"])
        self.assertEqual(names("qizil vino"), ["Vino (qizil)"])
        self.assertEqual(names("pizza margarita"), ["Pizza (Margarita)"])

    def test_qualifier_alone_never_picks_a_food(self):
        self.assertEqual(names("yangi bodring"), ["Bodring"])
        self.assertEqual(names("2 yangi anjir"), ["Anjir (yangi)"])
        self.assertEqual(names("xom guruch 100 g"), ["Guruch (xom)"])
        self.assertEqual(names("xom tuxum"), ["Tuxum (xom)"])
        self.assertEqual(names("tuzlangan bodring"), ["Bodring (tuzlangan)"])
        for generic in ("xom", "yangi", "pishirilgan", "qaynatilgan"):
            self.assertEqual(names(generic), [])

    def test_a_name_wins_over_a_bracket_note_of_another_food(self):
        self.assertEqual(names("mol go'shti 200 g"), ["Mol go'shti (qaynatilgan)"])
        self.assertEqual(names("qo'y go'shti"), ["Qo'y go'shti (qaynatilgan)"])
        self.assertEqual(names("dumba"), ["Dumba"])
        self.assertEqual(names("kolbasa"), ["Kolbasa (qaynatilgan)"])
        self.assertEqual(names("shashlik dumba"), ["Shashlik (dumba)"])

    def test_percent_names_the_product_and_is_not_an_amount(self):
        r = calories.parse_text("sut 2.5%")
        self.assertEqual([x["name"] for x in r], ["Sut (2.5%)"])
        self.assertEqual(r[0]["grams"], 200)  # one usual portion, not 2.5 portions
        self.assertEqual(names("kefir 1%"), ["Kefir (1%)"])
        self.assertTrue(names("kefir 1,5%"))  # a decimal comma does not crash the parser
        self.assertEqual(names("20% qaymoq"), ["Qaymoq (20%)"])
        self.assertEqual(names("smetana 10%"), ["Smetana (10%)"])
        self.assertEqual(names("150 g tvorog 5%"), ["Tvorog (5%)"])
        self.assertEqual(calories.parse_text("150 g tvorog 5%")[0]["grams"], 150)

    def test_extra_aliases(self):
        self.assertEqual(names("qora pivo"), ["Pivo (qorong'i)"])
        self.assertEqual(names("qahva sutli"), ["Qahva (sut bilan)"])
        self.assertEqual(names("sendvich tovuqli"), ["Sendvich (tovuqli, kichik)"])

    def test_amounts_still_work(self):
        r = calories.parse_text("3 ta somsa va 1 choy")
        self.assertEqual([x["name"] for x in r], ["Somsa (go'shtli)", "Choy (shakarsiz)"])
        self.assertEqual(r[0]["grams"], 360)
        self.assertEqual(calories.parse_text("1.5 kg olma")[0]["grams"], 1500)
        self.assertEqual(calories.parse_text("плов 300 г")[0]["grams"], 300)

    def test_plain_keeps_decimals(self):
        self.assertEqual(food_db.plain("Sut (2.5%)"), "sut 2.5%")
        self.assertEqual(food_db.plain("o'rik, 1.5 kg!"), "orik 1.5 kg")
        self.assertEqual(food_db.plain("a.b"), "a b")

    def test_the_exact_name_wins_over_a_look_alike(self):
        self.assertEqual(names("Kurka go'shti"), ["Kurka go'shti"])
        self.assertEqual(names("Tandir go'sht"), ["Tandir go'sht"])
        self.assertEqual(names("Kefir (yog'siz)"), ["Kefir (yog'siz)"])
        self.assertEqual(names("kefir yog'siz"), ["Kefir (yog'siz)"])

    def test_every_food_is_found_by_its_own_name(self):
        """Typing the full name of any of the ~600 foods must find that food (and never a second variant next to it, unless the row lists only
        its own aliases)."""
        missed = [f.name for f in food_db.FOODS_DB if str(f.id) not in [x["idx"] for x in calories.parse_text(f.name)]]
        self.assertEqual(missed, [])
