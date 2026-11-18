"""Built-in food table, part 3 (more Uzbek and Central Asian dishes, fast food chains, Asian / Caucasian / European dishes, sweets, snacks).
Same line format as gym/food_data1.py. Appended after part 2: never reorder. Every row needs a line in gym/food_names.py too
(its ru / en names are in gym/food_names3.py).
"""

RAW = """
# ---- Uzbek national dishes and breads
Qovurma lag'mon | 190 8 9 20 | 0 350 | qovurma lagmon, жареный лагман, fried laghman, fried lagman, gan lagmon
Tikka kabob | 215 24 13 1 | 70 160 | tikka kebab, тикка кебаб, тикка кабоб, chicken tikka
Gijduvon non | 285 8 4 54 | 400 150 | гиждуванская лепёшка, gijduvan non, gijduvon nonni, bukhara flatbread
Qiymali non | 300 10 14 34 | 200 200 | кийма нон, qiymali patir, meat stuffed flatbread, лепёшка с мясом
Yopgan non | 255 8 1.5 53 | 250 150 | yopma non, thin flatbread, тонкая лепёшка
Chuzma | 260 6 15 27 | 120 120 | чузма, chuzma non
Xasip | 330 13 28 3 | 0 100 | хасип, hasip, xasib, uzbek liver sausage, домашняя колбаса из рубца
Jizzax | 325 22 26 1 | 0 100 | жиз, jiz, jizz, qovurilgan go'sht jiz
Shirguruch | 120 3 3.5 20 | 0 250 | ширгуруч, shirguruch sut, milk rice porridge, молочный рис, рисовая каша на молоке
Mash sho'rva | 90 6 2 12 | 0 350 | mashxo'rda, moshxorda, мош хорда, машевый суп, mung bean soup, mash shorva
Mashkichiri | 140 6 4 20 | 0 300 | машкичири, moshkichiri, moshkichiri osh, mung bean rice
Mastava (guruchli) | 80 4 3 9 | 0 300 | guruchli mastava, rice soup mastava, мастава с рисом
Sho'rva (mol go'shti) | 55 5 3 2 | 0 350 | mol sho'rva, mol shorva, говяжий суп, beef broth soup
Qovurma xasip | 280 12 22 6 | 0 150 | hasip qovurma, жареный хасип
Do'ppi somsa | 300 7 18 28 | 110 110 | tandir somsa katta, uchburchak somsa, треугольная самса, triangle samsa
Qovoqli somsa | 235 4 11 31 | 120 120 | тыквенная самса, pumpkin samsa, qovoq somsa, qovoqli samsa
Kartoshkali somsa | 260 5 12 33 | 120 120 | картофельная самса, potato samsa, kartoshka somsa
Ko'katli somsa | 230 6 11 28 | 110 110 | самса с зеленью, greens samsa, ko'kli somsa, herb samsa
Tovuqli somsa | 270 10 14 26 | 120 120 | самса с курицей, chicken samsa, tovuq somsa
Pishloqli somsa | 310 11 19 25 | 110 110 | самса с сыром, cheese samsa, pishloq somsa
Pirojki (tuxum piyozli) | 235 7 10 29 | 90 90 | пирожки с яйцом и луком, egg onion pie
Xonim (kartoshkali) | 150 3 4 25 | 0 250 | ханум с картошкой, potato hanum
Pelmeni (uy) | 245 11 12 24 | 15 220 | домашние пельмени, home pelmeni, uy pelmeni
Ugra osh | 95 3 3 14 | 0 350 | угра ош, ugra, ugra oshi, угра суп
Umoch oshi | 110 3 3 17 | 0 350 | умач, umach, umoch, umach oshi, umoch osh, umach soup
Qatiqli sho'rva | 60 3 2 7 | 0 300 | qatiqli shorva, кислая шурпа, sour milk soup, qatiq shurpa
Tovuq sho'rva | 40 4 2 1 | 0 350 | tovuq shorva, куриный суп, chicken soup, куриный бульон
Kesma | 125 4 2 22 | 0 300 | кесма, kesma lagman, homemade noodles soup, домашняя лапша
Norin (sovuq) | 220 13 12 16 | 0 250 | cold norin, холодный нарын, norin salqin
Bayram palovi | 225 8 11 24 | 0 280 | to'y oshi, toy oshi, to'y palovi, свадебный плов, wedding plov, nahor osh, nahorgi osh
Qovurilgan jigar | 180 22 8 3 | 0 150 | fried liver, жареная печень, qovurma jigar
Tuxumli qovurma | 170 10 13 3 | 0 200 | tuxum qovurma, qovurma tuxum, eggs with tomatoes, яичница с помидорами
Shirmoy | 290 8 8 46 | 110 110 | ширмай, shirmoy non, sweet milk bread, shirmon, ширмон
Qatlamali patir | 360 7 20 40 | 220 150 | patir qatlamali, flaky patir, слоёный патыр
Zuvalama | 195 8 8 22 | 0 200 | зувалама, zuvala, fried meat pastry, zuvalama non
Chala | 85 5 4 6 | 0 150 | чала, qatiq chala, chala sut
Halim | 190 9 7 22 | 0 250 | халим, haleem, halim go'sht, meat porridge, мясная каша халим
Sutli guruch bo'tqa | 120 3.5 3.5 19 | 0 250 | rice milk porridge, молочная рисовая каша, guruchli sutli bo'tqa
Pishmaniye | 520 7 28 58 | 0 50 | пишмание, pismaniye, turkish floss halva, pishmaniya
Xalvo | 520 12 30 52 | 0 40 | халва, halva, halvo, sunflower halva, tahini halva
Bekmes | 280 0.5 0 70 | 0 40 | бекмес, grape syrup, uzum shirasi, doshab, дошаб, shira, shirasi
Qiyom | 300 0.5 0 76 | 0 30 | киём, qand qiyomi, sugar syrup
Olxo'ri murabbo | 270 0.4 0.1 69 | 20 30 | олуповое варенье, plum jam, olxori murabbo
Gilos murabbo | 255 0.4 0.1 65 | 20 30 | вишнёвое варенье, cherry jam
Qulupnay murabbo | 260 0.5 0.1 66 | 20 30 | клубничное варенье, strawberry jam
Anjir murabbo | 275 0.8 0.2 69 | 20 30 | инжирное варенье, fig jam
Qimiz | 50 2 1.9 4.5 | 250 250 | кумыс, qymyz, kumis, kumys, fermented mare milk
Yashil choy | 1 0 0 0 | 200 200 | зелёный чай, green tea, yashil choy shakarsiz, ko'k choy
Shakarli choy | 25 0 0 6 | 200 200 | чёрный чай с сахаром, tea with sugar, qand bilan choy
Sutli choy | 40 1.5 1.8 4.5 | 250 250 | чай с молоком, milk tea, choy sut bilan
Limonli choy | 15 0 0 4 | 250 250 | чай с лимоном, lemon tea, choy limon bilan

# ---- fast food chains and street food
Whopper | 260 12 15 20 | 290 290 | воппер, whopper burger, burger king whopper, burger king
Big Mac | 255 12 13 24 | 215 215 | биг мак, bigmak, big mac burger, mcdonalds big mac, макдоналдс бургер
Double burger | 265 16 15 18 | 280 280 | двойной бургер, dabl burger, double beef burger
Mini burger | 250 12 10 26 | 100 100 | мини бургер, slider, hamburger mini
Chicken wings | 250 20 17 5 | 60 240 | куриные крылья, tovuq qanoti, wings, buffalo wings, kfc wings, qanotlar
KFC tovuq | 265 18 17 11 | 120 240 | kfc chicken, kfc fried chicken, кфс курица, fried chicken, kfc drumstick, kfc
Twister | 235 11 10 25 | 220 220 | твистер, kfc twister, chicken twister
Katta fri | 312 3.4 15 41 | 180 180 | большая картошка фри, large fries, big fries
Fransuz hot-dog | 280 9 16 25 | 160 160 | french hot dog, французский хот-дог, fransuz hotdog, sosiskali non
Corndog | 280 8 14 31 | 120 120 | корн-дог, korn dog, cornydog, korndog
Tovuqli lavash | 215 12 8 23 | 280 280 | лаваш с курицей, chicken lavash, lavash chicken roll
Pishloqli lavash | 245 10 12 25 | 250 250 | лаваш с сыром, cheese lavash, cheese lavash roll
Doner | 215 12 11 17 | 280 280 | донер, doner kebab, donar, донар, turkish doner, doner kabob, doner lavash
Donar (bulochkada) | 235 11 12 20 | 300 300 | donar non, donar bulochka, донер в булке, doner in bun
Pishloqli shaurma | 245 12 13 20 | 330 330 | shawarma cheese, шаурма с сыром, shaurma sirli
Katta shaurma | 215 11 10 20 | 400 400 | big shawarma, большая шаурма, shaurma 400
Club sandwich | 215 11 10 20 | 250 250 | клаб сэндвич, klab sendvich, klub sandwich, club sendvich, клубный сэндвич
Tovuqli sendvich | 220 12 8 24 | 180 180 | chicken sandwich, сэндвич с курицей, sandvich tovuq
Subway | 175 11 4 24 | 230 230 | сабвей, subway sandwich, subway tovuq, subway chicken
Pizza (Gavayi) | 235 11 8 29 | 110 110 | pitsa gavayi, гавайская пицца, hawaiian pizza, gavai pitsa
Pizza (go'shtli) | 275 13 13 26 | 110 110 | go'shtli pitsa, мясная пицца, meat pizza, pitsa goshtli, meat lovers pizza
Pizza (qo'ziqorinli) | 235 10 9 28 | 110 110 | qo'ziqorinli pitsa, грибная пицца, mushroom pizza, pitsa qoziqorin
Calzone | 260 11 11 29 | 250 250 | кальцоне, kalsone, folded pizza
Quesadilla | 260 12 14 22 | 200 200 | кесадилья, kesadilya
Nachos | 345 8 19 38 | 30 100 | начос, nachos chips, naco, nachos pishloq
Achchiq sous | 150 1 12 9 | 15 30 | острый соус, buffalo sauce, hot sauce, hot wings sous
Belgiya vaflisi | 290 7 11 40 | 75 75 | belgian waffle, бельгийская вафля, waffle, waffles, вафли бельгийские
Pankeyk | 230 6 8 33 | 80 160 | pancake, pancakes, панкейк, блинчики американские, american pancakes, pankek
Sinnabon | 370 5 14 56 | 130 130 | синнабон, cinnabon, cinnamon roll, tarchinli bulochka
Shokoladli kruassan | 400 7 21 45 | 80 80 | круассан с шоколадом, chocolate croissant, pain au chocolat, kruassan shokolad
Pishloqli kruassan | 380 10 22 36 | 80 80 | круассан с сыром, cheese croissant, kruassan pishloq
Lays chips | 540 6 35 50 | 25 50 | lays, лейс, чипсы, potato chips, crisps, pringles, принглс
Doritos | 495 7 26 60 | 30 50 | дорито, начос чипсы, corn chips, doritos nachos
Kinder | 560 8.7 35 54 | 13 25 | киндер, kinder chocolate, kinder bueno, киндер шоколад, kinder surprise, kinder delice
Oreo | 475 4.8 20 69 | 11 33 | орео, oreo pechenye, oreo cookie, oreo cookies
Nutella | 540 6.3 31 57 | 15 30 | нутелла, shokoladli pasta, nutella pasta, chocolate spread, паста шоколадная
Snickers | 490 9 24 60 | 50 50 | сникерс, snikers, snickers bar, snickers batonchik, марс, mars bar, mars, твикс, twix, баунти, bounty
Milka shokolad | 535 6.5 30 58 | 25 100 | милка, milka, milka chocolate, молочный шоколад, sut shokolad, milk chocolate
Shokoladli muzqaymoq | 230 4 12 27 | 65 100 | шоколадное мороженое, chocolate ice cream, eskimo, эскимо
Rojkali muzqaymoq | 235 3.8 11 29 | 80 80 | мороженое рожок, cone ice cream, rojok, ice cream cone, рожок
Sutli qahva | 55 1.5 1.5 8 | 200 200 | coffee with milk and sugar, кофе с молоком и сахаром, qahva sut va shakar bilan
Coca-Cola | 42 0 0 10.6 | 330 330 | cola, кола, coca cola, kola, pepsi, пепси, pepsi cola, coke, fanta, фанта, sprite, спрайт, gazli ichimlik, soda

# ---- Asian dishes
Pho | 70 5 2 8 | 0 500 | фо бо, pho bo, fo bo, vietnam suppi, vietnamese pho, фо
Pad thai | 175 8 7 21 | 0 300 | пад тай, pad tai, thai noodles, padtai
Ramen | 95 5 3.5 11 | 0 450 | рамен, ramyon, ramen sho'rva, лапша рамен
Doshirak | 440 9 17 62 | 70 70 | доширак, instant noodles, rolton, ролтон, лапша быстрого приготовления, big bon
Wok (tovuqli) | 155 12 5 15 | 0 300 | вок с курицей, chicken wok, tovuqli wok, wok tovuq
Tom yum | 45 4 2 3 | 0 350 | том ям, tom yam, tomyam, thai soup
Bibimbap | 130 6 3.5 18 | 0 400 | бибимбап, bibimbab, korean rice bowl, пибимпап
Tteokbokki | 175 4 3 33 | 0 250 | токпокки, tokpokki, ttokbokki, tteok bokki, korean rice cakes
Kuksi | 90 3 2 15 | 0 350 | куксу, kuksu, cold noodles korean, korean cold noodle
Xe salati | 110 12 5 4 | 0 150 | хе, he salat, khe, xe, korean raw fish salad, he baliq
Funchoza | 105 1.5 4 17 | 0 150 | фунчоза, funchose, glass noodles, noodle salad
Xitoy chuchvarasi | 215 9 8 27 | 25 150 | китайские пельмени, jiaozi, dim sum, gyoza, гёдза, дим сам, dimsam
Nigiri | 145 6 2.5 25 | 30 120 | нигири, nigiri losos, salmon nigiri, суши лосось, sushi losos
Roll Kaliforniya | 175 6 5.5 25 | 30 180 | калифорния, california roll, kaliforniya roll, california
Pishirilgan roll | 220 7 10 25 | 35 200 | запечённые роллы, baked roll, tempura roll, темпура ролл, hot roll
Miso sho'rva | 35 2.5 1.5 3 | 0 250 | мисо суп, miso soup, miso, мисо
Sashimi | 130 22 5 0 | 25 100 | сашими, sashimi losos, salmon sashimi, raw fish
Teriyaki tovuq | 160 16 5 11 | 0 250 | терияки, teriyaki chicken, chicken teriyaki, teriyaki
Qovurilgan guruch | 175 5 6 24 | 0 250 | жареный рис, fried rice, yangzhou fried rice, nasi goreng
Gyros | 225 11 11 20 | 300 300 | гирос, giros, gyro, pita gyros
Paella | 150 7 4 21 | 0 300 | паэлья, paelya, paella seafood, spanish rice, seafood paella
Fettuchini | 160 5 6 21 | 0 280 | fettuccine alfredo, феттучини, fetuchini, fettuccine, alfredo pasta
Karbonara | 190 7 10 18 | 0 300 | карбонара, carbonara, spagetti karbonara, makaron karbonara, spaghetti carbonara
Mol steyk | 250 26 16 0 | 0 200 | стейк, steak, mol steak, beef steak, biftek, стейк говяжий, ribeye, ribay
Losos steyk | 205 22 12 0 | 0 180 | лосось стейк, salmon steak, losos steyk, qizil baliq steyk
Tovuq kotlet | 225 15 14 10 | 80 160 | куриная котлета, chicken cutlet, kotleta tovuq
Teftel | 190 12 11 10 | 40 160 | тефтели, tefteli, meatballs, teftelli
Dudlangan mol go'shti | 305 25 22 1 | 0 100 | копчёная говядина, smoked beef, dudlangan go'sht
Dudlangan kolbasa | 410 18 38 1 | 20 50 | копчёная колбаса, smoked sausage, salami, салями, servelat, сервелат
Salo | 770 1.4 89 0 | 0 30 | сало, pork lard, shpik

# ---- Caucasian, Russian, European
Xinkali | 235 10 11 24 | 70 210 | хинкали, hinkali, khinkali, xinkali go'shtli, gruzin chuchvarasi, georgian dumplings
Xachapuri | 275 11 15 24 | 250 250 | хачапури, khachapuri, hachapuri, imeruli xachapuri, xacha puri, adjarian khachapuri
Lobio | 120 7 4 16 | 0 250 | лобио, lobio loviya, georgian beans, lobio fasol
Satsivi | 210 15 16 3 | 0 200 | сациви, satsivi tovuq, georgian chicken walnut sauce, sacivi
Chixirtma | 55 4 3 3 | 0 300 | чихиртма, chikhirtma, chikhirtma soup, georgian chicken soup
Okroshka | 50 2.5 2.5 4 | 0 300 | окрошка, okroshka kefir, okroshka sovuq, cold soup
Tvorogli blinchik | 190 8 8 22 | 60 120 | блинчики с творогом, pancake with cottage cheese, tvorogli blin
Go'shtli blinchik | 210 9 9 23 | 70 140 | блины с мясом, meat pancake, go'shtli blin
Napoleon tort | 410 5 25 42 | 0 100 | наполеон, napoleon, napoleon cake, napolyon, napoleon pirojnoe
Shokoladli tort | 395 5 21 48 | 0 120 | шоколадный торт, chocolate cake, tort shokolad, prague cake, прага торт
Mevali tort | 320 4 14 45 | 0 120 | фруктовый торт, fruit cake, tort mevali, berry cake, ягодный торт
Mannik | 255 6 9 38 | 0 100 | манник, mannik pirog, semolina cake, manniy pirog, mannik torti
Kremli pirojnoe | 400 4.5 28 33 | 0 90 | пирожное, pirojnoe, cream cake, пирожное с кремом
Qumli pechenye | 435 6 20 58 | 12 40 | песочное печенье, shortbread, kuki, cookie, cookies, печенье, pechenye, biskvit pechenye
Kremli vafli | 510 5 25 66 | 20 60 | вафли, wafers, vafli, вафли с кремом, vafli shokoladli
Sutli suli bo'tqasi | 90 3.4 3 13 | 0 250 | овсянка на молоке, oatmeal with milk, ovsyanka sut bilan, oat porridge milk
Yog'li tvorog | 225 16 18 2 | 0 100 | жирный творог, cottage cheese fat, 18% tvorog, творог 18%
Adigey pishlog'i | 245 18 19 1.5 | 0 80 | адыгейский сыр, adyghe cheese, adigey pishloq
Brinza | 260 17 21 0 | 0 80 | брынза, brinza pishloq, feta, feta cheese, фета, suluguni, сулугуни
Mozzarella | 245 20 17 2 | 0 60 | моцарелла, motsarella, mozzarella cheese, mozarella
Qattiq pishloq | 360 25 28 0 | 15 40 | твёрдый сыр, hard cheese, parmesan, пармезан, parmezan, gouda, гауда, cheddar, российский сыр, rus pishloq
Eritilgan pishloq | 285 15 22 4 | 20 50 | плавленый сыр, processed cheese, druzhba, дружба, kremli pishloq, philadelphia cheese
Smetana | 205 2.8 20 3.2 | 15 50 | сметана, sour cream, smetana 20, smetana yog'li
Mayonez | 630 0.7 67 3 | 15 15 | майонез, mayonnaise, mayonez sous, provansal, провансаль
Achchiq shokolad | 540 6 36 45 | 10 25 | горький шоколад, dark chocolate, qora shokolad, bitter chocolate
Xuruz | 90 3 1.5 18 | 150 150 | хуруз, boiled corn, corn on the cob, кукуруза варёная, makkajoxori, qaynatilgan makkajo'xori
Qutab | 215 7 9 27 | 110 110 | кутаб, qutab azeri, kutab, gutab, azeri qutab
"""
