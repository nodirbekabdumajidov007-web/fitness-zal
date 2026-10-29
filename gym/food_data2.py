"""Built-in food table, part 2 (meat, fish, dairy, fruit, vegetables, nuts, sauces, sweets, drinks, sports nutrition).
Same line format as gym/food_data1.py. Rows are appended after part 1, never reordered."""

RAW = """
# ---- meat and offal
Tovuq ko'kragi (xom) | 113 23 1.9 0 | 0 150 | xom tovuq ko'kragi, сырая куриная грудка, raw chicken breast
Tovuq sonlari (pishirilgan) | 210 26 11 0 | 0 150 | бёдра куриные, куриные бёдра, chicken thighs, chicken thigh, tovuq soni
Tovuq oyoqchasi | 175 18 11 0 | 100 150 | голень, куриная голень, drumstick, chicken leg, tovuq oyog'i, tovuq boldiri
Tovuq qanoti (xom) | 195 17 14 0 | 0 150 | куриные крылья, raw wings, tovuq qanoti
Tovuq jigari | 140 20 6 1 | 0 100 | куриная печень, chicken liver, tovuq jigar
Tovuq yuragi | 160 16 10 0.7 | 0 100 | куриные сердечки, chicken hearts, tovuq yurak
Tovuq oshqozoni | 114 18 4.2 0 | 0 100 | куриные желудки, chicken gizzards, tovuq oshqozon
Tandir tovuq | 215 25 12 0 | 0 200 | тандыр курица, курица гриль, grilled chicken, roast chicken, tovuq tandir, gril tovuq
Kurka go'shti (ko'krak) | 135 30 1 0 | 0 150 | индейка, грудка индейки, turkey, turkey breast, kurka
Kurka go'shti | 195 21 12 0 | 0 150 | мясо индейки, turkey meat, hindi go'shti
O'rdak go'shti | 330 16 28 0 | 0 150 | утка, duck, o'rdak
G'oz go'shti | 320 29 22 0 | 0 150 | гусь, goose, g'oz
Quyon go'shti | 180 21 11 0 | 0 150 | кролик, rabbit, quyon
Mol go'shti (xom) | 187 19 12 0 | 0 150 | сырая говядина, raw beef, xom mol go'shti
Mol qiymasi | 250 17 20 0 | 0 150 | говяжий фарш, minced beef, ground beef, qiyma, фарш, mince
Mol bifshteks (qovurilgan) | 270 26 18 0 | 0 150 | бифштекс, steak, steyk, beefsteak, bifshteks, стейк
Mol filesi | 190 28 8 0 | 0 150 | говяжья вырезка, beef fillet, tenderloin, fillet mignon, fille
Mol jigari (qovurilgan) | 175 27 5 4 | 0 100 | печень говяжья, beef liver, mol jigari, jigar, печень
Mol tili | 230 16 18 0 | 0 100 | язык говяжий, beef tongue, til
Mol yuragi | 110 18 4 0 | 0 100 | сердце говяжье, beef heart, mol yurak
Qo'y go'shti (xom) | 210 17 16 0 | 0 150 | сырая баранина, raw lamb, xom qo'y go'shti
Qo'y qovurg'asi | 300 17 26 0 | 0 150 | бараньи рёбрышки, lamb ribs, qovurg'a, ribs
Qo'y qiymasi | 280 16 24 0 | 0 150 | бараний фарш, minced lamb, ground lamb
Qo'y jigari | 130 20 5 2 | 0 100 | баранья печень, lamb liver
Cho'chqa go'shti | 260 16 21 0 | 0 150 | свинина, pork, cho'chqa
Cho'chqa qiymasi | 290 15 25 0 | 0 150 | свиной фарш, ground pork, minced pork
Ot go'shti | 175 20 10 0 | 0 150 | конина, horse meat, ot
Jambon | 145 18 8 1 | 25 50 | ветчина, ham, jambon
Bekon | 540 37 42 1 | 10 40 | бекон, bacon, bekon
Salyami | 450 22 40 1 | 10 40 | салями, salami, kolbasa salyami
Kolbasa (dudlangan) | 470 17 44 1 | 10 40 | копчёная колбаса, smoked sausage, dudlangan kolbasa
Kolbasa (doktorskaya) | 257 13 22 1.5 | 25 75 | докторская колбаса, doctors sausage, doktor kolbasa
Pashtet | 250 12 21 3 | 0 30 | паштет, pate, pashtet
Tushonka | 230 15 18 0 | 0 100 | тушёнка, canned meat, tushonka, go'sht konservasi, stew meat
Go'sht (dudlangan, quruq) | 410 55 18 3 | 0 30 | вяленое мясо, jerky, beef jerky, quritilgan go'sht, qoq go'sht
# ---- fish and seafood
Losos (pishirilgan) | 206 22 12 0 | 0 150 | лосось, сёмга, семга, salmon, losos, baked salmon
Losos (xom) | 208 20 13 0 | 0 150 | сырой лосось, raw salmon, losos xom
Losos (tuzlangan) | 202 20 14 0 | 0 50 | слабосолёный лосось, salted salmon, smoked salmon, tuzlangan losos, dudlangan losos
Forel | 150 21 7 0 | 0 150 | форель, trout, forel
Skumbriya | 205 19 14 0 | 0 150 | скумбрия, mackerel, makrel, skumbriya dudlangan
Seld (tuzlangan) | 217 18 16 0 | 0 100 | селёдка, сельдь, herring, seld, salted herring
Treska | 82 18 0.7 0 | 0 150 | треска, cod, treska
Sazan | 127 18 5.6 0 | 0 150 | сазан, карп, carp, sazan
Sudak | 97 21 1.1 0 | 0 150 | судак, pike perch, zander
Tilapiya | 128 26 2.7 0 | 0 150 | тилапия, tilapia
Xek (baliq) | 86 17 2.2 0 | 0 150 | хек, hake, xek
Baliq (qovurilgan) | 190 20 11 3 | 0 150 | жареная рыба, fried fish, qovurma baliq, baliq qovurilgan
Baliq (panirovka) | 220 15 13 12 | 0 150 | рыба в панировке, breaded fish, fish sticks, fish fingers
Qizil ikra | 250 31 14 0 | 0 20 | красная икра, red caviar, salmon roe, ikra
Qora ikra | 264 24 18 4 | 0 20 | чёрная икра, black caviar, sturgeon caviar
Krab tayoqchalari | 95 6 1 15 | 18 100 | крабовые палочки, crab sticks, surimi, krab tayoqcha
Krevetka | 99 24 0.3 0.2 | 0 100 | креветки, shrimp, prawns, krevetka pishirilgan
Midiya | 86 12 2.2 3.7 | 0 100 | мидии, mussels
Kalmar | 92 16 1.4 3 | 0 100 | кальмар, squid, kalmar
Sprot (konserva) | 363 17 32 0 | 0 60 | шпроты, sprats, sprot konserva
Sardina (konserva) | 208 25 11 0 | 0 100 | сардины, sardines, sardina konserva
Baliq konservasi (tomatda) | 140 14 8 3 | 0 100 | рыбные консервы, canned fish, konserva baliq, консервы в томате
# ---- dairy and eggs
Sut (3.2%) | 60 3 3.2 4.7 | 0 200 | молоко 3.2, whole milk, to'liq yog'li sut, pasteurizovannoe
Sut (1.5%) | 44 3 1.5 4.7 | 0 200 | молоко 1.5, low fat milk, past yog'li sut
Sut (yog'siz) | 34 3.4 0.1 5 | 0 200 | обезжиренное молоко, skim milk, yog'siz sut, nonfat milk
Echki suti | 68 3.5 4 4.5 | 0 200 | козье молоко, goat milk, echki sut
Quritilgan sut | 480 26 25 38 | 0 20 | сухое молоко, powdered milk, milk powder, sut kukuni
Quyultirilgan sut | 320 7 8.5 56 | 0 30 | сгущёнка, сгущённое молоко, condensed milk, sgushyonka, qiyom sut
Qaymoq (10%) | 118 3 10 4 | 0 30 | сливки 10, cream, light cream, qaymoq, сливки
Qaymoq (20%) | 205 2.8 20 3.7 | 0 30 | сливки 20, medium cream, qaymoq 20
Qaymoq (33%) | 330 2.2 33 3.2 | 0 30 | сливки 33, heavy cream, whipping cream, qaymoq 33, взбитые сливки
Smetana (10%) | 116 3 10 3.2 | 0 30 | сметана 10, light sour cream
Smetana (15%) | 160 2.6 15 3 | 0 30 | сметана 15
Kefir (1%) | 40 3 1 4 | 0 200 | кефир 1, low fat kefir, kefir yog'siz
Kefir (yog'siz) | 30 3 0.1 4 | 0 200 | обезжиренный кефир, fat free kefir
Ryajenka | 67 3 4 4.2 | 0 200 | ряженка, baked milk, rjenka, ryazhenka
Ayron | 28 1.5 1.4 2.5 | 0 250 | айран, ayran, ayron ichimlik, айрон
Qatiq (yog'siz) | 40 3 0.5 4 | 0 200 | обезжиренный катык, low fat yogurt, yog'siz qatiq
Qatiq (qaymoqli) | 90 3 6 4 | 0 200 | жирный катык, full fat yogurt, qaymoqli qatiq
Suzma | 160 9 12 4 | 0 100 | сузьма, suzma, chakka, strained yogurt, чакка, labneh
Qurt | 340 38 12 20 | 10 30 | курт, qurt, kurt, dried cheese balls, сухой сыр
Prostokvasha | 53 2.9 2.5 4 | 0 200 | простокваша, soured milk, prostokvasha
Yogurt (tabiiy) | 60 4 3 5 | 0 125 | натуральный йогурт, plain yogurt, natural yogurt, yogurt oddiy
Yogurt (mevali) | 90 3.5 2.5 14 | 0 125 | фруктовый йогурт, fruit yogurt, mevali yogurt, sweet yogurt, danone, данон
Yunon yogurti | 97 9 5 4 | 0 150 | греческий йогурт, greek yogurt, yunon yogurt
Yogurt (yog'siz) | 45 4.5 0.1 6 | 0 125 | обезжиренный йогурт, nonfat yogurt, fat free yogurt
Tvorog (9%) | 169 16 9 3 | 0 150 | творог 9, tvorog 9, cottage cheese 9
Tvorog (yog'siz) | 70 18 0.3 1.8 | 0 150 | творог обезжиренный 0, tvorog 0, fat free cottage cheese
Sirok (glazurlangan) | 407 7 24 41 | 45 45 | глазированный сырок, glazed curd snack, sirok, сырок, tvorog siroki
Pishloq (rossiya) | 360 23 30 0 | 20 30 | российский сыр, russian cheese, rossiya pishloq
Pishloq (gollandiya) | 352 25 27 0 | 20 30 | голландский сыр, dutch cheese, gouda, gollandiya
Pishloq (mozzarella) | 280 22 22 2 | 0 50 | моцарелла, mozzarella, mocarella
Pishloq (brinza) | 260 17 21 1.5 | 0 50 | брынза, фета, feta, brinza, feta pishloq
Pishloq (suluguni) | 290 20 24 0.5 | 0 50 | сулугуни, suluguni, sulguni
Pishloq (eritilgan)| 280 13 21 6 | 20 30 | плавленый сыр, processed cheese, drujba, дружба, eritilgan pishloq, plavlenniy
Pishloq (parmezan) | 400 36 28 0 | 0 20 | пармезан, parmesan, parmezan
Pishloq (cheddar) | 400 25 33 1.3 | 0 30 | чеддер, cheddar
Pishloq (kamamber) | 300 20 24 0.5 | 0 50 | камамбер, camembert, brie, бри
Pishloq (qaymoqli) | 340 6 34 4 | 0 30 | сливочный сыр, cream cheese, philadelphia, creamy cheese, filadelfiya pishloq
Mascarpone | 430 4.6 45 4 | 0 30 | маскарпоне, maskarpone
Rikotta | 170 11 13 3 | 0 50 | рикотта, ricotta
Muzqaymoq (plombir) | 200 3.5 11 22 | 70 100 | пломбир, ice cream, plombir, morozhenoe, мороженое, muzqaymoq
Muzqaymoq (sutli) | 130 3.5 3.5 21 | 70 100 | молочное мороженое, milk ice cream
Muzqaymoq (eskimo) | 270 3 17 27 | 80 80 | эскимо, eskimo, eskimo muzqaymoq, popsicle chocolate
Muzqaymoq (shokoladli) | 215 4 11 26 | 70 100 | шоколадное мороженое, chocolate ice cream
Sariyog' (margarin) | 743 0.5 82 1 | 0 10 | маргарин, margarine, margarin
Sariyog' (eritilgan, ghee) | 887 0 99 0 | 0 10 | топлёное масло, ghee, erigan sariyog', gi, ghi, eritilgan sariyog
Qaymoq (qatlamli, kaymak) | 300 3 30 3 | 0 30 | каймак, kaymak, qaymoq qatlam
# ---- fruit
Nok | 57 0.4 0.1 15 | 170 170 | груша, pear, pears
Shaftoli | 39 0.9 0.3 9.5 | 150 150 | персик, peach, peaches
Nektarin | 44 1.1 0.3 10.5 | 140 140 | нектарин, nectarine
O'rik | 48 1.4 0.4 11 | 40 120 | абрикос, apricot, apricots, orik
Olxo'ri | 46 0.7 0.3 11 | 40 120 | слива, plum, plums, olxori, alycha, алыча
Gilos | 63 1.1 0.2 16 | 0 100 | черешня, sweet cherry, gilos, cherry
Olcha | 52 0.8 0.2 12 | 0 100 | вишня, sour cherry, olcha, vishnya
Qulupnay | 33 0.7 0.3 8 | 0 150 | клубника, strawberry, strawberries, qulupnay
Malina | 52 1.2 0.7 12 | 0 100 | малина, raspberry, raspberries
Maymunjon | 43 1.4 0.5 10 | 0 100 | ежевика, blackberry, blackberries
Smorodina (qora) | 44 1 0.4 7.3 | 0 100 | чёрная смородина, blackcurrant, smorodina
Ko'k meva (chernika) | 57 0.7 0.3 14 | 0 100 | черника, голубика, blueberry, blueberries, chernika
Klyukva | 46 0.5 0.1 12 | 0 100 | клюква, cranberry, cranberries
Mandarin | 38 0.8 0.2 8 | 80 80 | мандарин, tangerine, mandarine, mandarin
Limon | 29 1.1 0.3 9 | 60 60 | лимон, lemon
Greypfrut | 42 0.8 0.1 11 | 250 150 | грейпфрут, grapefruit, greypfrut
Laym | 30 0.7 0.2 10 | 60 60 | лайм, lime
Kivi | 61 1.1 0.5 15 | 75 75 | киви, kiwi
Ananas | 50 0.5 0.1 13 | 0 150 | ананас, pineapple
Mango | 60 0.8 0.4 15 | 0 150 | манго, mango
Papayya | 43 0.5 0.3 11 | 0 150 | папайя, papaya
Avokado | 160 2 15 9 | 150 100 | авокадо, avocado
Xurmo | 70 0.6 0.2 19 | 150 150 | хурма, persimmon, hurma, xurma yangi
Anjir (yangi) | 74 0.8 0.3 19 | 50 100 | инжир свежий, fresh fig, anjir, fig
Anjir (quritilgan) | 250 3 1 64 | 0 30 | инжир сушёный, dried figs, dried fig, quritilgan anjir
Xurma (quritilgan) | 282 2.5 0.4 75 | 20 40 | финики, dates, hurma, date, xurma quritilgan, фурма
Turshak | 240 2.2 0.4 64 | 10 30 | чернослив, prunes, dried plums, qurigan olxo'ri
Olma (quritilgan) | 240 3 0.3 59 | 0 30 | сушёные яблоки, dried apples, quritilgan olma
Nok (quritilgan) | 249 2.5 0.6 62 | 0 30 | сушёные груши, dried pears, quritilgan nok
Kokos (yangi) | 354 3.3 33 15 | 0 40 | кокос, coconut, kokos
Kokos qirindisi | 660 6 65 24 | 0 15 | кокосовая стружка, desiccated coconut, coconut flakes
Tut | 43 1.4 0.4 10 | 0 100 | шелковица, mulberry, tut, mulberries
Tut (quritilgan) | 320 10 3 70 | 0 30 | сушёная шелковица, dried mulberry, quritilgan tut
Behi (quritilgan) | 250 3 0.5 62 | 0 30 | сушёная айва, dried quince
Qovun (quritilgan) | 340 4 0.5 82 | 0 30 | сушёная дыня, dried melon, qovoq-qoqi, quritilgan qovun
Murabbo (jem) | 260 0.4 0.1 65 | 0 30 | варенье, джем, jam, jem, murabbo, varenye, confiture
Marmelad | 320 0.4 0.1 78 | 0 30 | мармелад, marmalade, marmelad, jelly candy
Pastila | 320 0.5 0 80 | 0 30 | пастила, pastila, fruit pastille
Meva salati | 70 0.8 0.3 17 | 0 200 | фруктовый салат, fruit salad, mevali salat
Kompot mevalari (konserva) | 80 0.4 0.1 20 | 0 100 | консервированные фрукты, canned fruit, kompot meva
# ---- vegetables and greens
Kartoshka (xom) | 77 2 0.4 16 | 150 150 | сырой картофель, raw potato
Batat | 86 1.6 0.1 20 | 0 150 | батат, сладкий картофель, sweet potato, shirin kartoshka, yam
Qovoq | 28 1.3 0.3 7 | 0 200 | тыква, pumpkin, qovoq, squash
Baqlajon | 24 1 0.2 6 | 0 150 | баклажан, eggplant, aubergine, baklajon
Bolgar qalampiri | 27 1.3 0.1 5.3 | 120 120 | болгарский перец, bell pepper, paprika, sweet pepper, qalampir, перец сладкий
Achchiq qalampir | 40 2 0.4 9 | 15 15 | острый перец, chili, chilli, hot pepper, achchiq qalampir, чили
Kabachok | 24 0.6 0.3 4.6 | 0 150 | кабачок, цукини, zucchini, courgette, kabachok
Turp | 19 1.2 0.1 3.4 | 0 50 | редис, редька, radish, turp, reduska
Sholg'om | 28 0.9 0.1 6 | 0 100 | репа, turnip, shalgam, shalg'om
Sarimsoq | 143 6.5 0.5 30 | 4 8 | чеснок, garlic, sarimsoq piyoz
Yashil piyoz | 20 1.3 0.1 3.5 | 0 30 | зелёный лук, green onion, spring onion, scallion, ko'k piyoz
Ukrop | 40 2.5 0.5 6.3 | 0 10 | укроп, dill, shivit, шивит
Petrushka | 49 3.7 0.4 7.6 | 0 10 | петрушка, parsley, petrushka
Kashnich | 23 2.1 0.5 3.7 | 0 10 | кинза, кориандр, cilantro, coriander, kashnich
Rayhon | 23 3.2 0.6 2.7 | 0 5 | базилик, basil, rayhon, reyhon
Salat bargi | 15 1.4 0.2 2.9 | 0 50 | салат листовой, lettuce, salat, латук, aysberg
Ismaloq | 23 2.9 0.4 3.6 | 0 50 | шпинат, spinach, ismaloq
Brokkoli | 34 2.8 0.4 7 | 0 150 | брокколи, broccoli
Gulkaram | 30 2.5 0.3 5 | 0 150 | цветная капуста, cauliflower, gulkaram
Brussel karami | 43 3.4 0.3 9 | 0 100 | брюссельская капуста, brussels sprouts
Qizilcha | 43 1.6 0.2 10 | 0 100 | свёкла, свекла, beet, beetroot, qizil lavlagi, lavlagi
Qizilcha (qaynatilgan) | 49 1.8 0.1 11 | 0 100 | варёная свёкла, boiled beetroot, qaynatilgan lavlagi
Sabzi (qaynatilgan) | 35 0.8 0.2 8 | 0 100 | варёная морковь, boiled carrot
Shampinon | 22 3.1 0.3 3.3 | 20 100 | шампиньоны, mushrooms, champignon, qo'ziqorin, гриб, грибы, mushroom
Qo'ziqorin (qovurilgan) | 130 3 11 4 | 0 100 | жареные грибы, fried mushrooms, qovurilgan qo'ziqorin
Pomidor pastasi | 80 5 0.5 14 | 0 20 | томатная паста, tomato paste, tomat pastasi
Zaytun | 115 0.8 10.7 6 | 4 30 | оливки, маслины, olives, olive, zaytun meva, qora zaytun
Karam (tuzlangan) | 19 1.8 0.1 3 | 0 100 | квашеная капуста, sauerkraut, kisly karam, tuzlangan karam
Bodring (tuzlangan) | 11 0.8 0.1 1.7 | 60 100 | солёные огурцы, pickles, pickled cucumber, tuzlangan bodring, marinovannyj
Kimchi | 15 1.1 0.5 2.4 | 0 50 | кимчи, kimchi
Selderey | 16 0.7 0.2 3 | 0 50 | сельдерей, celery
Qushqo'nmas | 20 2.2 0.1 3.9 | 0 100 | спаржа, asparagus
Yashil loviya | 31 1.8 0.1 7 | 0 100 | стручковая фасоль, green beans, string beans
Yashil no'xat (yangi) | 81 5 0.4 14 | 0 100 | зелёный горошек свежий, fresh peas, fresh green peas
Xren | 71 2.5 0.4 16 | 0 10 | хрен, horseradish, xren
Avokado salat | 140 2 12 7 | 0 150 | салат с авокадо, avocado salad
Sabzavotli salat (moyli) | 80 1.5 6 5 | 0 200 | салат овощной с маслом, vegetable salad with oil, oil salad
Sabzavot rag'u | 60 2 3 7 | 0 250 | овощное рагу, vegetable stew, ragu, рагу, sabzavot ragu
Baqlajon ikrasi | 95 1.5 7.5 6 | 0 100 | баклажанная икра, eggplant caviar, baklajon ikra
# ---- nuts and seeds
Funduq | 628 15 61 17 | 0 30 | фундук, лесной орех, hazelnut, hazelnuts, funduk
Kaju | 553 18 44 30 | 0 30 | кешью, cashew, cashews
Yer yong'oq | 551 26 45 10 | 0 30 | арахис, peanut, peanuts, yer yong'og'i, arahis
Yer yong'oq pastasi | 588 25 50 20 | 0 20 | арахисовая паста, peanut butter, arahis pastasi, yong'oq moyi
Pekan | 691 9 72 14 | 0 30 | пекан, pecan
Makadamiya | 718 8 76 14 | 0 30 | макадамия, macadamia
Brazil yong'og'i | 656 14 66 12 | 0 30 | бразильский орех, brazil nut
Kungaboqar urug'i | 580 21 49 20 | 0 30 | семечки, подсолнечные семечки, sunflower seeds, semechki, kungaboqar uruq, semichka
Qovoq urug'i | 559 30 49 11 | 0 30 | тыквенные семечки, pumpkin seeds, qovoq uruq
Kunjut | 573 18 50 23 | 0 10 | кунжут, sesame, sesame seeds, kunjut urug'i
Zig'ir urug'i | 534 18 42 29 | 0 10 | семена льна, flax seeds, flaxseed, lyon
Chia urug'i | 486 17 31 42 | 0 15 | чиа, chia, chia seeds
Aralash yong'oqlar | 600 18 52 21 | 0 30 | ореховое ассорти, mixed nuts, trail mix, assorti yong'oq
Qovurilgan no'xat | 375 20 6 55 | 0 30 | жареный нут, roasted chickpeas, nohut qovurilgan
Kashtan | 213 2 2 45 | 0 50 | каштан, chestnut, kashtan
Shokolad pastasi (Nutella) | 540 6 31 58 | 0 20 | нутелла, nutella, shokolad pasta, chocolate spread
Tahin | 595 17 54 21 | 0 15 | тахини, tahini, tahin pastasi, kunjut pastasi
# ---- oils, fats and sauces
Zaytun moyi | 898 0 99.8 0 | 0 10 | оливковое масло, olive oil, zaytun yog'i
Paxta moyi | 899 0 99.9 0 | 0 10 | хлопковое масло, cottonseed oil, paxta yog'i, chigit moyi
Kokos moyi | 899 0 99.9 0 | 0 10 | кокосовое масло, coconut oil
Kunjut moyi | 884 0 100 0 | 0 10 | кунжутное масло, sesame oil
Salo (cho'chqa yog'i) | 770 2.4 90 0 | 0 20 | сало, lard, salo, cho'chqa moyi
Mol yog'i | 880 0 98 0 | 0 15 | говяжий жир, tallow, beef fat, mol moyi
Mayonez (klassik) | 620 3 67 2.6 | 0 15 | майонез, mayonnaise, mayonez, mayonaise
Mayonez (yengil) | 260 1 25 8 | 0 15 | лёгкий майонез, light mayonnaise, yengil mayonez
Ketchup | 100 1.5 0.3 25 | 0 20 | кетчуп, ketchup, kechup, ketchap
Tomat sousi | 80 2 0.5 17 | 0 30 | томатный соус, tomato sauce, tomat sous
Soya sousi | 53 8 0.6 5 | 0 15 | соевый соус, soy sauce, soya sous
Xantal (gorchitsa) | 66 4 4 5 | 0 10 | горчица, mustard, xantal, gorchitsa
Pesto | 400 5 40 4 | 0 20 | песто, pesto sous
Sarimsoqli sous | 250 2 22 12 | 0 20 | чесночный соус, garlic sauce, sarimsoq sous
Ranch sous | 430 1 45 6 | 0 20 | ранч, ranch, ranch sous
BBQ sous | 150 1 0.5 36 | 0 20 | барбекю соус, bbq sauce, barbecue sauce
Chili sous (shirin) | 200 0.5 0 50 | 0 20 | сладкий чили, sweet chili sauce, chili sous
Adjika | 100 2.5 6 9 | 0 15 | аджика, adjika, adjika sous
Tkemali | 50 0.6 0.1 12 | 0 20 | ткемали, tkemali sous
Sirka | 20 0 0 0.9 | 0 10 | уксус, vinegar, sirka, olma sirkasi
Tuz | 0 0 0 0 | 0 5 | соль, salt
Zira | 375 18 22 44 | 0 3 | зира, тмин, cumin, kmin, zira ziravor
Zanjabil | 80 1.8 0.8 18 | 0 5 | имбирь, ginger, zanjabil
Dolchin | 247 4 1.2 81 | 0 3 | корица, cinnamon, dolchin, darchin
Bechamel sousi | 120 3 8 9 | 0 50 | бешамель, bechamel, beshamel
# ---- sweets and desserts
Shokolad (qora, 70%) | 560 8 40 33 | 0 20 | горький шоколад, тёмный шоколад, dark chocolate, qora shokolad, bitter chocolate
Shokolad (oq) | 540 6 32 59 | 0 30 | белый шоколад, white chocolate, oq shokolad
Shokolad (yong'oqli) | 550 8 33 52 | 0 30 | шоколад с орехами, nut chocolate, chocolate with nuts
Shokolad batonchik (Snickers) | 490 9 24 61 | 50 50 | сникерс, snickers, snikers
Mars batonchik | 450 4 17 71 | 51 51 | марс, mars, mars baton
Twix | 495 5 24 65 | 50 50 | твикс, tviks
Bounty | 470 4 24 59 | 57 57 | баунти, bounty baton
Karamel konfet | 380 0 0 95 | 8 16 | карамель, леденцы, hard candy, caramel candy, konfet, конфета, конфеты, candy, candies
Shokolad konfet | 450 4 22 60 | 12 24 | шоколадные конфеты, chocolate candy, chocolates, shokoladli konfet
Iris (konfet) | 420 3 8 83 | 10 20 | ирис, toffee, iris
Zefir | 300 1 0 78 | 35 35 | зефир, marshmallow, zefir, marshmallows
Chupa-chups | 380 0 0 97 | 12 12 | чупа-чупс, lollipop, chupachups, lolipop
Halva (kunjutli) | 520 13 30 50 | 0 40 | халва, halva, xalva, halvah, tahini halva
Halva (kungaboqarli) | 516 11.6 29.7 54 | 0 40 | халва подсолнечная, sunflower halva
Halvaytar | 150 3 4 26 | 0 200 | халвайтар, xalvaytar, halvaitar, halwaitar
Chak-chak | 440 6 17 70 | 0 60 | чак-чак, chak chak, chakchak
Navvot | 390 0 0 97 | 0 20 | навот, nabat, navat, rock sugar, кристаллический сахар
Parvarda | 380 1 5 85 | 0 30 | парварда, parvarda
Nishalda | 330 2 6 66 | 0 100 | нишалда, nishalda, nisholda
Pashmak | 380 0 0 95 | 0 30 | пашмак, pashmak, cotton candy, сладкая вата, shakar paxta
Tort (kremli) | 400 4 25 42 | 0 120 | торт, cake, tort, kremli tort, торт кремовый, cream cake
Tort (Napoleon) | 380 5 22 42 | 0 120 | наполеон, napoleon, napoleon torti
Medovik | 370 5 17 49 | 0 120 | медовик, honey cake, medovik
Eklyer | 330 5 20 33 | 60 70 | эклер, eclair, eklyer, pirojnoe, пирожное
Keks | 390 5 17 55 | 60 60 | кекс, cupcake, muffin, маффин, keks, makfin
Brauni | 466 5 29 52 | 50 50 | брауни, brownie
Cheesecake | 320 6 22 26 | 0 120 | чизкейк, chizkeyk, cheese cake
Tiramisu | 280 5 17 28 | 0 120 | тирамису, tiramisu
Baklava | 430 7 25 47 | 40 60 | пахлава, pahlava, baklava, paxlava
Puding | 110 3 3 18 | 0 150 | пудинг, pudding
Jele | 70 2 0 15 | 0 150 | желе, jelly, jele, jelatin
Qaymoqli bulochka | 340 6 15 46 | 80 80 | булочка со сливками, cream bun, qaymoqli bulka
Shakar sirop | 260 0 0 65 | 0 20 | сироп, syrup, sirop, shakar sirop
Kakao kukuni | 228 20 14 58 | 0 10 | какао, какао-порошок, cocoa powder, kakao, cocoa
Maple sirop | 260 0 0 67 | 0 20 | кленовый сироп, maple syrup
Gozinaki | 470 9 25 55 | 0 40 | гозинаки, gozinaki, kozinaki, kozinak
Granola bar | 420 7 15 65 | 30 30 | злаковый батончик, cereal bar, granola baton, muesli bar
Guruch galeta | 380 8 3 80 | 9 18 | рисовые хлебцы, rice cakes, rice cake, guruch non
Xlebsy (dietik non) | 330 11 2 66 | 10 30 | хлебцы, crispbread, hlebtsy, xlebsi, dietic non
# ---- drinks
Suv | 0 0 0 0 | 250 250 | вода, water, suv ichish, mineral suv, gazsiz suv, минеральная вода
Gazli suv | 0 0 0 0 | 250 250 | газированная вода, sparkling water, gazlangan suv, soda water
Choy (limonli) | 3 0 0 0.5 | 200 200 | чай с лимоном, lemon tea, limonli choy
Choy (sutli, shakarsiz) | 20 1 1 2 | 200 200 | чай с молоком, milk tea, sutli choy, sut bilan choy
Choy (1 qand bilan) | 17 0 0 4 | 200 200 | чай с одной ложкой сахара, tea one sugar, bitta qandli choy
Choy (asalli) | 40 0 0 10 | 200 200 | чай с мёдом, tea with honey, asalli choy
Choy (shirin, 3 qand bilan) | 45 0 0 12 | 200 200 | чай с тремя ложками сахара, very sweet tea, 3 qandli choy
Masala choy | 70 2 2 11 | 200 200 | масала чай, masala chai, chai latte, chay
Matcha latte | 60 2.5 2 8 | 250 250 | матча латте, matcha, matcha latte
Qahva (qora, shakarsiz) | 2 0.1 0 0 | 150 150 | кофе, чёрный кофе, coffee, black coffee, qahva, kofe, americano
Qahva (shakar bilan) | 25 0.1 0 6 | 150 150 | кофе с сахаром, coffee with sugar, shakarli qahva, kofe shakar bilan
Qahva (sut bilan) | 40 1.5 1.5 4 | 200 200 | кофе с молоком, coffee with milk, sutli qahva, kofe sut bilan
Kapuchino | 45 2.5 2 4 | 200 200 | капучино, cappuccino, kapuchino
Latte | 55 3 2.5 5 | 250 250 | латте, latte, kofe latte
Espresso | 2 0.1 0 0 | 30 30 | эспрессо, espresso, espresso qahva
Amerikano | 2 0.1 0 0 | 250 250 | американо, americano coffee
Mokko | 90 3 3 12 | 250 250 | мокко, mocha, mokko kofe
Qahva 3 in 1 | 70 1 2 12 | 200 200 | 3 в 1, 3in1, 3 in 1, кофе 3 в 1, nescafe 3 in 1, neskafe, nescafe
Flat white | 50 3 2.5 4 | 200 200 | флэт уайт, flat white coffee
Issiq shokolad | 100 3 3 15 | 200 200 | горячий шоколад, hot chocolate, issiq kakao, hot cocoa
Kakao (sutli) | 77 3.6 3.5 8 | 200 200 | какао с молоком, cocoa with milk, kakao ichimlik
Olma sharbati | 46 0.5 0.1 11 | 0 200 | яблочный сок, apple juice, olma soki
Uzum sharbati | 70 0.3 0 17 | 0 200 | виноградный сок, grape juice, uzum soki
Anor sharbati | 66 0.3 0 16 | 0 200 | гранатовый сок, pomegranate juice, anor soki
Shaftoli sharbati | 55 0.5 0 13 | 0 200 | персиковый сок, peach juice
Pomidor sharbati | 18 0.8 0.1 3.5 | 0 200 | томатный сок, tomato juice, pomidor soki
Sabzi sharbati | 40 1 0.2 9 | 0 200 | морковный сок, carrot juice, sabzi soki
Ananas sharbati | 53 0.4 0.1 13 | 0 200 | ананасовый сок, pineapple juice
Multifrukt sharbat | 50 0.4 0.1 12 | 0 200 | мультифрукт, multifruit juice, mix juice, sok, сок, juice, sharbat
Limonad | 40 0 0 10 | 330 330 | лимонад, lemonade, limonad
Fanta | 42 0 0 10.5 | 330 330 | фанта, orange soda, apelsinli gazli ichimlik
Sprite | 38 0 0 9.5 | 330 330 | спрайт, sprite, 7up, севен ап, lemon lime soda
Kola (shakarsiz) | 0.4 0 0 0 | 330 330 | кола зеро, cola zero, diet cola, coke zero, pepsi max, dietik kola
Gazli ichimlik | 42 0 0 10.5 | 330 330 | газировка, soda, soft drink, gazlangan ichimlik, fizzy drink, mirinda, миринда, dinamit
Energetik ichimlik | 45 0.4 0 11 | 250 250 | энергетик, energy drink, red bull, ред булл, flash, adrenaline, burn, flesh, energetik
Kompot | 40 0.2 0 10 | 200 200 | компот, compote, mevali kompot, kompot ichimlik
Uzvar | 55 0.4 0 14 | 200 200 | узвар, dried fruit compote, quritilgan mevalar kompoti
Kisel | 55 0.1 0 14 | 200 200 | кисель, kissel, kisel
Kvas | 27 0.2 0 5.2 | 250 250 | квас, kvas, kvass
Mors | 40 0.1 0 10 | 200 200 | морс, mors, fruit drink
Ice tea | 30 0 0 7.5 | 330 330 | холодный чай, iced tea, ice tea, muzli choy, lipton ice tea
Sut kokteyli | 112 3 3 18 | 250 250 | молочный коктейль, milkshake, milk shake, kokteyl
Yogurt ichimlik | 70 3 1.5 11 | 250 250 | питьевой йогурт, drinking yogurt, ichimlik yogurt
Smuzi | 70 1 0.5 15 | 250 250 | смузи, smoothie, smuzi mevali
Protein kokteyli (tayyor) | 70 12 1.5 3 | 330 330 | готовый протеиновый коктейль, ready protein shake, protein shake, protein kokteyl
Pivo (och) | 43 0.5 0 3.6 | 500 500 | пиво, beer, pivo, lager, light beer, пиво светлое
Pivo (qorong'i) | 48 0.5 0 4.5 | 500 500 | тёмное пиво, dark beer, stout
Pivo (alkogolsiz) | 25 0.4 0 5 | 500 500 | безалкогольное пиво, non alcoholic beer, alkogolsiz pivo
Vino (qizil) | 85 0.1 0 2.6 | 150 150 | красное вино, red wine, vino, вино
Vino (oq) | 82 0.1 0 2.6 | 150 150 | белое вино, white wine, oq vino
Aroq | 235 0 0 0.1 | 50 50 | водка, vodka, aroq, arak
Konyak | 239 0 0 0.5 | 50 50 | коньяк, cognac, brandy, konyak
Viski | 250 0 0 0.1 | 50 50 | виски, whiskey, whisky
Shampan | 88 0.2 0 5 | 150 150 | шампанское, champagne, sparkling wine, shampan vinosi
Sidr | 45 0 0 4 | 330 330 | сидр, cider
Boza | 50 1 0.3 11 | 250 250 | боза, bozа, boza ichimlik
Kokos suvi | 19 0.7 0.2 3.7 | 250 250 | кокосовая вода, coconut water
Soya suti | 40 3.3 1.8 2 | 250 250 | соевое молоко, soy milk
Bodom suti | 24 0.8 1.1 3 | 250 250 | миндальное молоко, almond milk
Suli suti | 45 1 1.5 7 | 250 250 | овсяное молоко, oat milk
Izotonik ichimlik | 25 0 0 6 | 500 500 | изотоник, isotonic drink, gatorade, powerade, sport drink
# ---- sports nutrition
Gainer | 380 20 3 70 | 100 100 | гейнер, mass gainer, gainer kukuni, massa gainer
Whey izolyat | 370 90 1 2 | 30 30 | изолят, whey isolate, protein isolate, izolyat
Kazein | 370 78 2 8 | 30 30 | казеин, casein, kazein protein
Protein bar (kam shakarli) | 350 33 13 24 | 60 60 | low sugar protein bar, протеиновый батончик без сахара, quest bar, bombbar, бомбар
Protein pechenye | 380 20 15 40 | 50 50 | протеиновое печенье, protein cookie
Energetik gel | 250 0 0 62 | 40 40 | энергетический гель, energy gel, sport gel
Kreatin | 0 0 0 0 | 5 5 | креатин, creatine, kreatin monogidrat
BCAA | 0 0 0 0 | 8 8 | бцаа, bcaa, aminokislotalar, amino acids
"""
