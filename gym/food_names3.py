"""Russian and English display names of the foods in gym/food_data3.py. Line format: Uzbek name | Russian | English (merged into food_names.NAMES)."""

RAW = """
Qovurma lag'mon | Жареный лагман | Fried laghman
Tikka kabob | Тикка-кебаб | Chicken tikka kebab
Gijduvon non | Гиждуванская лепёшка | Gijduvan flatbread
Qiymali non | Лепёшка с мясом | Meat-stuffed flatbread
Yopgan non | Тонкая лепёшка (юпка) | Thin flatbread
Chuzma | Чузма | Chuzma (layered flatbread)
Xasip | Хасип | Hasip (liver sausage)
Jizzax | Жиз (жареное мясо) | Jiz (fried meat)
Shirguruch | Ширгуруч (молочный рис) | Shirguruch (milk rice)
Mash sho'rva | Машевый суп (мошхорда) | Mung bean soup (moshxo'rda)
Mashkichiri | Машкичири | Mashkichiri (mung bean rice)
Mastava (guruchli) | Мастава с рисом | Mastava with rice
Sho'rva (mol go'shti) | Суп из говядины | Beef soup
Qovurma xasip | Жареный хасип | Fried hasip
Do'ppi somsa | Самса-треугольник | Triangle samsa
Qovoqli somsa | Самса с тыквой | Pumpkin samsa
Kartoshkali somsa | Самса с картошкой | Potato samsa
Ko'katli somsa | Самса с зеленью | Herb samsa
Tovuqli somsa | Самса с курицей | Chicken samsa
Pishloqli somsa | Самса с сыром | Cheese samsa
Pirojki (tuxum piyozli) | Пирожки с яйцом и луком | Egg and onion pirozhki
Xonim (kartoshkali) | Ханум с картошкой | Hanum with potato
Pelmeni (uy) | Домашние пельмени | Homemade pelmeni
Ugra osh | Угра-ош | Ugra osh (noodle soup)
Umoch oshi | Умач | Umoch soup
Qatiqli sho'rva | Кислая шурпа (с катыком) | Yogurt soup
Tovuq sho'rva | Куриный суп | Chicken soup
Kesma | Кесма (суп с домашней лапшой) | Kesma (homemade noodle soup)
Norin (sovuq) | Холодный нарын | Cold norin
Bayram palovi | Праздничный плов (той-ош) | Festive plov (toy osh)
Qovurilgan jigar | Жареная печень | Fried liver
Tuxumli qovurma | Яичница с помидорами | Eggs with tomatoes
Shirmoy | Ширмой (сдобная лепёшка) | Shirmoy (sweet milk bread)
Qatlamali patir | Слоёный патыр | Layered patir
Zuvalama | Зувалама | Zuvalama
Chala | Чала | Chala
Halim | Халим | Halim (meat porridge)
Sutli guruch bo'tqa | Молочная рисовая каша | Milk rice porridge
Pishmaniye | Пишмание | Pismaniye (floss halva)
Xalvo | Халва | Halva
Bekmes | Бекмес (виноградный сироп) | Bekmes (grape syrup)
Qiyom | Киём (сахарный сироп) | Qiyom (sugar syrup)
Olxo'ri murabbo | Сливовое варенье | Plum jam
Gilos murabbo | Вишнёвое варенье | Cherry jam
Qulupnay murabbo | Клубничное варенье | Strawberry jam
Anjir murabbo | Инжирное варенье | Fig jam
Qimiz | Кумыс | Kumis (fermented mare milk)
Yashil choy | Зелёный чай | Green tea
Shakarli choy | Чай с сахаром | Tea with sugar
Sutli choy | Чай с молоком | Tea with milk
Limonli choy | Чай с лимоном | Tea with lemon
Whopper | Воппер | Whopper
Big Mac | Биг Мак | Big Mac
Double burger | Двойной бургер | Double burger
Mini burger | Мини-бургер | Mini burger
Chicken wings | Куриные крылышки | Chicken wings
KFC tovuq | Курица KFC | KFC fried chicken
Twister | Твистер | Twister wrap
Katta fri | Картофель фри (большой) | Large fries
Fransuz hot-dog | Французский хот-дог | French hot dog
Corndog | Корн-дог | Corn dog
Tovuqli lavash | Лаваш с курицей | Chicken lavash wrap
Pishloqli lavash | Лаваш с сыром | Cheese lavash wrap
Doner | Донер | Doner kebab
Donar (bulochkada) | Донер в булке | Doner in a bun
Pishloqli shaurma | Шаурма с сыром | Shawarma with cheese
Katta shaurma | Большая шаурма | Large shawarma
Club sandwich | Клаб-сэндвич | Club sandwich
Tovuqli sendvich | Сэндвич с курицей | Chicken sandwich
Subway | Сэндвич Subway | Subway sandwich
Pizza (Gavayi) | Пицца Гавайская | Hawaiian pizza
Pizza (go'shtli) | Пицца мясная | Meat pizza
Pizza (qo'ziqorinli) | Пицца с грибами | Mushroom pizza
Calzone | Кальцоне | Calzone
Quesadilla | Кесадилья | Quesadilla
Nachos | Начос | Nachos
Achchiq sous | Острый соус | Hot sauce
Belgiya vaflisi | Бельгийская вафля | Belgian waffle
Pankeyk | Панкейк | Pancake (American)
Sinnabon | Синнабон (булочка с корицей) | Cinnamon roll
Shokoladli kruassan | Круассан с шоколадом | Chocolate croissant
Pishloqli kruassan | Круассан с сыром | Cheese croissant
Lays chips | Чипсы (Lays) | Potato chips (Lays)
Doritos | Начос-чипсы (Doritos) | Corn chips (Doritos)
Kinder | Киндер (шоколад) | Kinder chocolate
Oreo | Печенье Орео | Oreo cookies
Nutella | Нутелла | Nutella
Snickers | Сникерс и батончики | Snickers and candy bars
Milka shokolad | Молочный шоколад | Milk chocolate
Shokoladli muzqaymoq | Шоколадное мороженое | Chocolate ice cream
Rojkali muzqaymoq | Мороженое в рожке | Ice cream cone
Sutli qahva | Кофе с молоком и сахаром | Coffee with milk and sugar
Coca-Cola | Кока-кола и газировка | Cola and soda
Pho | Фо бо | Pho
Pad thai | Пад тай | Pad thai
Ramen | Рамен | Ramen
Doshirak | Лапша быстрого приготовления | Instant noodles
Wok (tovuqli) | Вок с курицей | Chicken wok
Tom yum | Том ям | Tom yum
Bibimbap | Бибимбап | Bibimbap
Tteokbokki | Токпокки | Tteokbokki
Kuksi | Куксу (холодная лапша) | Kuksi (cold noodles)
Xe salati | Хе | Khe (Korean fish salad)
Funchoza | Фунчоза | Funchoza (glass noodles)
Xitoy chuchvarasi | Китайские пельмени | Chinese dumplings
Nigiri | Нигири | Nigiri
Roll Kaliforniya | Ролл Калифорния | California roll
Pishirilgan roll | Запечённый ролл | Baked roll
Miso sho'rva | Мисо-суп | Miso soup
Sashimi | Сашими | Sashimi
Teriyaki tovuq | Курица терияки | Chicken teriyaki
Qovurilgan guruch | Жареный рис | Fried rice
Gyros | Гирос | Gyros
Paella | Паэлья | Paella
Fettuchini | Феттучини | Fettuccine alfredo
Karbonara | Карбонара | Carbonara
Mol steyk | Стейк из говядины | Beef steak
Losos steyk | Стейк из лосося | Salmon steak
Tovuq kotlet | Куриная котлета | Chicken cutlet
Teftel | Тефтели | Meatballs (tefteli)
Dudlangan mol go'shti | Копчёная говядина | Smoked beef
Dudlangan kolbasa | Копчёная колбаса | Smoked sausage
Salo | Сало | Pork lard (salo)
Xinkali | Хинкали | Khinkali
Xachapuri | Хачапури | Khachapuri
Lobio | Лобио | Lobio
Satsivi | Сациви | Satsivi
Chixirtma | Чихиртма | Chikhirtma
Okroshka | Окрошка | Okroshka
Tvorogli blinchik | Блинчики с творогом | Pancakes with cottage cheese
Go'shtli blinchik | Блинчики с мясом | Pancakes with meat
Napoleon tort | Торт Наполеон | Napoleon cake
Shokoladli tort | Шоколадный торт | Chocolate cake
Mevali tort | Фруктовый торт | Fruit cake
Mannik | Манник | Mannik (semolina cake)
Kremli pirojnoe | Пирожное с кремом | Cream pastry
Qumli pechenye | Песочное печенье | Shortbread cookies
Kremli vafli | Вафли с кремом | Cream wafers
Sutli suli bo'tqasi | Овсянка на молоке | Oatmeal with milk
Yog'li tvorog | Жирный творог | Full-fat cottage cheese
Adigey pishlog'i | Адыгейский сыр | Adyghe cheese
Brinza | Брынза | Brinza (feta-style cheese)
Mozzarella | Моцарелла | Mozzarella
Qattiq pishloq | Твёрдый сыр | Hard cheese
Eritilgan pishloq | Плавленый сыр | Processed cheese
Smetana | Сметана | Sour cream
Mayonez | Майонез | Mayonnaise
Achchiq shokolad | Горький шоколад | Dark chocolate
Xuruz | Варёная кукуруза | Boiled corn
Qutab | Кутаб | Qutab
"""
