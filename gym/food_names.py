"""Display names of the built-in foods in Russian and English (the Uzbek name is the one in gym/food_data1.py / food_data2.py).

Line format:  Uzbek name (exactly as in the data files) | Russian | English
The calorie page shows these in search results, the diary and the free-text preview according to the site language; a food without a line
falls back to its Uzbek name. The names of the member's own foods are never translated. Search also accepts these names.
gym/tests_calories.py checks that every built-in food has both names, so a row appended to the data files needs a line here too.
"""

RAW = """
Osh (palov) | Плов (ош) | Plov (pilaf)
Lag'mon | Лагман | Lagman
Manti | Манты | Manti (steamed dumplings)
Somsa (go'shtli) | Самса (с мясом) | Samsa (meat)
Shashlik (mol go'shti) | Шашлык (из говядины) | Shashlik (beef kebab)
Shashlik (qo'y go'shti) | Шашлык (из баранины) | Shashlik (lamb kebab)
Non (tandir) | Лепёшка (тандырная) | Flatbread (tandoor)
Oq non | Белый хлеб | White bread
Guruch (pishirilgan) | Рис (варёный) | Rice (boiled)
Grechka (pishirilgan) | Гречка (варёная) | Buckwheat (cooked)
Suli bo'tqasi (suvda) | Овсяная каша (на воде) | Oatmeal (with water)
Makaron (pishirilgan) | Макароны (варёные) | Pasta (cooked)
Kartoshka (qaynatilgan) | Картофель (варёный) | Potato (boiled)
Kartoshka fri | Картофель фри | French fries
Tuxum (qaynatilgan) | Яйцо (варёное) | Egg (boiled)
Omlet | Омлет | Omelette
Tovuq ko'kragi (pishirilgan) | Куриная грудка (варёная) | Chicken breast (cooked)
Tovuq go'shti (qovurilgan) | Курица (жареная) | Chicken (fried)
Mol go'shti (qaynatilgan) | Говядина (варёная) | Beef (boiled)
Qo'y go'shti (qaynatilgan) | Баранина (варёная) | Lamb (boiled)
Baliq (qaynatilgan) | Рыба (варёная) | Fish (boiled)
Tuna (konserva) | Тунец (консервы) | Tuna (canned)
Kolbasa (qaynatilgan) | Колбаса (варёная) | Sausage (boiled)
Sut (2.5%) | Молоко (2.5%) | Milk (2.5%)
Kefir (2.5%) | Кефир (2.5%) | Kefir (2.5%)
Qatiq | Катык (кислое молоко) | Yogurt (qatiq)
Tvorog (5%) | Творог (5%) | Cottage cheese (5%)
Tvorog (past yog'li) | Творог (обезжиренный) | Cottage cheese (low fat)
Pishloq | Сыр | Cheese
Smetana (20%) | Сметана (20%) | Sour cream (20%)
Sariyog' | Сливочное масло | Butter
O'simlik moyi | Растительное масло | Vegetable oil
Banan | Банан | Banana
Olma | Яблоко | Apple
Uzum | Виноград | Grapes
Behi | Айва | Quince
Anor | Гранат | Pomegranate
Apelsin | Апельсин | Orange
Qovun | Дыня | Melon
Tarvuz | Арбуз | Watermelon
O'rik (quritilgan) | Курага (сушёная) | Dried apricots
Mayiz | Изюм | Raisins
Yong'oq (grek) | Грецкий орех | Walnut
Bodom | Миндаль | Almond
Pista | Фисташки | Pistachios
Pomidor | Помидор | Tomato
Bodring | Огурец | Cucumber
Sabzi | Морковь | Carrot
Piyoz | Лук репчатый | Onion
Karam | Капуста | Cabbage
Shirchoy (sho'rva) | Ширчой (суп) | Shirchoy (milk tea soup)
Mastava | Мастава | Mastava
Sho'rva | Шурпа | Shurpa (meat soup)
Dimlama | Димлама | Dimlama (stewed meat and vegetables)
Chuchvara | Пельмени (чучвара) | Chuchvara (small dumplings)
Qozon kabob | Казан-кебаб | Kazan kebab
Pitsa | Пицца | Pizza
Burger | Бургер | Burger
Shokolad (sutli) | Шоколад (молочный) | Chocolate (milk)
Pechenye | Печенье | Cookies
Qand | Сахар | Sugar
Asal | Мёд | Honey
Choy (shakarsiz) | Чай (без сахара) | Tea (no sugar)
Choy (2 qand bilan) | Чай (с 2 кусочками сахара) | Tea (with 2 sugar cubes)
Kola | Кола | Cola
Apelsin sharbati | Апельсиновый сок | Orange juice
Protein kukuni (whey) | Протеин (сывороточный) | Protein powder (whey)
Protein batonchik | Протеиновый батончик | Protein bar
Toy oshi | Свадебный плов | Wedding plov
Toshkent oshi | Ташкентский плов | Tashkent plov
Samarqand oshi | Самаркандский плов | Samarkand plov
Osh (qo'y go'shtli) | Плов (с бараниной) | Plov (with lamb)
Osh (mol go'shtli) | Плов (с говядиной) | Plov (with beef)
Osh (tovuqli) | Плов (с курицей) | Plov (with chicken)
Dietetik osh | Диетический плов | Diet plov
Devzira oshi | Плов из девзиры | Devzira plov
Mosh guruch | Машкичири (рис с машем) | Mung bean rice (mashkichiri)
Moshxo'rda | Машхурда (суп с машем) | Mung bean soup (moshkhurda)
Shavla | Шавла | Shavla (thick rice dish)
Bo'tqa (guruchli, sutli) | Каша (рисовая, молочная) | Porridge (rice, milk)
Sumalak | Сумаляк | Sumalak (wheat sprout pudding)
Mastava (go'shtli) | Мастава (с мясом) | Mastava (with meat)
Sho'rva (tovuqli) | Суп (куриный) | Soup (chicken)
Sho'rva (qo'y go'shtli) | Шурпа (из баранины) | Shurpa (lamb)
Sho'rva (baliq) | Уха (рыбный суп) | Fish soup
No'xat sho'rva | Нутовый суп | Chickpea soup
Yasmiq sho'rva | Чечевичный суп | Lentil soup
Loviya sho'rva | Фасолевый суп | Bean soup
Lapsha sho'rva (tovuqli) | Куриный суп с лапшой | Chicken noodle soup
Sabzavot sho'rva | Овощной суп | Vegetable soup
Bulyon (go'sht) | Бульон (мясной) | Broth (meat)
Umoch | Умач (мучной суп) | Umoch (flour soup)
Atala | Атала | Atala (thin flour soup)
Kuk chuchvara | Зелёные пельмени | Herb dumplings
Chuchvara (sho'rvada) | Пельмени в бульоне | Dumplings in broth
Chuchvara (qovurilgan) | Пельмени (жареные) | Dumplings (fried)
Chalop | Чалоп (холодный кефирный суп) | Chalop (cold yogurt soup)
Okroshka (kefirda) | Окрошка (на кефире) | Okroshka (with kefir)
Beshbarmoq | Бешбармак | Beshbarmak
Norin | Нарын | Naryn (cold noodles with meat)
Qovurma (go'sht) | Жареное мясо | Fried meat
Qovurdoq | Курдак (жаркое) | Kovurdak (meat and potato roast)
Jarkop | Жаркоп | Zharkop (meat and potato stew)
Do'lma | Долма (в виноградных листьях) | Dolma (stuffed grape leaves)
Karam dolma | Голубцы | Stuffed cabbage rolls
Baqlajon do'lma | Фаршированные баклажаны | Stuffed eggplant
Qalampir do'lma | Фаршированный перец | Stuffed pepper
Xonim | Ханум | Khanum (steamed meat roll)
Manti (qovoqli) | Манты (с тыквой) | Manti (pumpkin)
Manti (kartoshkali) | Манты (с картошкой) | Manti (potato)
Manti (tovuqli) | Манты (с курицей) | Manti (chicken)
Tuxum barak | Яичный барак | Egg barak (stuffed dumplings)
Lyulya kabob | Люля-кебаб | Lula kebab
Tandir kabob | Тандыр-кебаб | Tandoor kebab
Jigar kabob | Шашлык из печени | Liver kebab
Shashlik (tovuq go'shti) | Шашлык (из курицы) | Shashlik (chicken kebab)
Shashlik (dumba) | Шашлык (из курдюка) | Shashlik (fat tail kebab)
Dumba | Курдючный жир | Lamb tail fat
Qazi | Казы | Kazy (horse sausage)
Qarta | Карта (конская кишка) | Karta (horse intestine)
Tandir go'sht | Тандыр-гошт (мясо из тандыра) | Tandoor meat
Jiz-biz | Жиз-быз | Jiz-biz (fried offal)
Bo'g'irsoq | Баурсаки | Baursak
Somsa (tandir, qo'y go'shtli) | Самса (тандырная, с бараниной) | Samsa (tandoor, lamb)
Somsa (qatlama) | Самса (слоёная) | Samsa (puff pastry)
Somsa (qovoqli) | Самса (с тыквой) | Samsa (pumpkin)
Somsa (kartoshkali) | Самса (с картошкой) | Samsa (potato)
Somsa (tovuqli) | Самса (с курицей) | Samsa (chicken)
Somsa (jigarli) | Самса (с печенью) | Samsa (liver)
Somsa (pishloqli) | Самса (с сыром) | Samsa (cheese)
Somsa (ko'katli) | Самса (с зеленью) | Samsa (herbs)
Gumma | Гумма (пирог с мясом) | Gumma (meat pie)
Pirojki (go'shtli) | Пирожки (с мясом) | Pirozhki (meat)
Pirojki (kartoshkali) | Пирожки (с картошкой) | Pirozhki (potato)
Chebureki | Чебуреки | Chebureki
Belyash | Беляш | Belyash
Pirog (olmali) | Яблочный пирог | Apple pie
Qatlama | Катлама | Katlama (layered flatbread)
Achichuk | Аччик-чучук (салат) | Achichuk (tomato and onion salad)
Koreyscha sabzi | Морковь по-корейски | Korean carrot salad
Pomidor-bodring salat | Салат из помидоров и огурцов | Tomato and cucumber salad
Karam salat | Салат из капусты | Cabbage salad
Sabzi salat | Салат из моркови | Carrot salad
Kartoshka pyure | Картофельное пюре | Mashed potatoes
Qovurilgan kartoshka | Жареная картошка | Fried potatoes
Pechdagi kartoshka | Запечённый картофель | Baked potato
Draniki | Драники | Potato pancakes
Borsch | Борщ | Borscht
Shchi | Щи | Shchi (cabbage soup)
Solyanka | Солянка | Solyanka
Rassolnik | Рассольник | Rassolnik (pickle soup)
Kharcho | Харчо | Kharcho
Pelmeni (do'kon) | Пельмени (магазинные) | Dumplings (store-bought)
Vareniki (kartoshkali) | Вареники (с картошкой) | Vareniki (potato)
Vareniki (tvorogli) | Вареники (с творогом) | Vareniki (cottage cheese)
Blin | Блины | Pancakes (blini)
Oladyi | Оладьи | Fritters
Syrniki | Сырники | Syrniki (cottage cheese pancakes)
Blinchik (tvorogli) | Блинчики (с творогом) | Crepes (cottage cheese)
Blinchik (go'shtli) | Блинчики (с мясом) | Crepes (meat)
Kotlet (mol go'shtli) | Котлета (говяжья) | Cutlet (beef)
Kotlet (tovuq) | Котлета (куриная) | Cutlet (chicken)
Beef stroganov | Бефстроганов | Beef stroganoff
Gulyash | Гуляш | Goulash
Yaichnitsa (qovurilgan tuxum) | Яичница | Fried eggs
Tuxum (xom) | Яйцо (сырое) | Egg (raw)
Tuxum oqi | Яичный белок | Egg white
Tuxum sarig'i | Яичный желток | Egg yolk
Bedana tuxumi | Перепелиные яйца | Quail eggs
Olivye | Салат оливье | Olivier salad
Vinegret | Винегрет | Vinaigrette (beet salad)
Seld shuba ostida | Селёдка под шубой | Herring under a fur coat
Mimoza salat | Салат мимоза | Mimosa salad
Krab salat | Крабовый салат | Crab salad
Sezar salat | Салат цезарь | Caesar salad
Yunon salat | Греческий салат | Greek salad
Ko'katli salat | Зелёный салат | Green salad
Hot-dog | Хот-дог | Hot dog
Sendvich (kolbasa, pishloq) | Сэндвич (колбаса, сыр) | Sandwich (sausage, cheese)
Buterbrod (kolbasa) | Бутерброд (с колбасой) | Sandwich (with sausage)
Buterbrod (pishloq) | Бутерброд (с сыром) | Sandwich (with cheese)
Buterbrod (sariyog') | Бутерброд (с маслом) | Bread and butter
Tost (sendvich) | Тост (сэндвич) | Toast (grilled sandwich)
Cheeseburger | Чизбургер | Cheeseburger
Big burger | Большой бургер | Big burger
Chicken burger | Чикенбургер | Chicken burger
Pizza (Margarita) | Пицца (Маргарита) | Pizza (Margherita)
Pizza (pepperoni) | Пицца (пепперони) | Pizza (pepperoni)
Pizza (4 pishloq) | Пицца (4 сыра) | Pizza (4 cheese)
Pizza (tovuqli) | Пицца (с курицей) | Pizza (chicken)
Shawarma (tovuq) | Шаурма (с курицей) | Shawarma (chicken)
Shawarma (mol/qo'y) | Шаурма (с говядиной или бараниной) | Shawarma (beef or lamb)
Lavash rulet (go'shtli) | Лаваш-ролл (с мясом) | Lavash roll (meat)
Naggets | Наггетсы | Chicken nuggets
Tovuq qanotchalari (qovurilgan) | Куриные крылышки (жареные) | Chicken wings (fried)
Tovuq stripslari | Куриные стрипсы | Chicken strips
Onion rings | Луковые кольца | Onion rings
Taco | Тако | Taco
Burrito | Буррито | Burrito
Panini | Панини | Panini
Sendvich (tovuqli, kichik) | Сэндвич (с курицей, маленький) | Sandwich (chicken, small)
Donat | Пончик | Donut
Kruassan | Круассан | Croissant
Kruassan (shokoladli) | Круассан (шоколадный) | Croissant (chocolate)
Sosiska | Сосиска | Frankfurter
Sosiska (tovuq) | Сосиска (куриная) | Chicken sausage
Mozzarella tayoqchalari | Сырные палочки (моцарелла) | Mozzarella sticks
Falafel | Фалафель | Falafel
Xummus | Хумус | Hummus
Sushi (rolli) | Суши (роллы) | Sushi (rolls)
Roll Filadelfiya | Ролл Филадельфия | Philadelphia roll
Chips (kartoshka) | Чипсы (картофельные) | Potato chips
Popkorn | Попкорн | Popcorn
Suxarik | Сухарики | Croutons
Kreker | Крекер | Crackers
Lapsha (tez tayyorlanadigan, xom) | Лапша быстрого приготовления (сухая) | Instant noodles (dry)
Lapsha (tez tayyor, tayyor holda) | Лапша быстрого приготовления (готовая) | Instant noodles (prepared)
Pasta karbonara | Паста карбонара | Pasta carbonara
Pasta bolonez | Паста болоньезе | Pasta bolognese
Lazanya | Лазанья | Lasagna
Rizotto | Ризотто | Risotto
Makaron pishloqli | Макароны с сыром | Mac and cheese
Flatbread pizza (lahmacun) | Лахмаджун | Lahmacun (Turkish flatbread pizza)
Guruch (xom) | Рис (сырой) | Rice (raw)
Guruch (jigarrang, pishirilgan) | Бурый рис (варёный) | Brown rice (cooked)
Grechka (xom) | Гречка (сухая) | Buckwheat (raw)
Suli yormasi (xom) | Овсяные хлопья (сухие) | Rolled oats (dry)
Suli bo'tqasi (sutda) | Овсяная каша (на молоке) | Oatmeal (with milk)
Arpa bo'tqasi | Перловая каша | Barley porridge
Tariq bo'tqasi | Пшённая каша | Millet porridge
Manniy bo'tqa | Манная каша | Semolina porridge
Guruch bo'tqasi (sutli) | Рисовая каша (на молоке) | Rice porridge (with milk)
Makka bo'tqasi | Кукурузная каша | Corn porridge (polenta)
Kuskus (pishirilgan) | Кускус (варёный) | Couscous (cooked)
Bulgur (pishirilgan) | Булгур (варёный) | Bulgur (cooked)
Kinoa (pishirilgan) | Киноа (варёная) | Quinoa (cooked)
Mosh (pishirilgan) | Маш (варёный) | Mung beans (cooked)
Mosh (xom) | Маш (сухой) | Mung beans (dry)
No'xat (pishirilgan) | Нут (варёный) | Chickpeas (cooked)
No'xat (xom) | Нут (сухой) | Chickpeas (dry)
Loviya (pishirilgan) | Фасоль (варёная) | Beans (cooked)
Loviya (xom) | Фасоль (сухая) | Beans (dry)
Yasmiq (pishirilgan) | Чечевица (варёная) | Lentils (cooked)
Yasmiq (xom) | Чечевица (сухая) | Lentils (dry)
Yashil no'xat (konserva) | Зелёный горошек (консервы) | Green peas (canned)
Makkajo'xori (qaynatilgan) | Кукуруза (варёная) | Corn (boiled)
Makkajo'xori (konserva) | Кукуруза (консервированная) | Sweet corn (canned)
Tofu | Тофу | Tofu
Soya go'shti (xom) | Соевое мясо (сухое) | Soy meat (dry)
Makaron (xom) | Макароны (сухие) | Pasta (dry)
Lapsha (pishirilgan) | Лапша (варёная) | Noodles (cooked)
Guruch lapshasi | Рисовая лапша | Rice noodles
Udon | Удон | Udon noodles
Nyoki | Ньокки | Gnocchi
Non (butun, tandir) | Лепёшка (целая, тандырная) | Flatbread (whole, tandoor)
Obi non | Оби-нон | Obi non (Uzbek bread)
Patir | Патыр | Patir (rich flatbread)
Lochira | Лочира | Lochira (Uzbek flatbread)
Shirmoy non | Ширмон | Shirmon (sweet milk bread)
Kulcha | Кулча | Kulcha
Zog'ora non | Зогора-нон | Zogora (cornmeal flatbread)
Bulka (shirin) | Булочка (сладкая) | Sweet bun
Baget | Багет | Baguette
Tost non | Тостовый хлеб | Sliced toast bread
Kepakli non | Хлеб с отрубями | Bran bread
Qora non (javdar) | Чёрный хлеб (ржаной) | Rye bread
Lavash (yupqa non) | Лаваш (тонкий) | Lavash (thin bread)
Pita | Пита | Pita
Tortilya | Тортилья | Tortilla
Bublik | Бублик | Bagel
Sushka | Сушки | Bread rings
Pryanik | Пряник | Gingerbread
Vafli | Вафли | Wafers
Pechenye (ovsyanoe) | Овсяное печенье | Oatmeal cookies
Pancake (amerikancha) | Панкейки (американские) | American pancakes
Muesli | Мюсли | Muesli
Granola | Гранола | Granola
Kornfleks | Кукурузные хлопья | Cornflakes
Un (bug'doy uni) | Мука (пшеничная) | Flour (wheat)
Makka uni | Кукурузная мука | Corn flour
Tovuq ko'kragi (xom) | Куриная грудка (сырая) | Chicken breast (raw)
Tovuq sonlari (pishirilgan) | Куриные бёдра (варёные) | Chicken thighs (cooked)
Tovuq oyoqchasi | Куриная голень | Chicken drumstick
Tovuq qanoti (xom) | Куриные крылья (сырые) | Chicken wings (raw)
Tovuq jigari | Куриная печень | Chicken liver
Tovuq yuragi | Куриные сердечки | Chicken hearts
Tovuq oshqozoni | Куриные желудки | Chicken gizzards
Tandir tovuq | Курица из тандыра (гриль) | Roast chicken (tandoor)
Kurka go'shti (ko'krak) | Индейка (грудка) | Turkey (breast)
Kurka go'shti | Индейка | Turkey
O'rdak go'shti | Утка | Duck
G'oz go'shti | Гусь | Goose
Quyon go'shti | Кролик | Rabbit
Mol go'shti (xom) | Говядина (сырая) | Beef (raw)
Mol qiymasi | Говяжий фарш | Ground beef
Mol bifshteks (qovurilgan) | Бифштекс (жареный) | Beef steak (fried)
Mol filesi | Говяжья вырезка | Beef tenderloin
Mol jigari (qovurilgan) | Говяжья печень (жареная) | Beef liver (fried)
Mol tili | Говяжий язык | Beef tongue
Mol yuragi | Говяжье сердце | Beef heart
Qo'y go'shti (xom) | Баранина (сырая) | Lamb (raw)
Qo'y qovurg'asi | Бараньи рёбрышки | Lamb ribs
Qo'y qiymasi | Бараний фарш | Ground lamb
Qo'y jigari | Баранья печень | Lamb liver
Cho'chqa go'shti | Свинина | Pork
Cho'chqa qiymasi | Свиной фарш | Ground pork
Ot go'shti | Конина | Horse meat
Jambon | Ветчина | Ham
Bekon | Бекон | Bacon
Salyami | Салями | Salami
Kolbasa (dudlangan) | Колбаса (копчёная) | Sausage (smoked)
Kolbasa (doktorskaya) | Колбаса (докторская) | Sausage (doctor's)
Pashtet | Паштет | Pate
Tushonka | Тушёнка | Canned stewed meat
Go'sht (dudlangan, quruq) | Мясо (вяленое) | Meat (jerky)
Losos (pishirilgan) | Лосось (запечённый) | Salmon (baked)
Losos (xom) | Лосось (сырой) | Salmon (raw)
Losos (tuzlangan) | Лосось (слабосолёный) | Salmon (salted)
Forel | Форель | Trout
Skumbriya | Скумбрия | Mackerel
Seld (tuzlangan) | Сельдь (солёная) | Herring (salted)
Treska | Треска | Cod
Sazan | Сазан (карп) | Carp
Sudak | Судак | Pike perch
Tilapiya | Тилапия | Tilapia
Xek (baliq) | Хек | Hake
Baliq (qovurilgan) | Рыба (жареная) | Fish (fried)
Baliq (panirovka) | Рыба (в панировке) | Fish (breaded)
Qizil ikra | Красная икра | Red caviar
Qora ikra | Чёрная икра | Black caviar
Krab tayoqchalari | Крабовые палочки | Crab sticks
Krevetka | Креветки | Shrimp
Midiya | Мидии | Mussels
Kalmar | Кальмар | Squid
Sprot (konserva) | Шпроты (консервы) | Sprats (canned)
Sardina (konserva) | Сардины (консервы) | Sardines (canned)
Baliq konservasi (tomatda) | Рыбные консервы (в томате) | Canned fish (in tomato sauce)
Sut (3.2%) | Молоко (3.2%) | Milk (3.2%)
Sut (1.5%) | Молоко (1.5%) | Milk (1.5%)
Sut (yog'siz) | Молоко (обезжиренное) | Milk (skim)
Echki suti | Козье молоко | Goat milk
Quritilgan sut | Сухое молоко | Milk powder
Quyultirilgan sut | Сгущённое молоко | Condensed milk
Qaymoq (10%) | Сливки (10%) | Cream (10%)
Qaymoq (20%) | Сливки (20%) | Cream (20%)
Qaymoq (33%) | Сливки (33%) | Cream (33%)
Smetana (10%) | Сметана (10%) | Sour cream (10%)
Smetana (15%) | Сметана (15%) | Sour cream (15%)
Kefir (1%) | Кефир (1%) | Kefir (1%)
Kefir (yog'siz) | Кефир (обезжиренный) | Kefir (fat free)
Ryajenka | Ряженка | Ryazhenka (baked milk)
Ayron | Айран | Ayran
Qatiq (yog'siz) | Катык (обезжиренный) | Yogurt (qatiq, low fat)
Qatiq (qaymoqli) | Катык (жирный) | Yogurt (qatiq, full fat)
Suzma | Сузьма (чакка) | Suzma (strained yogurt)
Qurt | Курт | Qurt (dried cheese balls)
Prostokvasha | Простокваша | Soured milk
Yogurt (tabiiy) | Йогурт (натуральный) | Yogurt (plain)
Yogurt (mevali) | Йогурт (фруктовый) | Yogurt (fruit)
Yunon yogurti | Греческий йогурт | Greek yogurt
Yogurt (yog'siz) | Йогурт (обезжиренный) | Yogurt (fat free)
Tvorog (9%) | Творог (9%) | Cottage cheese (9%)
Tvorog (yog'siz) | Творог (обезжиренный 0%) | Cottage cheese (fat free)
Sirok (glazurlangan) | Глазированный сырок | Glazed curd snack
Pishloq (rossiya) | Сыр (российский) | Cheese (Russian)
Pishloq (gollandiya) | Сыр (голландский) | Cheese (Dutch)
Pishloq (mozzarella) | Сыр (моцарелла) | Cheese (mozzarella)
Pishloq (brinza) | Сыр (брынза) | Cheese (feta)
Pishloq (suluguni) | Сыр (сулугуни) | Cheese (suluguni)
Pishloq (eritilgan) | Сыр (плавленый) | Cheese (processed)
Pishloq (parmezan) | Сыр (пармезан) | Cheese (parmesan)
Pishloq (cheddar) | Сыр (чеддер) | Cheese (cheddar)
Pishloq (kamamber) | Сыр (камамбер) | Cheese (camembert)
Pishloq (qaymoqli) | Сыр (сливочный) | Cheese (cream cheese)
Mascarpone | Маскарпоне | Mascarpone
Rikotta | Рикотта | Ricotta
Muzqaymoq (plombir) | Мороженое (пломбир) | Ice cream (plombir)
Muzqaymoq (sutli) | Мороженое (молочное) | Ice cream (milk)
Muzqaymoq (eskimo) | Мороженое (эскимо) | Ice cream (chocolate-coated bar)
Muzqaymoq (shokoladli) | Мороженое (шоколадное) | Ice cream (chocolate)
Sariyog' (margarin) | Маргарин | Margarine
Sariyog' (eritilgan, ghee) | Топлёное масло (гхи) | Ghee (clarified butter)
Qaymoq (qatlamli, kaymak) | Каймак | Kaymak (clotted cream)
Nok | Груша | Pear
Shaftoli | Персик | Peach
Nektarin | Нектарин | Nectarine
O'rik | Абрикос | Apricot
Olxo'ri | Слива | Plum
Gilos | Черешня | Sweet cherry
Olcha | Вишня | Sour cherry
Qulupnay | Клубника | Strawberry
Malina | Малина | Raspberry
Maymunjon | Ежевика | Blackberry
Smorodina (qora) | Смородина (чёрная) | Blackcurrant
Ko'k meva (chernika) | Черника | Blueberry
Klyukva | Клюква | Cranberry
Mandarin | Мандарин | Tangerine
Limon | Лимон | Lemon
Greypfrut | Грейпфрут | Grapefruit
Laym | Лайм | Lime
Kivi | Киви | Kiwi
Ananas | Ананас | Pineapple
Mango | Манго | Mango
Papayya | Папайя | Papaya
Avokado | Авокадо | Avocado
Xurmo | Хурма | Persimmon
Anjir (yangi) | Инжир (свежий) | Fig (fresh)
Anjir (quritilgan) | Инжир (сушёный) | Fig (dried)
Xurma (quritilgan) | Финики | Dates
Turshak | Чернослив | Prunes
Olma (quritilgan) | Яблоки (сушёные) | Apples (dried)
Nok (quritilgan) | Груши (сушёные) | Pears (dried)
Kokos (yangi) | Кокос (свежий) | Coconut (fresh)
Kokos qirindisi | Кокосовая стружка | Desiccated coconut
Tut | Шелковица | Mulberry
Tut (quritilgan) | Шелковица (сушёная) | Mulberry (dried)
Behi (quritilgan) | Айва (сушёная) | Quince (dried)
Qovun (quritilgan) | Дыня (сушёная) | Melon (dried)
Murabbo (jem) | Варенье (джем) | Jam
Marmelad | Мармелад | Marmalade candy
Pastila | Пастила | Pastila (fruit pastille)
Meva salati | Фруктовый салат | Fruit salad
Kompot mevalari (konserva) | Консервированные фрукты | Canned fruit
Kartoshka (xom) | Картофель (сырой) | Potato (raw)
Batat | Батат | Sweet potato
Qovoq | Тыква | Pumpkin
Baqlajon | Баклажан | Eggplant
Bolgar qalampiri | Болгарский перец | Bell pepper
Achchiq qalampir | Острый перец | Chili pepper
Kabachok | Кабачок | Zucchini
Turp | Редис | Radish
Sholg'om | Репа | Turnip
Sarimsoq | Чеснок | Garlic
Yashil piyoz | Зелёный лук | Green onion
Ukrop | Укроп | Dill
Petrushka | Петрушка | Parsley
Kashnich | Кинза | Cilantro
Rayhon | Базилик | Basil
Salat bargi | Салат (листовой) | Lettuce
Ismaloq | Шпинат | Spinach
Brokkoli | Брокколи | Broccoli
Gulkaram | Цветная капуста | Cauliflower
Brussel karami | Брюссельская капуста | Brussels sprouts
Qizilcha | Свёкла | Beetroot
Qizilcha (qaynatilgan) | Свёкла (варёная) | Beetroot (boiled)
Sabzi (qaynatilgan) | Морковь (варёная) | Carrot (boiled)
Shampinon | Шампиньоны | Mushrooms
Qo'ziqorin (qovurilgan) | Грибы (жареные) | Mushrooms (fried)
Pomidor pastasi | Томатная паста | Tomato paste
Zaytun | Оливки | Olives
Karam (tuzlangan) | Квашеная капуста | Sauerkraut
Bodring (tuzlangan) | Солёные огурцы | Pickled cucumbers
Kimchi | Кимчи | Kimchi
Selderey | Сельдерей | Celery
Qushqo'nmas | Спаржа | Asparagus
Yashil loviya | Стручковая фасоль | Green beans
Yashil no'xat (yangi) | Зелёный горошек (свежий) | Green peas (fresh)
Xren | Хрен | Horseradish
Avokado salat | Салат с авокадо | Avocado salad
Sabzavotli salat (moyli) | Овощной салат (с маслом) | Vegetable salad (with oil)
Sabzavot rag'u | Овощное рагу | Vegetable stew
Baqlajon ikrasi | Баклажанная икра | Eggplant caviar
Funduq | Фундук | Hazelnuts
Kaju | Кешью | Cashews
Yer yong'oq | Арахис | Peanuts
Yer yong'oq pastasi | Арахисовая паста | Peanut butter
Pekan | Пекан | Pecans
Makadamiya | Макадамия | Macadamia nuts
Brazil yong'og'i | Бразильский орех | Brazil nuts
Kungaboqar urug'i | Семечки подсолнечника | Sunflower seeds
Qovoq urug'i | Тыквенные семечки | Pumpkin seeds
Kunjut | Кунжут | Sesame seeds
Zig'ir urug'i | Семена льна | Flax seeds
Chia urug'i | Семена чиа | Chia seeds
Aralash yong'oqlar | Ореховое ассорти | Mixed nuts
Qovurilgan no'xat | Жареный нут | Roasted chickpeas
Kashtan | Каштан | Chestnut
Shokolad pastasi (Nutella) | Шоколадная паста (Нутелла) | Chocolate spread (Nutella)
Tahin | Тахини | Tahini
Zaytun moyi | Оливковое масло | Olive oil
Paxta moyi | Хлопковое масло | Cottonseed oil
Kokos moyi | Кокосовое масло | Coconut oil
Kunjut moyi | Кунжутное масло | Sesame oil
Salo (cho'chqa yog'i) | Сало (свиной жир) | Lard (pork fat)
Mol yog'i | Говяжий жир | Beef fat
Mayonez (klassik) | Майонез (классический) | Mayonnaise (classic)
Mayonez (yengil) | Майонез (лёгкий) | Mayonnaise (light)
Ketchup | Кетчуп | Ketchup
Tomat sousi | Томатный соус | Tomato sauce
Soya sousi | Соевый соус | Soy sauce
Xantal (gorchitsa) | Горчица | Mustard
Pesto | Песто | Pesto
Sarimsoqli sous | Чесночный соус | Garlic sauce
Ranch sous | Соус ранч | Ranch sauce
BBQ sous | Соус барбекю | BBQ sauce
Chili sous (shirin) | Сладкий соус чили | Sweet chili sauce
Adjika | Аджика | Adjika
Tkemali | Ткемали | Tkemali sauce
Sirka | Уксус | Vinegar
Tuz | Соль | Salt
Zira | Зира (тмин) | Cumin
Zanjabil | Имбирь | Ginger
Dolchin | Корица | Cinnamon
Bechamel sousi | Соус бешамель | Bechamel sauce
Shokolad (qora, 70%) | Шоколад (тёмный, 70%) | Chocolate (dark, 70%)
Shokolad (oq) | Шоколад (белый) | Chocolate (white)
Shokolad (yong'oqli) | Шоколад (с орехами) | Chocolate (with nuts)
Shokolad batonchik (Snickers) | Шоколадный батончик (Сникерс) | Chocolate bar (Snickers)
Mars batonchik | Батончик Марс | Mars bar
Twix | Твикс | Twix
Bounty | Баунти | Bounty
Karamel konfet | Карамель (конфеты) | Caramel candy
Shokolad konfet | Шоколадные конфеты | Chocolate candies
Iris (konfet) | Ирис (конфета) | Toffee
Zefir | Зефир | Marshmallow
Chupa-chups | Чупа-чупс | Lollipop
Halva (kunjutli) | Халва (кунжутная) | Halva (sesame)
Halva (kungaboqarli) | Халва (подсолнечная) | Halva (sunflower)
Halvaytar | Халвайтар | Halvaitar
Chak-chak | Чак-чак | Chak-chak
Navvot | Навват (кристаллический сахар) | Nabat (rock sugar)
Parvarda | Парварда | Parvarda
Nishalda | Нишалда | Nishalda
Pashmak | Пашмак (сладкая вата) | Pashmak (cotton candy)
Tort (kremli) | Торт (кремовый) | Cake (cream)
Tort (Napoleon) | Торт (Наполеон) | Cake (Napoleon)
Medovik | Медовик | Honey cake
Eklyer | Эклер | Eclair
Keks | Кекс | Muffin
Brauni | Брауни | Brownie
Cheesecake | Чизкейк | Cheesecake
Tiramisu | Тирамису | Tiramisu
Baklava | Пахлава | Baklava
Puding | Пудинг | Pudding
Jele | Желе | Jelly
Qaymoqli bulochka | Булочка со сливками | Cream bun
Shakar sirop | Сахарный сироп | Sugar syrup
Kakao kukuni | Какао-порошок | Cocoa powder
Maple sirop | Кленовый сироп | Maple syrup
Gozinaki | Гозинаки | Gozinaki
Granola bar | Злаковый батончик | Granola bar
Guruch galeta | Рисовые хлебцы | Rice cakes
Xlebsy (dietik non) | Хлебцы (диетические) | Crispbread
Suv | Вода | Water
Gazli suv | Газированная вода | Sparkling water
Choy (limonli) | Чай (с лимоном) | Tea (with lemon)
Choy (sutli, shakarsiz) | Чай (с молоком, без сахара) | Tea (with milk, no sugar)
Choy (1 qand bilan) | Чай (с 1 кусочком сахара) | Tea (with 1 sugar cube)
Choy (asalli) | Чай (с мёдом) | Tea (with honey)
Choy (shirin, 3 qand bilan) | Чай (сладкий, с 3 кусочками сахара) | Tea (sweet, with 3 sugar cubes)
Masala choy | Масала-чай | Masala chai
Matcha latte | Матча латте | Matcha latte
Qahva (qora, shakarsiz) | Кофе (чёрный, без сахара) | Coffee (black, no sugar)
Qahva (shakar bilan) | Кофе (с сахаром) | Coffee (with sugar)
Qahva (sut bilan) | Кофе (с молоком) | Coffee (with milk)
Kapuchino | Капучино | Cappuccino
Latte | Латте | Latte
Espresso | Эспрессо | Espresso
Amerikano | Американо | Americano
Mokko | Мокко | Mocha
Qahva 3 in 1 | Кофе 3 в 1 | Coffee 3 in 1
Flat white | Флэт уайт | Flat white
Issiq shokolad | Горячий шоколад | Hot chocolate
Kakao (sutli) | Какао (с молоком) | Cocoa (with milk)
Olma sharbati | Яблочный сок | Apple juice
Uzum sharbati | Виноградный сок | Grape juice
Anor sharbati | Гранатовый сок | Pomegranate juice
Shaftoli sharbati | Персиковый сок | Peach juice
Pomidor sharbati | Томатный сок | Tomato juice
Sabzi sharbati | Морковный сок | Carrot juice
Ananas sharbati | Ананасовый сок | Pineapple juice
Multifrukt sharbat | Мультифруктовый сок | Multifruit juice
Limonad | Лимонад | Lemonade
Fanta | Фанта | Fanta
Sprite | Спрайт | Sprite
Kola (shakarsiz) | Кола (без сахара) | Cola (sugar free)
Gazli ichimlik | Газировка | Soft drink
Energetik ichimlik | Энергетик | Energy drink
Kompot | Компот | Compote
Uzvar | Узвар (компот из сухофруктов) | Dried fruit compote
Kisel | Кисель | Kissel
Kvas | Квас | Kvass
Mors | Морс | Berry fruit drink
Ice tea | Холодный чай | Iced tea
Sut kokteyli | Молочный коктейль | Milkshake
Yogurt ichimlik | Питьевой йогурт | Drinking yogurt
Smuzi | Смузи | Smoothie
Protein kokteyli (tayyor) | Протеиновый коктейль (готовый) | Protein shake (ready-made)
Pivo (och) | Пиво (светлое) | Beer (light)
Pivo (qorong'i) | Пиво (тёмное) | Beer (dark)
Pivo (alkogolsiz) | Пиво (безалкогольное) | Beer (non-alcoholic)
Vino (qizil) | Вино (красное) | Wine (red)
Vino (oq) | Вино (белое) | Wine (white)
Aroq | Водка | Vodka
Konyak | Коньяк | Cognac
Viski | Виски | Whiskey
Shampan | Шампанское | Champagne
Sidr | Сидр | Cider
Boza | Боза | Boza
Kokos suvi | Кокосовая вода | Coconut water
Soya suti | Соевое молоко | Soy milk
Bodom suti | Миндальное молоко | Almond milk
Suli suti | Овсяное молоко | Oat milk
Izotonik ichimlik | Изотонический напиток | Isotonic drink
Gainer | Гейнер | Mass gainer
Whey izolyat | Сывороточный изолят | Whey isolate
Kazein | Казеин | Casein
Protein bar (kam shakarli) | Протеиновый батончик (с малым содержанием сахара) | Protein bar (low sugar)
Protein pechenye | Протеиновое печенье | Protein cookie
Energetik gel | Энергетический гель | Energy gel
Kreatin | Креатин | Creatine
BCAA | BCAA (аминокислоты) | BCAA (amino acids)
"""

# {Uzbek name: (Russian, English)}
NAMES = {}
for _line in RAW.strip().splitlines():
    _uz, _ru, _en = (x.strip() for x in _line.split("|"))
    if _uz in NAMES:
        raise ValueError(f"duplicate food name: {_uz}")
    NAMES[_uz] = (_ru, _en)
