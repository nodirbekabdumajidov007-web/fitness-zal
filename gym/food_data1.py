"""Built-in food table, part 1 (dishes, fast food, grains and bread). Parsed by gym/food_db.py.

Line format:  Name | kcal protein fat carbs (per 100 g) | piece_g portion_g | alias, alias, ...
piece_g = grams of one piece (0 = not counted in pieces); portion_g = usual portion (0 = use the piece).
Aliases are uz (Latin, apostrophes optional), ru (Cyrillic) and en words or phrases. The name itself is an alias too, unless the alias
list starts with "=" (then only the listed aliases count).
The first 68 rows are the original table of the calorie page: keep their order, saved entries and links refer to the row number.
Rows may only be appended, never reordered.
"""

RAW = """
# ---- original table (do not reorder)
Osh (palov) | 200 6 9 24 | 0 250 | plov, palov, плов, pilaf, pilav, plof, uzbek pilaf, o'zbek oshi
Lag'mon | 135 6 5 17 | 0 350 | lagmon, lagman, лагман, laghman, lagmon sho'rvali
Manti | 210 9 10 20 | 70 210 | манты, мант, manty, steamed dumplings
Somsa (go'shtli) | 290 9 17 26 | 120 120 | somsa, samsa, самса, самсы, samosa, go'shtli somsa, meat samsa
Shashlik (mol go'shti) | 230 24 15 0 | 80 160 | shashlik, shashlyk, шашлык, kebab, kabob, кебаб, shish kebab, mol shashlik, beef kebab
Shashlik (qo'y go'shti) | 260 22 19 0 | 80 160 | qo'y shashlik, шашлык из баранины, lamb kebab, lamb shashlik
Non (tandir) | 260 8 1 54 | 150 150 | non, хлеб, лепёшка, лепешка, bread, tandir non, flatbread, нон
Oq non | 265 8 3 50 | 30 100 | white bread, белый хлеб, батон, baton, buxanka, булка хлеба
Guruch (pishirilgan) | 130 2.7 0.3 28 | 0 200 | guruch, рис, rice, boiled rice, отварной рис
Grechka (pishirilgan) | 110 4 1 21 | 0 200 | grechka, grecha, гречка, гречневая каша, buckwheat
Suli bo'tqasi (suvda) | 70 2.5 1.4 12 | 0 250 | suli, овсянка, овсяная каша, oatmeal, oat porridge, porridge, gerkules, геркулес
Makaron (pishirilgan) | 160 5.5 1 31 | 0 200 | makaron, макароны, pasta, spagetti, спагетти, spaghetti, vermishel
Kartoshka (qaynatilgan) | 82 2 0.4 17 | 0 200 | kartoshka, картошка, картофель, potato, boiled potato, отварной картофель
Kartoshka fri | 310 3.8 15 41 | 0 150 | kartoshka fri, fri, картофель фри, french fries, fries, fri kartoshka
Tuxum (qaynatilgan) | 155 13 11 1.1 | 55 55 | tuxum, tuhum, яйцо, яйца, яйц, egg, eggs, boiled egg, варёное яйцо
Omlet | 185 11 14 2 | 0 150 | омлет, omelette, omelet
Tovuq ko'kragi (pishirilgan) | 165 31 3.6 0 | 0 150 | tovuq, tovuq ko'kragi, курица, куриная грудка, грудка, chicken, chicken breast, boiled chicken
Tovuq go'shti (qovurilgan) | 240 27 14 0 | 0 150 | qovurilgan tovuq, жареная курица, fried chicken, tovuq qovurma
Mol go'shti (qaynatilgan) | 250 26 16 0 | 0 150 | mol, mol go'shti, говядина, говядин, beef, boiled beef
Qo'y go'shti (qaynatilgan) | 290 25 21 0 | 0 150 | qo'y go'shti, баранина, lamb, mutton, qoy
Baliq (qaynatilgan) | 130 22 4.5 0 | 0 150 | baliq, рыба, fish, boiled fish
Tuna (konserva) | 116 26 1 0 | 0 100 | tuna, тунец, tuna konserva, tunets
Kolbasa (qaynatilgan) | 300 12 28 1.5 | 50 100 | kolbasa, колбаса, sausage, doktorskaya
Sut (2.5%) | 52 2.9 2.5 4.7 | 0 200 | sut, молоко, milk
Kefir (2.5%) | 53 3 2.5 4 | 0 200 | kefir, кефир
Qatiq | 60 3 3.2 4 | 0 200 | катык, yogurt, йогурт, yoghurt, qatiq
Tvorog (5%) | 121 17 5 3 | 0 150 | tvorog, творог, cottage cheese, twarog
Tvorog (past yog'li) | 88 18 1 3 | 0 150 | yog'siz tvorog, обезжиренный творог, low fat cottage cheese, nonfat tvorog
Pishloq | 350 25 27 1 | 20 30 | сыр, cheese, pishloq, syr
Smetana (20%) | 206 2.8 20 3.2 | 0 30 | smetana, сметана, sour cream
Sariyog' | 717 0.8 81 0.6 | 10 10 | масло сливочное, сливочное масло, butter, sariyog
O'simlik moyi | 899 0 99.9 0 | 0 10 | o'simlik yog'i, ўсимлик ёғи, подсолнечное масло, растительное масло, vegetable oil, sunflower oil, moy
Banan | 89 1.1 0.3 23 | 120 120 | банан, banana
Olma | 52 0.3 0.2 14 | 180 180 | яблоко, яблок, apple
Uzum | 69 0.7 0.2 18 | 0 100 | виноград, grape, grapes, kishmish uzum
Behi | 57 0.4 0.1 15 | 0 150 | айва, quince
Anor | 83 1.7 1.2 19 | 0 150 | гранат, pomegranate
Apelsin | 47 0.9 0.1 12 | 150 150 | апельсин, orange
Qovun | 35 0.8 0.2 8 | 0 200 | дыня, melon, sariq qovun
Tarvuz | 30 0.6 0.2 8 | 0 300 | арбуз, watermelon
O'rik (quritilgan) | 241 3.4 0.5 63 | 0 30 | = quritilgan o'rik, o'rik quritilgan, курага, урюк, dried apricot, dried apricots, uryuk, kuraga
Mayiz | 299 3 0.5 79 | 0 30 | изюм, raisin, raisins, kishmish, кишмиш
Yong'oq (grek) | 654 15 65 14 | 0 30 | yong'oq, грецкий орех, грецкие орехи, грецк, walnut, walnuts, grek yong'og'i
Bodom | 579 21 50 22 | 0 30 | миндаль, миндал, almond, almonds
Pista | 560 20 45 28 | 0 30 | фисташки, фисташк, pistachio, pistachios
Pomidor | 18 0.9 0.2 3.9 | 100 100 | помидор, томат, tomato, tomatoes
Bodring | 15 0.7 0.1 3.6 | 100 100 | огурец, огурцы, cucumber
Sabzi | 41 0.9 0.2 10 | 80 80 | морковь, carrot, carrots
Piyoz | 40 1.1 0.1 9 | 100 50 | лук, репчатый лук, onion, onions
Karam | 25 1.3 0.1 6 | 0 100 | капуста, cabbage, oq karam
Shirchoy (sho'rva) | 60 3 3 5 | 0 300 | = shirchoy, ширчой, shir choy
Mastava | 75 4 3 8 | 0 300 | мастава, mastava sho'rva
Sho'rva | 70 5 4 4 | 0 300 | shorva, shurva, shurpa, шурпа, шорва, суп, soup, go'shtli sho'rva
Dimlama | 120 7 7 8 | 0 300 | димлама, димляма, dimlama go'shtli
Chuchvara | 230 11 10 25 | 0 200 | пельмени, пельмень, dumpling, dumplings, pelmeni, chuchvara qaynatma
Qozon kabob | 280 17 20 7 | 0 200 | qozon kebab, qozon kabob, казан кебаб, казан-кабоб, kazan kebab
Pitsa | 266 11 10 33 | 110 110 | pizza, пицца, пицц, pitsa
Burger | 250 13 12 22 | 200 200 | бургер, гамбургер, gamburger, hamburger, burger
Shokolad (sutli) | 535 7.7 30 59 | 0 40 | shokolad, шоколад, chocolate, milk chocolate
Pechenye | 440 6.5 17 66 | 12 36 | печенье, cookie, cookies, biscuit, biscuits, pecheniye
Qand | 387 0 0 100 | 0 10 | shakar, сахар, sugar, qand-shakar
Asal | 304 0.3 0 82 | 0 20 | мёд, мед, honey
Choy (shakarsiz) | 1 0 0 0.2 | 200 200 | choy, чай, tea, qora choy, black tea, ko'k choy, green tea, зелёный чай, чёрный чай
Choy (2 qand bilan) | 30 0 0 8 | 200 200 | shakarli choy, qandli choy, чай с сахаром, sweet tea, choy qand bilan
Kola | 42 0 0 10.6 | 330 330 | кола, cola, coke, coca cola, coca-cola, pepsi, пепси
Apelsin sharbati | 45 0.7 0.2 10 | 0 200 | апельсиновый сок, orange juice, apelsin soki
Protein kukuni (whey) | 400 80 6 8 | 30 30 | protein, протеин, whey, whey protein, protein powder, protein kukuni
Protein batonchik | 370 30 12 35 | 60 60 | protein bar, протеиновый батончик, protein baton, protein batonchik

# ---- Uzbek and Central Asian dishes: osh and rice
Toy oshi | 215 6 11 23 | 0 300 | to'y oshi, свадебный плов, wedding plov, wedding pilaf
Toshkent oshi | 205 5.5 10 23 | 0 300 | тошкент ош, ташкентский плов, tashkent plov
Samarqand oshi | 210 6.5 9 26 | 0 300 | samarqand osh, самаркандский плов, samarkand plov, no'xatli osh
Osh (qo'y go'shtli) | 230 7 12 23 | 0 300 | qo'y go'shtli osh, плов с бараниной, lamb plov
Osh (mol go'shtli) | 210 7 10 23 | 0 300 | mol go'shtli osh, плов с говядиной, beef plov
Osh (tovuqli) | 175 8 6 23 | 0 300 | tovuqli osh, плов с курицей, chicken plov
Dietetik osh | 150 6 4 22 | 0 300 | yog'siz osh, диетический плов, diet plov, light plov, low fat plov
Devzira oshi | 200 6 9 25 | 0 300 | devzira osh, девзира, devzira plov
Mosh guruch | 125 5.5 3 20 | 0 300 | moshguruch, мош гуруч, машкичири, mashkichiri, mung bean rice
Moshxo'rda | 90 5 3 11 | 0 300 | mosh sho'rva, маш-хурда, машхурда, moshkurda, mung bean soup
Shavla | 150 5 5 22 | 0 300 | шавла, shavla go'shtli, savla
Bo'tqa (guruchli, sutli) | 105 3 3 16 | 0 250 | sutli guruch bo'tqasi, молочная рисовая каша, rice milk porridge, guruch bo'tqasi
Sumalak | 200 3 4 38 | 0 150 | сумалак, sumalak, wheat sprout pudding
# ---- soups
Mastava (go'shtli) | 85 5 3.5 9 | 0 300 | go'shtli mastava, мастава с мясом, meat mastava
Sho'rva (tovuqli) | 45 4 2 3 | 0 300 | tovuqli sho'rva, куриный суп, chicken soup, куриный бульон
Sho'rva (qo'y go'shtli) | 90 6 6 4 | 0 300 | qo'y sho'rva, шурпа из баранины, lamb soup
Sho'rva (baliq) | 50 6 2 2 | 0 300 | baliq sho'rvasi, уха, ukha, fish soup
No'xat sho'rva | 85 5 2 12 | 0 300 | nohut shorva, нутовый суп, chickpea soup, no'xatli sho'rva, sho'rnoxot
Yasmiq sho'rva | 75 5 1.5 11 | 0 300 | чечевичный суп, lentil soup, yasmiq sho'rvasi
Loviya sho'rva | 70 4.5 1.5 10 | 0 300 | фасолевый суп, bean soup, loviyali sho'rva
Lapsha sho'rva (tovuqli) | 45 3 1.5 5 | 0 300 | куриный суп с лапшой, chicken noodle soup, tovuq lapsha
Sabzavot sho'rva | 35 1.2 1.2 5 | 0 300 | овощной суп, vegetable soup, sabzavotli sho'rva
Bulyon (go'sht) | 15 2 0.5 0.3 | 0 250 | бульон, broth, bulyon, go'sht suvi, sho'rva suvi
Umoch | 90 3 2 15 | 0 300 | умач, umoch oshi, flour soup
Atala | 80 2 3 12 | 0 250 | атала, atala sho'rva
Kuk chuchvara | 160 7 5 20 | 0 250 | ko'k chuchvara, зелёные пельмени, herb dumplings
Chuchvara (sho'rvada) | 120 6 4 14 | 0 350 | chuchvara sho'rva, пельмени в бульоне, dumpling soup
Chuchvara (qovurilgan) | 290 10 17 25 | 0 200 | qovurma chuchvara, жареные пельмени, fried dumplings
Chalop | 40 1.5 2 3 | 0 300 | чалоп, chalop, qatiq chalop, ayron sho'rva
Okroshka (kefirda) | 55 3 2.5 5 | 0 300 | okroshka, окрошка, okroshka kefir
# ---- meat dishes
Beshbarmoq | 190 10 12 10 | 0 350 | beshbarmoq, бешбармак, besh barmoq, beshbarmak, norin go'sht
Norin | 215 12 12 15 | 0 300 | нарын, норин, naryn, narin, norin go'shtli
Qovurma (go'sht) | 300 22 22 3 | 0 200 | qovurma, жареное мясо, fried meat, go'sht qovurma
Qovurdoq | 250 14 18 8 | 0 250 | qovurdoq go'sht, жаркое, kovurdoq, roast meat potatoes
Jarkop | 260 15 18 12 | 0 250 | жаркоп, jarkop go'sht, jarkop
Do'lma | 160 8 8 14 | 50 200 | dolma, долма, dolma uzum bargida, stuffed grape leaves
Karam dolma | 100 6 5 8 | 100 200 | golubtsy, голубцы, stuffed cabbage, golubsi, karam do'lma
Baqlajon do'lma | 110 5 6 9 | 0 200 | stuffed eggplant, фаршированные баклажаны, baklajon dolma
Qalampir do'lma | 105 5 5 9 | 0 200 | перец фаршированный, stuffed pepper, bolgar qalampiri dolma
Xonim | 190 6 8 24 | 0 250 | ханум, hanum, xonim, steamed rolls, ханум мясной
Manti (qovoqli) | 130 3 4 20 | 70 210 | qovoqli manti, манты с тыквой, pumpkin manti, pumpkin dumplings
Manti (kartoshkali) | 150 4 5 22 | 70 210 | kartoshkali manti, манты с картошкой, potato manti
Manti (tovuqli) | 190 10 8 20 | 70 210 | tovuqli manti, манты с курицей, chicken manti
Tuxum barak | 190 8 9 20 | 0 200 | tuhum barak, tuxumbarak, яйцо барак
Lyulya kabob | 250 17 19 3 | 100 150 | lula kabob, lulya, люля-кебаб, люля кебаб, lula kebab, lyulya kebab, qiyma kabob, minced kebab
Tandir kabob | 270 22 20 0 | 0 150 | tandir kebab, тандыр кебаб, tandoor kebab, tandir go'sht
Jigar kabob | 190 22 10 1 | 60 120 | jigar shashlik, печёночный шашлык, liver kebab, jigar kebab
Shashlik (tovuq go'shti) | 180 25 8 1 | 80 160 | tovuq shashlik, шашлык из курицы, chicken kebab, chicken shashlik, tovuq kabob
Shashlik (dumba) | 450 12 45 0 | 40 80 | dumba shashlik, курдючный шашлык, fat tail kebab, dumbali shashlik
Dumba | 800 2 85 0 | 0 20 | dumba yog'i, курдючный жир, курдюк, lamb tail fat, qo'y dumbasi, sheep tail fat
Qazi | 330 14 30 1 | 0 100 | казы, kazy, horse sausage, ot kolbasasi
Qarta | 260 15 18 5 | 0 100 | карта, karta, qarta jigari, horse intestine
Tandir go'sht | 280 24 20 0 | 0 150 | тандыр гошт, tandoor meat, baked lamb
Jiz-biz | 380 15 33 5 | 0 200 | jizbiz, жиз-быз, jizz-byz, jiz biz
Bo'g'irsoq | 400 7 22 45 | 25 75 | boursak, баурсаки, boirsok, baursak, bog'irsoq
# ---- somsa and pastries
Somsa (tandir, qo'y go'shtli) | 300 9 18 26 | 120 120 | tandir somsa, тандырная самса, tandoor samsa, qo'y somsa
Somsa (qatlama) | 330 9 22 25 | 100 100 | qatlama somsa, слоёная самса, layered samsa, puff samsa
Somsa (qovoqli) | 220 4 11 26 | 110 110 | qovoqli somsa, самса с тыквой, pumpkin samsa
Somsa (kartoshkali) | 240 5 12 28 | 110 110 | kartoshkali somsa, самса с картошкой, potato samsa
Somsa (tovuqli) | 270 11 14 26 | 110 110 | tovuqli somsa, самса с курицей, chicken samsa
Somsa (jigarli) | 280 11 16 24 | 110 110 | jigarli somsa, самса с печенью, liver samsa
Somsa (pishloqli) | 310 11 18 27 | 100 100 | pishloqli somsa, самса с сыром, cheese samsa
Somsa (ko'katli) | 230 5 11 26 | 100 100 | ko'katli somsa, самса с зеленью, herb samsa
Gumma | 260 8 12 31 | 0 200 | гумма, gumma go'shtli, meat pie
Pirojki (go'shtli) | 260 8 12 31 | 60 120 | pirozhki, пирожки, pirojki, pirojok, пирожок с мясом, meat pie small
Pirojki (kartoshkali) | 240 5 9 36 | 60 120 | пирожок с картошкой, potato pirozhki, kartoshkali pirojki
Chebureki | 300 10 18 26 | 100 100 | чебурек, cheburek, chebureki, чебуреки
Belyash | 290 9 17 27 | 100 100 | беляш, belyash, byalyash
Pirog (olmali) | 240 3 9 37 | 0 120 | яблочный пирог, apple pie, olmali pirog
Qatlama | 330 6 18 36 | 100 100 | катлама, qatlama non, katlama
# ---- salads and sides
Achichuk | 20 1 0.1 4 | 0 150 | аччик-чучук, ачучук, shakarob, achchiq-chuchuk, tomato onion salad
Koreyscha sabzi | 120 1.5 8 11 | 0 100 | morkovcha, морковча, korean carrot, sabzi koreyscha, морковь по-корейски
Pomidor-bodring salat | 45 1 3.5 3 | 0 200 | salat pomidor bodring, салат из огурцов и помидоров, cucumber tomato salad, sabzavot salati
Karam salat | 55 1.3 3.5 5 | 0 150 | салат из капусты, cabbage salad, coleslaw
Sabzi salat | 70 1 4 8 | 0 100 | салат из моркови, carrot salad
Kartoshka pyure | 106 2 4 15 | 0 200 | pyure, пюре, картофельное пюре, mashed potatoes, kartoshka pyuresi
Qovurilgan kartoshka | 190 3 10 22 | 0 200 | жареная картошка, fried potatoes, kartoshka qovurma
Pechdagi kartoshka | 90 2.5 0.1 21 | 0 200 | запечённый картофель, baked potato, tandir kartoshka
Draniki | 200 4 10 24 | 40 150 | драники, картофельные оладьи, potato pancakes, hash browns, kartoshka oladyi
# ---- Russian and European dishes
Borsch | 50 2 2.5 5 | 0 300 | borsh, борщ, borscht, borsch
Shchi | 35 1.5 1.8 3.5 | 0 300 | щи, kapustnyj sup, cabbage soup
Solyanka | 70 5 4 3 | 0 300 | солянка, solyanka, meat solyanka
Rassolnik | 50 2 2.5 5 | 0 300 | рассольник, rassolnik
Kharcho | 95 5 5 7 | 0 300 | харчо, xarcho, kharcho soup
Pelmeni (do'kon) | 275 12 14 25 | 15 200 | пельмени магазинные, store dumplings, pelmeni go'shtli, pel'meni
Vareniki (kartoshkali) | 160 4 4 27 | 25 200 | вареники с картошкой, potato vareniki, varenik, вареники
Vareniki (tvorogli) | 190 8 5 28 | 25 200 | вареники с творогом, cottage cheese vareniki, tvorogli vareniki
Blin | 233 6 12 26 | 40 120 | bliny, блины, блин, pancake, pancakes, blinchik, blini
Oladyi | 230 6 10 29 | 30 120 | оладьи, оладушки, oladi, fritters
Syrniki | 220 14 11 18 | 60 120 | сырники, sirniki, cottage cheese pancakes, tvorogli oladyi
Blinchik (tvorogli) | 190 8 8 22 | 60 120 | блинчики с творогом, crepes with cottage cheese, tvorogli blin
Blinchik (go'shtli) | 220 10 11 20 | 60 120 | блинчики с мясом, crepes with meat, go'shtli blin
Kotlet (mol go'shtli) | 250 14 17 10 | 80 100 | kotlet, котлета, cutlet, mol kotlet, котлета говяжья, frikadelka, teftel
Kotlet (tovuq) | 190 14 10 9 | 80 100 | tovuq kotlet, куриная котлета, chicken cutlet, chicken patty
Beef stroganov | 190 14 13 4 | 0 250 | befstroganov, бефстроганов, stroganoff, bef stroganov
Gulyash | 130 8 9 4 | 0 250 | гуляш, goulash, gulyash
Yaichnitsa (qovurilgan tuxum) | 196 14 15 1 | 55 110 | yaichnitsa, яичница, fried egg, fried eggs, qovurilgan tuxum, tuxum qovurma, glazunya
Tuxum (xom) | 143 12.5 10 0.7 | 55 55 | xom tuxum, сырое яйцо, raw egg
Tuxum oqi | 52 11 0.2 0.7 | 33 33 | белок яйца, egg white, egg whites, tuxum oqligi, яичный белок
Tuxum sarig'i | 322 16 27 3.6 | 17 17 | желток, egg yolk, tuxum sarigi
Bedana tuxumi | 168 12 13 0.6 | 10 50 | перепелиные яйца, quail egg, quail eggs
Olivye | 190 5 15 8 | 0 150 | оливье, olivier, olive salad, stolichniy, salat olive, russian salad
Vinegret | 75 1.5 5 7 | 0 150 | винегрет, vinaigrette, vinegret salat, beet salad
Seld shuba ostida | 190 6 13 11 | 0 150 | селёдка под шубой, shuba, шуба, herring under fur coat, shuba salat
Mimoza salat | 210 7 16 8 | 0 150 | мимоза, mimosa salad, mimoza
Krab salat | 150 5 10 9 | 0 150 | крабовый салат, crab salad, krab salati
Sezar salat | 180 8 13 8 | 0 200 | цезарь, caesar salad, caesar, sezar
Yunon salat | 100 3 8 4 | 0 200 | греческий салат, greek salad, grecheskiy
Ko'katli salat | 50 1.5 3 4 | 0 150 | зелёный салат, green salad, salat bargi salat
Hot-dog | 247 10 14 20 | 150 150 | hotdog, хот-дог, хот дог, hot dog, xotdog
Sendvich (kolbasa, pishloq) | 260 11 12 26 | 150 150 | sendvich, сэндвич, sandwich, sandwich kolbasa, buterbrod sendvich
Buterbrod (kolbasa) | 270 10 14 25 | 60 60 | бутерброд с колбасой, sandwich with sausage, buterbrod
Buterbrod (pishloq) | 300 12 16 27 | 60 60 | бутерброд с сыром, cheese sandwich, pishloqli buterbrod
Buterbrod (sariyog') | 330 5 20 33 | 40 40 | бутерброд с маслом, bread and butter, sariyog'li non
Tost (sendvich) | 290 12 14 29 | 100 100 | тост, toast, tost, grill sandwich, grilled cheese
# ---- fast food
Cheeseburger | 280 15 14 24 | 120 120 | chizburger, чизбургер, cheese burger
Big burger | 257 12.8 12.5 20 | 215 215 | big mac, биг мак, bigmak, katta burger, double burger
Chicken burger | 245 12 11 24 | 180 180 | tovuq burger, чикен бургер, chickenburger, чикенбургер
Pizza (Margarita) | 250 11 10 28 | 110 110 | pitsa margarita, пицца маргарита, margherita, margarita
Pizza (pepperoni) | 290 13 14 28 | 110 110 | pitsa pepperoni, пицца пепперони, pepperoni pizza
Pizza (4 pishloq) | 280 12 15 25 | 110 110 | пицца четыре сыра, four cheese pizza, 4 pishloq
Pizza (tovuqli) | 245 12 9 29 | 110 110 | tovuqli pitsa, пицца с курицей, chicken pizza
Shawarma (tovuq) | 200 11 9 19 | 300 300 | shaurma, шаурма, shawarma, lavash tovuq, doner tovuq, шаверма, shaverma, chicken shawarma
Shawarma (mol/qo'y) | 230 11 12 18 | 300 300 | shaurma go'shtli, шаурма с говядиной, beef shawarma, doner, donar, doner kebab, donar kebab
Lavash rulet (go'shtli) | 210 10 9 22 | 250 250 | lavash, lavash rulet, лаваш ролл, lavash roll, rulet
Naggets | 270 15 17 15 | 20 120 | nuggets, наггетсы, chicken nuggets, nagget, nuggetsy
Tovuq qanotchalari (qovurilgan) | 290 22 20 6 | 40 160 | chicken wings, куриные крылышки, wings, qanotchalar, kfc wings
Tovuq stripslari | 260 17 14 17 | 30 120 | chicken strips, стрипсы, strips, strips tovuq
Onion rings | 290 4 17 31 | 15 100 | луковые кольца, piyoz halqalari, piyoz rings
Taco | 226 9 13 20 | 100 100 | тако, tako, tacos
Burrito | 210 8 8 28 | 250 250 | буррито, burrito go'shtli
Panini | 250 11 10 29 | 180 180 | панини, panini sendvich
Sendvich (tovuqli, kichik) | 180 12 4 25 | 250 250 | subway, sabvey, subway sendvich, chicken sub, сэндвич с курицей, tovuqli sendvich, sendvich tovuqli
Donat | 420 5 22 50 | 60 60 | donut, doughnut, пончик, пончики, donat shirin
Kruassan | 406 8 21 46 | 60 60 | croissant, круассан, kruasan, kruassan oddiy
Kruassan (shokoladli) | 420 7 22 49 | 70 70 | шоколадный круассан, chocolate croissant
Sosiska | 270 11 24 2 | 50 100 | сосиска, сосиски, frankfurter, sosiski, sosiskalar
Sosiska (tovuq) | 220 13 18 2 | 50 100 | куриные сосиски, chicken sausage, tovuq sosiska
Mozzarella tayoqchalari | 300 12 17 23 | 25 100 | сырные палочки, mozzarella sticks, cheese sticks, pishloq tayoqcha
Falafel | 333 13 18 32 | 17 100 | фалафель, falafel
Xummus | 166 8 10 14 | 0 50 | hummus, хумус, humus
Sushi (rolli) | 150 5 3 26 | 30 150 | sushi, суши, roll, роллы, ролл, rolls, sushi roll
Roll Filadelfiya | 190 7 8 21 | 30 180 | филадельфия, philadelphia roll, filadelfiya
Chips (kartoshka) | 540 6 35 50 | 0 40 | chipsy, чипсы, chips, lays, layz, kartoshka chipsi
Popkorn | 480 7 25 56 | 0 50 | попкорн, popcorn, popkorn sho'r
Suxarik | 400 11 10 68 | 0 30 | сухарики, croutons, suxariki, сухарик
Kreker | 430 9 15 64 | 0 30 | крекер, cracker, crackers, kreker, krakers
Lapsha (tez tayyorlanadigan, xom) | 450 9 18 62 | 0 80 | doshirak, дошираки, instant noodles, лапша быстрого приготовления, rolton, роллтон, tez tayyor lapsha
Lapsha (tez tayyor, tayyor holda) | 120 3 5 16 | 0 300 | doshirak tayyor, приготовленная лапша быстрого приготовления, prepared instant noodles
Pasta karbonara | 190 7 9 20 | 0 250 | карбонара, carbonara, makaron karbonara
Pasta bolonez | 160 7 6 20 | 0 250 | болоньезе, bolognese, makaron bolonez, spaghetti bolognese
Lazanya | 150 8 7 14 | 0 250 | лазанья, lasagna, lasagne
Rizotto | 160 4 5 24 | 0 250 | ризотто, risotto
Makaron pishloqli | 190 8 7 24 | 0 250 | макароны с сыром, mac and cheese, makaron pishloq bilan, mac n cheese
Flatbread pizza (lahmacun) | 230 10 8 29 | 150 150 | лахмаджун, lahmacun, lahmajun, lahmacun, turkcha pitsa
# ---- grains, cereals, pasta, bread
Guruch (xom) | 340 7 0.6 76 | 0 60 | xom guruch, рис сырой, raw rice, guruch quruq
Guruch (jigarrang, pishirilgan) | 112 2.3 0.8 23 | 0 200 | бурый рис, brown rice, jigarrang guruch
Grechka (xom) | 313 13 3.4 62 | 0 60 | xom grechka, гречка сухая, raw buckwheat
Suli yormasi (xom) | 366 12 6.5 61 | 0 40 | oat flakes, овсяные хлопья, ovsyanka xom, rolled oats, dry oats, gerkules xom, suli xom
Suli bo'tqasi (sutda) | 110 4 4 15 | 0 250 | sutli suli, овсянка на молоке, oatmeal with milk
Arpa bo'tqasi | 110 3 0.5 22 | 0 200 | перловка, перловая каша, barley porridge, arpa, perlovka
Tariq bo'tqasi | 90 3 1 17 | 0 200 | пшённая каша, пшено, millet porridge, tariq
Manniy bo'tqa | 80 3 3 11 | 0 200 | манка, манная каша, semolina porridge, manniy, manna
Guruch bo'tqasi (sutli) | 105 3 3 16 | 0 250 | рисовая каша на молоке, milk rice porridge
Makka bo'tqasi | 85 2 1 17 | 0 200 | мамалыга, polenta, corn porridge, mamaliga, makka
Kuskus (pishirilgan) | 112 3.8 0.2 23 | 0 200 | кускус, couscous, kuskus
Bulgur (pishirilgan) | 83 3 0.2 19 | 0 200 | булгур, bulgur, bulgur pishirilgan
Kinoa (pishirilgan) | 120 4.4 1.9 21 | 0 200 | киноа, quinoa, kinoa
Mosh (pishirilgan) | 105 7 0.4 19 | 0 200 | маш, mung beans, mosh, mash
Mosh (xom) | 347 24 1.2 63 | 0 60 | xom mosh, маш сухой, raw mung beans
No'xat (pishirilgan) | 164 9 2.6 27 | 0 200 | nohut, нут, chickpeas, chickpea, no'xat, nuxat
No'xat (xom) | 364 19 6 61 | 0 60 | xom no'xat, нут сухой, dry chickpeas
Loviya (pishirilgan) | 127 9 0.5 23 | 0 200 | фасоль, beans, loviya, lobiya, kidney beans, boiled beans
Loviya (xom) | 333 24 1 60 | 0 60 | xom loviya, фасоль сухая, dry beans
Yasmiq (pishirilgan) | 116 9 0.4 20 | 0 200 | чечевица, lentils, yasmiq, lentil
Yasmiq (xom) | 352 25 1.1 60 | 0 60 | xom yasmiq, чечевица сухая, dry lentils
Yashil no'xat (konserva) | 70 4 0.3 12 | 0 100 | горошек зелёный, green peas, konserva no'xat, green peas canned, gorosheк
Makkajo'xori (qaynatilgan) | 96 3.4 1.5 21 | 150 150 | кукуруза варёная, boiled corn, corn on the cob, makka qaynatilgan, makkajo'xori
Makkajo'xori (konserva) | 80 2.5 1 14 | 0 100 | кукуруза консервированная, canned corn, sweet corn, konserva makka
Tofu | 76 8 4.8 1.9 | 0 100 | тофу, soy cheese, tofu pishloq
Soya go'shti (xom) | 345 52 1 30 | 0 40 | соевое мясо, soy meat, soy protein, soya
Makaron (xom) | 350 12 1.5 70 | 0 80 | xom makaron, макароны сухие, dry pasta, raw pasta
Lapsha (pishirilgan) | 110 3.5 0.5 22 | 0 200 | lapsha, лапша, noodles, vermishel pishirilgan, egg noodles
Guruch lapshasi | 109 0.9 0.2 25 | 0 200 | рисовая лапша, rice noodles, funchoza, фунчоза, funchose
Udon | 130 4 0.5 27 | 0 200 | удон, udon noodles
Nyoki | 130 3 1 27 | 0 200 | ньокки, gnocchi
Non (butun, tandir) | 260 8 1 54 | 250 250 | butun non, tandir non butun, lepyoshka, whole flatbread, obi nonli, lepeshka
Obi non | 270 8 3 54 | 300 300 | оби нон, obi-non, obinon, uzbek bread
Patir | 340 8 14 44 | 250 250 | патыр, patir non, yog'li non, fatir
Lochira | 280 8 6 50 | 120 120 | лочира, lochira non, lochira
Shirmoy non | 380 8 14 56 | 80 80 | ширмон, shirmoy, shirmon, sutli non, sweet bread
Kulcha | 300 8 8 50 | 80 80 | кулча, kulcha non, kulcha
Zog'ora non | 320 8 6 60 | 60 60 | zogora, зогора, zog'ora, cornbread
Bulka (shirin) | 290 8 7 50 | 80 80 | булочка, bulochka, bulka, bun, булка, sweet bun, bulochka shirin
Baget | 270 9 1 54 | 250 60 | багет, baguette, baget
Tost non | 265 8 3 49 | 25 50 | тостовый хлеб, toast bread, sliced bread, tost nonlar
Kepakli non | 250 9 3 46 | 30 60 | хлеб с отрубями, bran bread, whole grain bread, цельнозерновой хлеб, bran non
Qora non (javdar) | 210 6.5 1.2 43 | 30 100 | чёрный хлеб, ржаной хлеб, rye bread, black bread, borodinskiy, бородинский
Lavash (yupqa non) | 275 9 1.2 56 | 90 90 | лаваш, lavash non, lavash bread, yupqa lavash, armenian lavash
Pita | 275 9 1.2 56 | 60 60 | пита, pita bread, pita non
Tortilya | 300 8 7 51 | 40 40 | тортилья, tortilla, wrap, tortilla non
Bublik | 340 10 1.5 68 | 20 40 | бублик, баранка, bagel, baranka, bubliklar
Sushka | 330 11 1.3 70 | 8 24 | сушки, bread rings, sushki, dry bread rings
Pryanik | 350 4.5 4.5 77 | 40 40 | пряник, gingerbread, pryanik
Vafli | 500 5 25 65 | 15 60 | вафли, wafers, vafli, wafer
Pechenye (ovsyanoe) | 437 6.5 14 71 | 15 45 | овсяное печенье, oatmeal cookie, oat cookie
Pancake (amerikancha) | 227 6 10 28 | 40 120 | american pancakes, панкейки, pankeyk, pancakes, pankeyki
Muesli | 360 10 7 64 | 0 50 | мюсли, musli, müsli
Granola | 450 10 18 60 | 0 50 | гранола, granola
Kornfleks | 360 7 1 82 | 0 40 | cornflakes, кукурузные хлопья, corn flakes, hlopya, sereal
Un (bug'doy uni) | 334 11 1.2 70 | 0 30 | мука, flour, un, bug'doy uni, wheat flour
Makka uni | 331 7 2.7 71 | 0 30 | кукурузная мука, corn flour, cornmeal
"""
