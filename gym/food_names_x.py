"""Turkish, Kyrgyz and Tajik display names of the built-in foods (the Uzbek names are in food_data1.py / food_data2.py).

Line format:  English name (exactly as in food_names.py) | Turkish | Kyrgyz | Tajik
Turkish has a name for every food. Kyrgyz and Tajik have the most common foods and Uzbek dishes; an empty cell falls back to the Russian name
(see food_names.py / food_db.py). Names of a member's own foods are never translated.
"""

RAW = """
Plov (pilaf) | Özbek pilavı (plov) | Палоо (плов) | Палав (плов)
Lagman | Lağman | Лагман | Лағмон
Manti (steamed dumplings) | Mantı (buharda) | Манты (буулантылган) | Манту (бухорӣ)
Samsa (meat) | Samsa (etli) | Самса (этүү) | Самбӯса (бо гӯшт)
Shashlik (beef kebab) | Şaşlık (dana) | Шашлык (уй этинен) | Шашлик (аз гӯшти гов)
Shashlik (lamb kebab) | Şaşlık (kuzu) | Шашлык (кой этинен) | Шашлик (аз гӯшти гӯсфанд)
Flatbread (tandoor) | Tandır ekmeği | Тандыр нан | Нони тандурӣ
White bread | Beyaz ekmek | Ак нан | Нони сафед
Rice (boiled) | Pirinç (haşlanmış) | Күрүч (бышырылган) | Биринҷ (пухта)
Buckwheat (cooked) | Karabuğday (pişmiş) | Гречка (бышырылган) | Марҷумак (пухта)
Oatmeal (with water) | Yulaf lapası (suyla) | Сули ашы (сууда) | Шӯлаи овёс (бо об)
Pasta (cooked) | Makarna (haşlanmış) | Макарон (бышырылган) | Макарон (пухта)
Potato (boiled) | Patates (haşlanmış) | Картөшкө (бышырылган) | Картошка (пухта)
French fries | Patates kızartması | Картөшкө фри | Картошкаи фри
Egg (boiled) | Yumurta (haşlanmış) | Жумуртка (бышырылган) | Тухм (ҷӯшонда)
Omelette | Omlet | Омлет | Омлет
Chicken breast (cooked) | Tavuk göğsü (pişmiş) | Тоок төшү (бышырылган) | Синаи мурғ (пухта)
Chicken (fried) | Tavuk (kızartma) | Тоок (куурулган) | Мурғ (бирён)
Beef (boiled) | Dana eti (haşlanmış) | Уй эти (бышырылган) | Гӯшти гов (пухта)
Lamb (boiled) | Kuzu eti (haşlanmış) | Кой эти (бышырылган) | Гӯшти гӯсфанд (пухта)
Fish (boiled) | Balık (haşlanmış) | Балык (бышырылган) | Моҳӣ (пухта)
Tuna (canned) | Ton balığı (konserve) | Тунец (консерва) | Тунец (консерва)
Sausage (boiled) | Sosis (haşlanmış) | Колбаса (бышырылган) | Колбаса (пухта)
Milk (2.5%) | Süt (%2,5) | Сүт (2,5%) | Шир (2,5%)
Kefir (2.5%) | Kefir (%2,5) | Кефир (2,5%) | Кефир (2,5%)
Yogurt (qatiq) | Yoğurt (katık) | Каймак (катык) | Қатиқ
Cottage cheese (5%) | Lor peyniri (%5) | Сүзмө (5%) | Панири сузма (5%)
Cottage cheese (low fat) | Lor peyniri (az yağlı) | Сүзмө (майсыз) | Панири сузма (камравған)
Cheese | Peynir | Быштак | Панир
Sour cream (20%) | Ekşi krema (%20) | Каймак (20%) | Сметана (20%)
Butter | Tereyağı | Сары май | Равғани маска
Vegetable oil | Bitkisel yağ | Өсүмдүк майы | Равғани наботӣ
Banana | Muz | Банан | Банан
Apple | Elma | Алма | Себ
Grapes | Üzüm | Жүзүм | Ангур
Quince | Ayva | Айва | Беҳӣ
Pomegranate | Nar | Анар | Анор
Orange | Portakal | Апельсин | Афлесун
Melon | Kavun | Коон | Харбуза
Watermelon | Karpuz | Дарбыз | Тарбуз
Dried apricots | Kuru kayısı | Кургак өрүк | Ҷонгилон
Raisins | Kuru üzüm | Мейиз | Мавиз
Walnut | Ceviz | Грек жаңгагы | Чормағз
Almond | Badem | Бадам | Бодом
Pistachios | Antep fıstığı | Мисте | Писта
Tomato | Domates | Помидор | Помидор
Cucumber | Salatalık | Бадыраң | Бодиринг
Carrot | Havuç | Сабиз | Сабзӣ
Onion | Soğan | Пиязы | Пиёз
Cabbage | Lahana | Капуста | Карам
Shirchoy (milk tea soup) | Şirçoy (sütlü çay çorbası) | Ширчай (сүттүү чай шорпосу) | Ширчой (шӯрбои чойи шир)
Mastava | Mastava (pirinçli çorba) | Мастава | Мастова
Shurpa (meat soup) | Şurpa (et çorbası) | Шорпо (эт шорпосу) | Шӯрбо (бо гӯшт)
Dimlama (stewed meat and vegetables) | Dımlama (etli sebze güveci) | Дымлама (эт жана жашылча) | Димлама (гӯшт ва сабзавот)
Chuchvara (small dumplings) | Çüçvara (küçük mantı) | Чучвара (майда пельмень) | Чучвара (хурд)
Kazan kebab | Kazan kebabı | Казан кабоб | Қазонкабоб
Pizza | Pizza | Пицца | Питса
Burger | Hamburger | Бургер | Бургер
Chocolate (milk) | Sütlü çikolata | Сүттүү шоколад | Шоколади ширӣ
Cookies | Bisküvi | Печенье | Кукиҳо
Sugar | Şeker | Кант | Шакар
Honey | Bal | Бал | Асал
Tea (no sugar) | Çay (şekersiz) | Чай (кантсыз) | Чой (бе шакар)
Tea (with 2 sugar cubes) | Çay (2 küp şekerli) | Чай (2 кесек кант менен) | Чой (бо 2 пора шакар)
Cola | Kola | Кола | Кола
Orange juice | Portakal suyu | Апельсин ширеси | Шарбати афлесун
Protein powder (whey) | Protein tozu (whey) | Протеин порошогу (whey) | Хокаи протеин (whey)
Protein bar | Protein bar | Протеин батончиги | Батончики протеин
Wedding plov | Düğün pilavı (to'y oshi) | Той палоосу | Палави тӯй
Tashkent plov | Taşkent pilavı | Ташкент палоосу | Палави тошкандӣ
Samarkand plov | Semerkant pilavı | Самарканд палоосу | Палави самарқандӣ
Plov (with lamb) | Pilav (kuzu etli) | Палоо (кой этинен) | Палав (бо гӯшти гӯсфанд)
Plov (with beef) | Pilav (dana etli) | Палоо (уй этинен) | Палав (бо гӯшти гов)
Plov (with chicken) | Pilav (tavuklu) | Палоо (тоок этинен) | Палав (бо мурғ)
Diet plov | Diyet pilav | Диеталык палоо | Палави парҳезӣ
Devzira plov | Devzira pilavı | Девзира палоосу | Палави девзира
Mung bean rice (mashkichiri) | Maş fasulyeli pilav (maşkiçiri) | Маш күрүч (машкичири) | Машкичири (биринҷ бо маш)
Mung bean soup (moshkhurda) | Maş fasulyesi çorbası (moşhurda) | Маш шорпосу (мошхурда) | Мошхӯрда
Shavla (thick rice dish) | Şavla (yoğun pirinç yemeği) | Шавла (коюу күрүч тамагы) | Шавла (таоми ғафси биринҷ)
Porridge (rice, milk) | Sütlü pirinç lapası | Сүттүү күрүч ашы | Шир-биринҷ
Sumalak (wheat sprout pudding) | Sümelek (buğday filizi tatlısı) | Сумалак (буудай өскөнүнөн) | Сумалак (аз ниҳоли гандум)
Mastava (with meat) | Mastava (etli) | Мастава (этүү) | Мастова (бо гӯшт)
Soup (chicken) | Çorba (tavuklu) | Шорпо (тоок) | Шӯрбо (бо мурғ)
Shurpa (lamb) | Şurpa (kuzu etli) | Шорпо (кой этинен) | Шӯрбо (аз гӯшти гӯсфанд)
Fish soup | Balık çorbası | Балык шорпосу | Шӯрбои моҳӣ
Chickpea soup | Nohut çorbası | Нокот шорпосу | Шӯрбои нахӯд
Lentil soup | Mercimek çorbası | Жасмык шорпосу | Шӯрбои ади
Bean soup | Fasulye çorbası | Төө буурчак шорпосу | Шӯрбои лӯбиё
Chicken noodle soup | Tavuklu şehriye çorbası | Тоок кесме шорпосу | Угро бо мурғ
Vegetable soup | Sebze çorbası | Жашылча шорпосу | Шӯрбои сабзавот
Broth (meat) | Et suyu | Эт сорпосу | Обгӯшт
Umoch (flour soup) | Umaç (unlu çorba) | Умач (ун шорпосу) | Умоч (шӯрбои орд)
Atala (thin flour soup) | Atala (ince unlu çorba) | Атала (ингичке ун шорпосу) | Атала (шӯрбои орди тунук)
Herb dumplings | Otlu mantı | Чөп куюлган манты | Чучвараи сабзӣ
Dumplings in broth | Çorbalı mantı | Шорподогу манты | Чучвара дар шӯрбо
Dumplings (fried) | Mantı (kızarmış) | Манты (куурулган) | Манту (бирён)
Chalop (cold yogurt soup) | Çalop (soğuk yoğurt çorbası) | Чалоп (муздак катык шорпосу) | Чалоп (шӯрбои хунуки қатиқ)
Okroshka (with kefir) | Okroşka (kefirli) | Окрошка (кефир менен) | Окрошка (бо кефир)
Beshbarmak | Beşparmak | Бешбармак | Бешбармок
Naryn (cold noodles with meat) | Narın (etli soğuk erişte) | Нарын (этүү муздак кесме) | Нарин (угрои хунук бо гӯшт)
Fried meat | Kavurma (et) | Куурулган эт | Гӯшти бирён
Kovurdak (meat and potato roast) | Kavurdak (etli patates kavurma) | Куурдак (эт жана картөшкө) | Қовурдоқ (гӯшт ва картошка)
Zharkop (meat and potato stew) | Jarkop (etli patates güveci) | Жаркоп (эт жана картөшкө) | Жаркоп (гӯшт ва картошка)
Dolma (stuffed grape leaves) | Yaprak sarma | Долма (жүзүм жалбырагы) | Долма (барги ангур)
Stuffed cabbage rolls | Lahana sarma | Голубцы (капуста оромо) | Голубсӣ (карам печон)
Stuffed eggplant | Patlıcan dolması | Баклажан долмасы | Боёнҷони долма
Stuffed pepper | Biber dolması | Болгар калемпир долмасы | Қаламфури долма
Khanum (steamed meat roll) | Hanım (buharda et rulosu) | Ханум (буулантылган эт орому) | Ханум (рулети буғии гӯштӣ)
Manti (pumpkin) | Mantı (balkabaklı) | Манты (ашкабак) | Манту (бо каду)
Manti (potato) | Mantı (patatesli) | Манты (картөшкө) | Манту (бо картошка)
Manti (chicken) | Mantı (tavuklu) | Манты (тоок) | Манту (бо мурғ)
Egg barak (stuffed dumplings) | Yumurtalı barak | Жумуртка барак | Баракҳои тухмдор
Lula kebab | Lüle kebap | Люля-кебаб | Люля-кабоб
Tandoor kebab | Tandır kebabı | Тандыр кабоб | Кабоби тандурӣ
Liver kebab | Ciğer kebabı | Боор кабоб | Кабоби ҷигар
Shashlik (chicken kebab) | Şaşlık (tavuk) | Шашлык (тоок) | Шашлик (аз мурғ)
Shashlik (fat tail kebab) | Şaşlık (kuyruk yağlı) | Шашлык (куйруктуу) | Шашлик (бо думба)
Lamb tail fat | Kuyruk yağı | Куйрук май | Равғани думба
Kazy (horse sausage) | Kazı (at sucuğu) | Казы (жылкы колбасасы) | Қозӣ (колбасаи аспӣ)
Karta (horse intestine) | Karta (at bağırsağı) | Карта (жылкы ичеги) | Карта (рӯдаи аспӣ)
Tandoor meat | Tandır eti | Тандыр эти | Гӯшти тандурӣ
Jiz-biz (fried offal) | Jız-bız (kızarmış sakatat) | Жиз-биз (куурулган бөйрөк-боор) | Ҷиз-биз (қалбгӯшт бирён)
Baursak | Börsek (bavırsak) | Боорсок | Бовурсоқ
Samsa (tandoor, lamb) | Samsa (tandır, kuzu etli) | Самса (тандыр, кой этинен) | Самбӯса (тандурӣ, гӯсфанд)
Samsa (puff pastry) | Samsa (milföy) | Самса (катмарлуу камыр) | Самбӯса (хамираи қабатӣ)
Samsa (pumpkin) | Samsa (balkabaklı) | Самса (ашкабак) | Самбӯса (бо каду)
Samsa (potato) | Samsa (patatesli) | Самса (картөшкө) | Самбӯса (бо картошка)
Samsa (chicken) | Samsa (tavuklu) | Самса (тоок) | Самбӯса (бо мурғ)
Samsa (liver) | Samsa (ciğerli) | Самса (боор) | Самбӯса (бо ҷигар)
Samsa (cheese) | Samsa (peynirli) | Самса (быштак) | Самбӯса (бо панир)
Samsa (herbs) | Samsa (otlu) | Самса (чөптүү) | Самбӯса (бо кабудӣ)
Gumma (meat pie) | Gumma (etli börek) | Гумма (этүү пирог) | Гумма (пирожкаи гӯштӣ)
Pirozhki (meat) | Piroşki (etli) | Пирожки (этүү) | Пирожки (бо гӯшт)
Pirozhki (potato) | Piroşki (patatesli) | Пирожки (картөшкө) | Пирожки (бо картошка)
Chebureki | Çiğ börek | Чебуреки | Чебуреки
Belyash | Belyaş | Беляш | Беляш
Apple pie | Elmalı turta | Алмалуу пирог | Пирожкаи себӣ
Katlama (layered flatbread) | Katlama (katmerli ekmek) | Катлама (катмарлуу нан) | Қатлама (нони қабатӣ)
Achichuk (tomato and onion salad) | Acıçuk (domates soğan salatası) | Ачичук (помидор-пияз салаты) | Аччиқчук (салати помидор ва пиёз)
Korean carrot salad | Kore usulü havuç salatası | Корей сабиз салаты | Салати сабзии кореягӣ
Tomato and cucumber salad | Domates salatalık salatası | Помидор-бадыраң салаты | Салати помидор ва бодиринг
Cabbage salad | Lahana salatası | Капуста салаты | Салати карам
Carrot salad | Havuç salatası | Сабиз салаты | Салати сабзӣ
Mashed potatoes | Patates püresi | Картөшкө пюреси | Пюреи картошка
Fried potatoes | Kızarmış patates | Куурулган картөшкө | Картошкаи бирён
Baked potato | Fırında patates | Бышкан картөшкө | Картошкаи дар танӯр пухта
Potato pancakes | Patates köftesi | Картөшкө оладьясы | Деруни картошка
Borscht | Borş | Борщ | Борщ
Shchi (cabbage soup) | Şçi (lahana çorbası) | Щи (капуста шорпосу) | Щи (шӯрбои карам)
Solyanka | Solyanka | Солянка | Солянка
Rassolnik (pickle soup) | Rassolnik (turşulu çorba) | Рассольник (туздуктуу шорпо) | Рассолник (шӯрбои хиёрдӯшоб)
Kharcho | Haşo (Gürcü çorbası) | Харчо | Харчо
Dumplings (store-bought) | Mantı (hazır) | Пельмени (даяр) | Пелмени (тайёр)
Vareniki (potato) | Vareniki (patatesli) | Вареники (картөшкө) | Вареники (бо картошка)
Vareniki (cottage cheese) | Vareniki (lor peynirli) | Вареники (сүзмө) | Вареники (бо панири сузма)
Pancakes (blini) | Blini (krep) | Блины | Блины
Fritters | Mayalı gözleme | Оладьи | Оладья
Syrniki (cottage cheese pancakes) | Sirniki (lorlu köfte) | Сырники (сүзмөдөн) | Сырники (аз панири сузма)
Crepes (cottage cheese) | Krep (lor peynirli) | Блины (сүзмө менен) | Блины (бо панири сузма)
Crepes (meat) | Krep (etli) | Блины (эт менен) | Блины (бо гӯшт)
Cutlet (beef) | Köfte (dana) | Котлет (уй эти) | Котлет (аз гӯшти гов)
Cutlet (chicken) | Köfte (tavuk) | Котлет (тоок) | Котлет (аз мурғ)
Beef stroganoff | Beef stroganoff | Бефстроганов | Бефстроганов
Goulash | Gulaş | Гуляш | Гуляш
Fried eggs | Sahanda yumurta | Куурулган жумуртка | Тухми бирён
Egg (raw) | Yumurta (çiğ) | Жумуртка (чийки) | Тухм (хом)
Egg white | Yumurta akı | Жумуртканын агы | Сафедаи тухм
Egg yolk | Yumurta sarısı | Жумуртканын сарысы | Зардаи тухм
Quail eggs | Bıldırcın yumurtası | Бөдөнө жумурткасы | Тухми бедона
Olivier salad | Rus salatası (Olivier) | Оливье салаты | Салати Оливье
Vinaigrette (beet salad) | Vinegret (pancar salatası) | Винегрет (кызылча салаты) | Винегрет (салати лаблабу)
Herring under a fur coat | Kürk mantolu ringa | «Тон кийген» сельдь | Селёдка зери пальто
Mimosa salad | Mimoza salatası | Мимоза салаты | Салати Мимоза
Crab salad | Yengeç salatası | Краб салаты | Салати краб
Caesar salad | Sezar salatası | Цезарь салаты | Салати Цезарь
Greek salad | Yunan salatası | Грек салаты | Салати юнонӣ
Green salad | Yeşil salata | Жашыл салат | Салати сабз
Hot dog | Sosisli sandviç | Хот-дог | Хот-дог
Sandwich (sausage, cheese) | Sandviç (sosisli, peynirli) | Сэндвич (колбаса, быштак) | Сэндвич (колбаса, панир)
Sandwich (with sausage) | Sandviç (sosisli) | Сэндвич (колбаса менен) | Сэндвич (бо колбаса)
Sandwich (with cheese) | Sandviç (peynirli) | Сэндвич (быштак менен) | Сэндвич (бо панир)
Bread and butter | Tereyağlı ekmek | Май жаккан нан | Нон бо равған
Toast (grilled sandwich) | Tost | Тост (грилде бышырылган бутерброд) | Тост (бутерброди гриль)
Cheeseburger | Çizburger | Чизбургер | Чизбургер
Big burger | Büyük hamburger | Чоң бургер | Бургери калон
Chicken burger | Tavuk burger | Тоок бургер | Бургер бо мурғ
Pizza (Margherita) | Pizza (Margarita) | Пицца (Маргарита) | Питса (Маргарита)
Pizza (pepperoni) | Pizza (Pepperoni) | Пицца (Пепперони) | Питса (Пепперони)
Pizza (4 cheese) | Pizza (4 peynirli) | Пицца (4 быштак) | Питса (4 панир)
Pizza (chicken) | Pizza (tavuklu) | Пицца (тоок менен) | Питса (бо мурғ)
Shawarma (chicken) | Tavuk döner (şavurma) | Шаурма (тоок) | Шаурма (бо мурғ)
Shawarma (beef or lamb) | Et döner (şavurma) | Шаурма (уй же кой эти) | Шаурма (гов ё гӯсфанд)
Lavash roll (meat) | Lavaş dürüm (etli) | Лаваш орому (этүү) | Лаваш печон (бо гӯшт)
Chicken nuggets | Tavuk nugget | Тоок наггетси | Нагетси мурғ
Chicken wings (fried) | Tavuk kanadı (kızarmış) | Тоок канаты (куурулган) | Болҳои мурғ (бирён)
Chicken strips | Tavuk şerit | Тоок тилкелери | Навори мурғ
Onion rings | Soğan halkası | Пияз шакекчелери | Ҳалқаҳои пиёз
Taco | Taco | Тако | Тако
Burrito | Burrito | Буррито | Буррито
Panini | Panini | Панини | Панини
Sandwich (chicken, small) | Sandviç (tavuklu, küçük) | Сэндвич (тооктуу, кичине) | Сэндвич (бо мурғ, хурд)
Donut | Donut | Пончик | Пончик
Croissant | Kruvasan | Круассан | Круассан
Croissant (chocolate) | Kruvasan (çikolatalı) | Круассан (шоколаддуу) | Круассан (бо шоколад)
Frankfurter | Sosis (Frankfurter) | Сосиска | Сосиска
Chicken sausage | Tavuk sosis | Тоок колбасасы | Колбасаи мурғ
Mozzarella sticks | Mozzarella sticks (peynir çubukları) | Моцарелла таякчалары | Чубчаҳои моцарелла
Falafel | Falafel | Фалафель | Фалафел
Hummus | Humus | Хумус | Хумус
Sushi (rolls) | Suşi (rulo) | Суши (роллдор) | Суши (роллҳо)
Philadelphia roll | Philadelphia rulo | Филадельфия ролл | Ролли Филадельфия
Potato chips | Patates cipsi | Картөшкө чипси | Чипси картошка
Popcorn | Patlamış mısır | Попкорн | Попкорн
Croutons | Kruton | Сухарики | Сухарик
Crackers | Kraker | Крекер | Крекер
Instant noodles (dry) | Hazır noodle (kuru) | Даяр лапша (кургак) | Лапшаи тайёр (хушк)
Instant noodles (prepared) | Hazır noodle (hazırlanmış) | Даяр лапша (бышырылган) | Лапшаи тайёр (тайёршуда)
Pasta carbonara | Makarna karbonara | Макарон карбонара | Макарони карбонара
Pasta bolognese | Makarna bolonez | Макарон болоньезе | Макарони болонез
Lasagna | Lazanya | Лазанья | Лазанья
Risotto | Risotto | Ризотто | Ризотто
Mac and cheese | Peynirli makarna | Быштактуу макарон | Макарони бо панир
Lahmacun (Turkish flatbread pizza) | Lahmacun | Лахмаджун (түрк пиццасы) | Лахмаҷун (питсаи туркӣ)
Rice (raw) | Pirinç (çiğ) | Күрүч (чийки) | Биринҷ (хом)
Brown rice (cooked) | Esmer pirinç (pişmiş) | Күрөң күрүч (бышырылган) | Биринҷи қаҳваранг (пухта)
Buckwheat (raw) | Karabuğday (çiğ) | Гречка (чийки) | Марҷумак (хом)
Rolled oats (dry) | Yulaf ezmesi (kuru) | Сули жармасы (кургак) | Ҳурдаи овёс (хушк)
Oatmeal (with milk) | Yulaf lapası (sütle) | Сули ашы (сүт менен) | Шӯлаи овёс (бо шир)
Barley porridge | Arpa lapası | Арпа ашы | Шӯлаи ҷав
Millet porridge | Darı lapası | Таруу ашы | Шӯлаи арзан
Semolina porridge | İrmik lapası | Манный ашы | Шӯлаи манка
Rice porridge (with milk) | Sütlaç lapası (sütlü pirinç) | Сүттүү күрүч ашы | Шир-биринҷ
Corn porridge (polenta) | Mısır lapası (polenta) | Жүгөрү ашы (полента) | Шӯлаи ҷуворимакка
Couscous (cooked) | Kuskus (pişmiş) | Кускус (бышырылган) | Кускус (пухта)
Bulgur (cooked) | Bulgur (pişmiş) | Булгур (бышырылган) | Булгур (пухта)
Quinoa (cooked) | Kinoa (pişmiş) | Киноа (бышырылган) | Киноа (пухта)
Mung beans (cooked) | Maş fasulyesi (pişmiş) | Маш (бышырылган) | Маш (пухта)
Mung beans (dry) | Maş fasulyesi (kuru) | Маш (кургак) | Маш (хушк)
Chickpeas (cooked) | Nohut (pişmiş) | Нокот (бышырылган) | Нахӯд (пухта)
Chickpeas (dry) | Nohut (kuru) | Нокот (кургак) | Нахӯд (хушк)
Beans (cooked) | Fasulye (pişmiş) | Төө буурчак (бышырылган) | Лӯбиё (пухта)
Beans (dry) | Fasulye (kuru) | Төө буурчак (кургак) | Лӯбиё (хушк)
Lentils (cooked) | Mercimek (pişmiş) | Жасмык (бышырылган) | Ади (пухта)
Lentils (dry) | Mercimek (kuru) | Жасмык (кургак) | Ади (хушк)
Green peas (canned) | Bezelye (konserve) | Жашыл буурчак (консерва) | Нахӯдак (консерва)
Corn (boiled) | Mısır (haşlanmış) | Жүгөрү (бышырылган) | Ҷуворимакка (пухта)
Sweet corn (canned) | Tatlı mısır (konserve) | Таттуу жүгөрү (консерва) | Ҷуворимаккаи ширин (консерва)
Tofu | Tofu | Тофу | Тофу
Soy meat (dry) | Soya eti (kuru) | Соя эти (кургак) | Гӯшти соя (хушк)
Pasta (dry) | Makarna (kuru) | Макарон (кургак) | Макарон (хушк)
Noodles (cooked) | Erişte (pişmiş) | Кесме (бышырылган) | Угро (пухта)
Rice noodles | Pirinç eriştesi | Күрүч кесмеси | Угрои биринҷ
Udon noodles | Udon eriştesi | Удон кесмеси | Угрои удон
Gnocchi | Gnocchi (nyoki) | Ньокки | Ньокки
Flatbread (whole, tandoor) | Tandır ekmeği (bütün) | Тандыр нан (бүтүн) | Нони тандурӣ (бутун)
Obi non (Uzbek bread) | Obi non (Özbek ekmeği) | Оби нан (өзбек наны) | Оби нон (нони ӯзбекӣ)
Patir (rich flatbread) | Patır (yağlı ekmek) | Патыр (майлуу нан) | Патир (нони равғанӣ)
Lochira (Uzbek flatbread) | Loçira (Özbek ekmeği) | Лочира (өзбек наны) | Лочира (нони ӯзбекӣ)
Shirmon (sweet milk bread) | Şirmon (sütlü tatlı ekmek) | Ширмон (сүттүү таттуу нан) | Ширмон (нони ширини шириӣ)
Kulcha | Kulça | Кулча | Кулча
Zogora (cornmeal flatbread) | Zogora (mısır unlu ekmek) | Зогора (жүгөрү унунан нан) | Зогора (нони орди ҷуворимакка)
Sweet bun | Tatlı çörek | Таттуу булочка | Булочкаи ширин
Baguette | Baget | Багет | Багет
Sliced toast bread | Tost ekmeği | Тост наны | Нони тост
Bran bread | Kepekli ekmek | Кебектүү нан | Нони кунҷоладор
Rye bread | Çavdar ekmeği | Кара буудай наны | Нони ҷавдор
Lavash (thin bread) | Lavaş | Лаваш (жука нан) | Лаваш (нони тунук)
Pita | Pita | Пита | Пита
Tortilla | Tortilla | Тортилья | Тортилья
Bagel | Simit (bagel) | Бейгл | Бейгл
Bread rings | Simit | Токоч | Баранка
Gingerbread | Zencefilli kurabiye | Пряник | Пряник
Wafers | Gofret | Вафли | Вафли
Oatmeal cookies | Yulaflı kurabiye | Сулу печеньеси | Кукии овёс
American pancakes | Amerikan pankek | Америкалык панкейк | Панкейки амрикоӣ
Muesli | Müsli | Мюсли | Мюсли
Granola | Granola | Гранола | Гранола
Cornflakes | Mısır gevreği | Жүгөрү жалбырактары | Қиёми ҷуворимакка
Flour (wheat) | Un (buğday) | Ун (буудай) | Орд (гандум)
Corn flour | Mısır unu | Жүгөрү уну | Ордӣ ҷуворимакка
Chicken breast (raw) | Tavuk göğsü (çiğ) | Тоок төшү (чийки) | Синаи мурғ (хом)
Chicken thighs (cooked) | Tavuk but (pişmiş) | Тоок буту (бышырылган) | Рони мурғ (пухта)
Chicken drumstick | Tavuk baget | Тоок сою | Соқи мурғ
Chicken wings (raw) | Tavuk kanadı (çiğ) | Тоок канаты (чийки) | Болҳои мурғ (хом)
Chicken liver | Tavuk ciğeri | Тоок боору | Ҷигари мурғ
Chicken hearts | Tavuk yüreği | Тоок жүрөгү | Дили мурғ
Chicken gizzards | Tavuk taşlığı | Тоок капчыгы | Таши мурғ
Roast chicken (tandoor) | Tandır tavuğu | Тандыр тоок | Мурғи тандурӣ
Turkey (breast) | Hindi (göğüs) | Үндүк (төш) | Мурғи марҷон (сина)
Turkey | Hindi | Үндүк | Мурғи марҷон
Duck | Ördek | Өрдөк | Мурғобӣ
Goose | Kaz | Каз | Қоз
Rabbit | Tavşan | Коён | Харгӯш
Beef (raw) | Dana eti (çiğ) | Уй эти (чийки) | Гӯшти гов (хом)
Ground beef | Dana kıyma | Уй этинин фаршы | Қимаи гӯшти гов
Beef steak (fried) | Dana biftek (kızarmış) | Уй стейги (куурулган) | Стейки гов (бирён)
Beef tenderloin | Dana bonfile | Уй филеси | Филеи гов
Beef liver (fried) | Dana ciğeri (kızarmış) | Уй боору (куурулган) | Ҷигари гов (бирён)
Beef tongue | Dana dili | Уй тили | Забони гов
Beef heart | Dana yüreği | Уй жүрөгү | Дили гов
Lamb (raw) | Kuzu eti (çiğ) | Кой эти (чийки) | Гӯшти гӯсфанд (хом)
Lamb ribs | Kuzu kaburga | Кой кабыргасы | Қабурғаи гӯсфанд
Ground lamb | Kuzu kıyma | Кой этинин фаршы | Қимаи гӯшти гӯсфанд
Lamb liver | Kuzu ciğeri | Кой боору | Ҷигари гӯсфанд
Pork | Domuz eti | Чочко эти | Гӯшти хук
Ground pork | Domuz kıyma | Чочко этинин фаршы | Қимаи гӯшти хук
Horse meat | At eti | Жылкы эти | Гӯшти асп
Ham | Jambon | Ветчина | Ветчина
Bacon | Domuz pastırması | Бекон | Бекон
Salami | Salam | Салями | Салями
Sausage (smoked) | Sucuk (füme) | Колбаса (ышталган) | Колбаса (дудкардашуда)
Sausage (doctor's) | Doktor salam (haşlanmış sosis) | Колбаса (доктордук) | Колбаса (докторӣ)
Pate | Ezme (pate) | Паштет | Паштет
Canned stewed meat | Konserve et (haşlama) | Тушенка (консерва эти) | Тушёнка (гӯшти консерв)
Meat (jerky) | Kurutulmuş et (jerky) | Кургатылган эт (джерки) | Гӯшти хушк (джерки)
Salmon (baked) | Somon (fırında) | Лосось (бышкан) | Лосос (дар танӯр пухта)
Salmon (raw) | Somon (çiğ) | Лосось (чийки) | Лосос (хом)
Salmon (salted) | Somon (tuzlu) | Лосось (туздалган) | Лосос (намакин)
Trout | Alabalık | Форель | Гулмоҳӣ
Mackerel | Uskumru | Скумбрия | Скумбрия
Herring (salted) | Ringa (tuzlu) | Сельдь (туздалган) | Селёдка (намакин)
Cod | Morina | Треска | Треска
Carp | Sazan | Карп | Карп
Pike perch | Sudak | Судак | Судак
Tilapia | Tilapya | Тилапия | Тилапия
Hake | Mezgit | Хек | Хек
Fish (fried) | Balık (kızarmış) | Балык (куурулган) | Моҳӣ (бирён)
Fish (breaded) | Balık (galetalı) | Балык (панировкада) | Моҳӣ (дар панировка)
Red caviar | Kırmızı havyar | Кызыл икра | Икраи сурх
Black caviar | Siyah havyar | Кара икра | Икраи сиёҳ
Crab sticks | Yengeç çubukları | Краб таякчалары | Чубчаҳои краб
Shrimp | Karides | Креветка | Креветка
Mussels | Midye | Мидия | Мидия
Squid | Kalamar | Кальмар | Кальмар
Sprats (canned) | Çaça (konserve) | Шпроттор (консерва) | Шпрот (консерва)
Sardines (canned) | Sardalya (konserve) | Сардина (консерва) | Сардина (консерва)
Canned fish (in tomato sauce) | Konserve balık (domates soslu) | Балык консервасы (помидор соусунда) | Консерваи моҳӣ (дар соуси помидор)
Milk (3.2%) | Süt (%3,2) | Сүт (3,2%) | Шир (3,2%)
Milk (1.5%) | Süt (%1,5) | Сүт (1,5%) | Шир (1,5%)
Milk (skim) | Süt (yağsız) | Сүт (майсыз) | Шир (бе равған)
Goat milk | Keçi sütü | Эчки сүтү | Шири буз
Milk powder | Süt tozu | Сүт порошогу | Хокаи шир
Condensed milk | Yoğunlaştırılmış süt | Коюлтулган сүт | Шири конденсатсияшуда
Cream (10%) | Krema (%10) | Каймак (10%) | Қаймоқ (10%)
Cream (20%) | Krema (%20) | Каймак (20%) | Қаймоқ (20%)
Cream (33%) | Krema (%33) | Каймак (33%) | Қаймоқ (33%)
Sour cream (10%) | Ekşi krema (%10) | Сметана (10%) | Сметана (10%)
Sour cream (15%) | Ekşi krema (%15) | Сметана (15%) | Сметана (15%)
Kefir (1%) | Kefir (%1) | Кефир (1%) | Кефир (1%)
Kefir (fat free) | Kefir (yağsız) | Кефир (майсыз) | Кефир (камравған)
Ryazhenka (baked milk) | Ryazhenka (fırınlanmış süt) | Ряженка (бышырылган сүт) | Ряженка (шири пухта)
Ayran | Ayran | Айран | Айрон
Yogurt (qatiq, low fat) | Yoğurt (katık, az yağlı) | Катык (майы аз) | Қатиқ (камравған)
Yogurt (qatiq, full fat) | Yoğurt (katık, tam yağlı) | Катык (майлуу) | Қатиқ (серравған)
Suzma (strained yogurt) | Süzme (süzme yoğurt) | Сүзмө (сүзүлгөн катык) | Сузма (қатиқи сузишуда)
Qurt (dried cheese balls) | Kurut (kuru peynir topları) | Курут (кургатылган быштак) | Қурут
Soured milk | Ekşi süt | Ачыган сүт | Шири турш
Yogurt (plain) | Yoğurt (sade) | Йогурт (кошумчасыз) | Йогурт (оддӣ)
Yogurt (fruit) | Yoğurt (meyveli) | Йогурт (жемиштүү) | Йогурт (бо мева)
Greek yogurt | Yunan yoğurdu | Грек йогурту | Йогурти юнонӣ
Yogurt (fat free) | Yoğurt (yağsız) | Йогурт (майсыз) | Йогурт (камравған)
Cottage cheese (9%) | Lor peyniri (%9) | Сүзмө (9%) | Панири сузма (9%)
Cottage cheese (fat free) | Lor peyniri (yağsız) | Сүзмө (майсыз) | Панири сузма (бе равған)
Glazed curd snack | Glazürlü lor atıştırmalığı | Глазурдалган сүзмө | Сырок (панири сузмаи глазурӣ)
Cheese (Russian) | Peynir (Rus) | Быштак (орус) | Панир (русӣ)
Cheese (Dutch) | Peynir (Hollanda) | Быштак (голландиялык) | Панир (голландӣ)
Cheese (mozzarella) | Peynir (mozzarella) | Быштак (моцарелла) | Панир (моцарелла)
Cheese (feta) | Beyaz peynir (feta) | Быштак (фета) | Панир (фета)
Cheese (suluguni) | Peynir (suluguni) | Быштак (сулугуни) | Панир (сулугуни)
Cheese (processed) | Eritme peynir | Эритилген быштак | Панири обшуда
Cheese (parmesan) | Peynir (parmesan) | Быштак (пармезан) | Панир (пармезан)
Cheese (cheddar) | Peynir (çedar) | Быштак (чеддер) | Панир (чеддер)
Cheese (camembert) | Peynir (kamember) | Быштак (камамбер) | Панир (камамбер)
Cheese (cream cheese) | Krem peynir | Каймак быштак | Панири қаймоқӣ
Mascarpone | Mascarpone | Маскарпоне | Маскарпоне
Ricotta | Ricotta | Рикотта | Рикотта
Ice cream (plombir) | Dondurma (kaymaklı) | Балмуздак (пломбир) | Яхмос (пломбир)
Ice cream (milk) | Dondurma (sütlü) | Балмуздак (сүттүү) | Яхмос (ширӣ)
Ice cream (chocolate-coated bar) | Dondurma (çikolata kaplı çubuk) | Балмуздак (шоколаддуу таякча) | Яхмос (бо шоколад)
Ice cream (chocolate) | Dondurma (çikolatalı) | Балмуздак (шоколаддуу) | Яхмос (шоколадӣ)
Margarine | Margarin | Маргарин | Маргарин
Ghee (clarified butter) | Sadeyağ | Эритилген май | Равғани маскаи обшуда
Kaymak (clotted cream) | Kaymak | Каймак | Қаймоқ
Pear | Armut | Алмурут | Нок
Peach | Şeftali | Шабдалы | Шафтолу
Nectarine | Nektarin | Нектарин | Нектарин
Apricot | Kayısı | Өрүк | Зардолу
Plum | Erik | Кара өрүк | Олу
Sweet cherry | Kiraz | Гилас | Гелос
Sour cherry | Vişne | Чие | Олуболу
Strawberry | Çilek | Кулпунай | Тути заминӣ
Raspberry | Ahududu | Дан куурай | Малина
Blackberry | Böğürtlen | Кара бүлдүркөн | Марминҷон
Blackcurrant | Siyah frenk üzümü | Кара карагат | Қарағати сиёҳ
Blueberry | Yabanmersini | Көк жидек | Ёбоми кабуд
Cranberry | Kızılcık | Клюква | Клюква
Tangerine | Mandalina | Мандарин | Мандарин
Lemon | Limon | Лимон | Лимӯ
Grapefruit | Greyfurt | Грейпфрут | Грейпфрут
Lime | Misket limonu | Лайм | Лайм
Kiwi | Kivi | Киви | Киви
Pineapple | Ananas | Ананас | Ананас
Mango | Mango | Манго | Манго
Papaya | Papaya | Папайя | Папайя
Avocado | Avokado | Авокадо | Авокадо
Persimmon | Trabzon hurması | Хурма | Хурмо
Fig (fresh) | İncir (taze) | Инжир (жаңы) | Анҷир (тар)
Fig (dried) | İncir (kuru) | Инжир (кургак) | Анҷир (хушк)
Dates | Hurma | Курма | Хурмо (хурмои арабӣ)
Prunes | Kuru erik | Кара өрүк (кургатылган) | Олуи хушк
Apples (dried) | Kuru elma | Кургак алма | Себи хушк
Pears (dried) | Kuru armut | Кургак алмурут | Нок хушк
Coconut (fresh) | Hindistan cevizi (taze) | Кокос (жаңы) | Кокос (тар)
Desiccated coconut | Hindistan cevizi rendesi | Кокос чыпчасы | Қиёми кокос
Mulberry | Dut | Тут | Тут
Mulberry (dried) | Kuru dut | Кургак тут | Тути хушк
Quince (dried) | Kuru ayva | Кургак айва | Беҳии хушк
Melon (dried) | Kuru kavun | Кургак коон | Харбузаи хушк
Jam | Reçel | Варенье | Мураббо
Marmalade candy | Jöle şeker (marmelat) | Мармелад | Мармелад
Pastila (fruit pastille) | Pastil (meyve pestili) | Пастила (жемиш) | Пастила (мевагӣ)
Fruit salad | Meyve salatası | Жемиш салаты | Салати мева
Canned fruit | Konserve meyve | Жемиш консерваси | Консерваи мева
Potato (raw) | Patates (çiğ) | Картөшкө (чийки) | Картошка (хом)
Sweet potato | Tatlı patates | Таттуу картөшкө | Картошкаи ширин
Pumpkin | Balkabağı | Ашкабак | Каду
Eggplant | Patlıcan | Баклажан | Боёнҷон
Bell pepper | Dolmalık biber | Болгар калемпири | Қаламфури булғорӣ
Chili pepper | Acı biber | Ачуу калемпир | Қаламфури тунд
Zucchini | Kabak | Кабачок | Кабачок
Radish | Turp | Редиска | Шалғамча
Turnip | Şalgam | Шалгам | Шалғам
Garlic | Sarımsak | Сарымсак | Сирпиёз
Green onion | Yeşil soğan | Жашыл пияз | Пиёзи сабз
Dill | Dereotu | Укроп | Шибит
Parsley | Maydanoz | Петрушка | Петрушка
Cilantro | Kişniş | Кинза | Кашнич
Basil | Fesleğen | Райкан | Райҳон
Lettuce | Marul | Салат жалбырагы | Коҳу
Spinach | Ispanak | Шпинат | Исфаноҷ
Broccoli | Brokoli | Брокколи | Брокколи
Cauliflower | Karnabahar | Түстүү капуста | Гулкарам
Brussels sprouts | Brüksel lahanası | Брюссель капустасы | Карами брюссел
Beetroot | Pancar | Кызылча | Лаблабу
Beetroot (boiled) | Pancar (haşlanmış) | Кызылча (бышырылган) | Лаблабу (пухта)
Carrot (boiled) | Havuç (haşlanmış) | Сабиз (бышырылган) | Сабзӣ (пухта)
Mushrooms | Mantar | Козу карын | Занбӯруғ
Mushrooms (fried) | Mantar (kızarmış) | Козу карын (куурулган) | Занбӯруғ (бирён)
Tomato paste | Domates salçası | Помидор пастасы | Хамираи помидор
Olives | Zeytin | Зайтун | Зайтун
Sauerkraut | Lahana turşusu | Ачытылган капуста | Карами турш
Pickled cucumbers | Salatalık turşusu | Туздалган бадыраң | Бодиринги намакин
Kimchi | Kimçi | Кимчи | Кимчи
Celery | Kereviz | Сельдерей | Карафс
Asparagus | Kuşkonmaz | Спаржа | Спаржа
Green beans | Taze fasulye | Жашыл төө буурчак | Лӯбиёи сабз
Green peas (fresh) | Bezelye (taze) | Жашыл буурчак (жаңы) | Нахӯдаки сабз (тар)
Horseradish | Yaban turpu | Хрен | Хрен
Avocado salad | Avokado salatası | Авокадо салаты | Салати авокадо
Vegetable salad (with oil) | Sebze salatası (yağlı) | Жашылча салаты (май менен) | Салати сабзавот (бо равған)
Vegetable stew | Sebze güveci | Жашылча сотеси | Хӯриши сабзавот
Eggplant caviar | Patlıcan ezmesi | Баклажан икрасы | Икраи боёнҷон
Hazelnuts | Fındık | Фундук | Фундук
Cashews | Kaju | Кешью | Кешью
Peanuts | Yer fıstığı | Жер жаңгагы | Чормағзи заминӣ
Peanut butter | Fıstık ezmesi | Жер жаңгак пастасы | Хамираи чормағзи заминӣ
Pecans | Pekan cevizi | Пекан | Пекан
Macadamia nuts | Makadamya | Макадамия | Макадамия
Brazil nuts | Brezilya cevizi | Бразилия жаңгагы | Чормағзи бразилӣ
Sunflower seeds | Ay çekirdeği | Күнкарама данеги | Тухми офтобпараст
Pumpkin seeds | Kabak çekirdeği | Ашкабак данеги | Тухми каду
Sesame seeds | Susam | Күнжүт | Кунҷид
Flax seeds | Keten tohumu | Зыгыр уругу | Тухми зағир
Chia seeds | Chia tohumu | Чиа уругу | Тухми чиа
Mixed nuts | Karışık kuruyemiş | Аралаш жаңгактар | Омехтаи чормағзҳо
Roasted chickpeas | Leblebi | Куурулган нокот | Нахӯди бирён
Chestnut | Kestane | Каштан | Шоҳбулут
Chocolate spread (Nutella) | Çikolatalı krema (Nutella) | Шоколад пастасы (Nutella) | Хамираи шоколадӣ (Nutella)
Tahini | Tahin | Тахини | Тахин
Olive oil | Zeytinyağı | Зайтун майы | Равғани зайтун
Cottonseed oil | Pamuk yağı | Пахта майы | Равғани пахта
Coconut oil | Hindistan cevizi yağı | Кокос майы | Равғани кокос
Sesame oil | Susam yağı | Күнжүт майы | Равғани кунҷид
Lard (pork fat) | Domuz yağı | Чочко майы | Равғани хук
Beef fat | Sığır yağı | Уй майы | Равғани гов
Mayonnaise (classic) | Mayonez (klasik) | Майонез (классикалык) | Майонез (классикӣ)
Mayonnaise (light) | Mayonez (light) | Майонез (жеңил) | Майонез (сабук)
Ketchup | Ketçap | Кетчуп | Кетчуп
Tomato sauce | Domates sosu | Помидор соусу | Соуси помидор
Soy sauce | Soya sosu | Соя соусу | Соуси соя
Mustard | Hardal | Горчица | Хардал
Pesto | Pesto | Песто | Песто
Garlic sauce | Sarımsaklı sos | Сарымсак соусу | Соуси сирпиёз
Ranch sauce | Ranch sos | Ранч соусу | Соуси ранч
BBQ sauce | Barbekü sosu | BBQ соусу | Соуси BBQ
Sweet chili sauce | Tatlı acı sos | Таттуу чили соусу | Соуси чилии ширин
Adjika | Adjika | Аджика | Аджика
Tkemali sauce | Tkemali sosu | Ткемали соусу | Соуси ткемали
Vinegar | Sirke | Уксус | Сирко
Salt | Tuz | Туз | Намак
Cumin | Kimyon | Зире | Зира
Ginger | Zencefil | Занжабил | Занҷабил
Cinnamon | Tarçın | Корица | Дорчин
Bechamel sauce | Beşamel sos | Бешамель соусу | Соуси бешамел
Chocolate (dark, 70%) | Bitter çikolata (%70) | Кара шоколад (70%) | Шоколади талх (70%)
Chocolate (white) | Beyaz çikolata | Ак шоколад | Шоколади сафед
Chocolate (with nuts) | Fındıklı çikolata | Жаңгактуу шоколад | Шоколад бо чормағз
Chocolate bar (Snickers) | Çikolata barı (Snickers) | Шоколад батончиги (Snickers) | Батончики шоколадӣ (Snickers)
Mars bar | Mars çikolata | Mars батончиги | Батончики Mars
Twix | Twix | Twix | Twix
Bounty | Bounty | Bounty | Bounty
Caramel candy | Karamel şeker | Карамель | Конфети карамелӣ
Chocolate candies | Çikolatalı şekerleme | Шоколад момпосуйлары | Конфетҳои шоколадӣ
Toffee | Toffee (sütlü karamel) | Ирис | Ирис
Marshmallow | Marshmallow (şeker köpüğü) | Зефир | Зефир
Lollipop | Lolipop | Чупа-чупс | Чупа-чупс
Halva (sesame) | Helva (susamlı) | Халва (күнжүт) | Ҳалво (кунҷид)
Halva (sunflower) | Helva (ay çekirdeği) | Халва (күнкарама) | Ҳалво (офтобпараст)
Halvaitar | Halvaytar | Халвайтар | Ҳалвоитар
Chak-chak | Çak-çak | Чак-чак | Чак-чак
Nabat (rock sugar) | Nabat (kaya şekeri) | Набат (кристалл кант) | Новвот
Parvarda | Parvarda (Özbek şekerlemesi) | Парварда (өзбек момпосуйу) | Парварда
Nishalda | Nişalda (Özbek tatlısı) | Нишалда (өзбек таттуусу) | Нишолло
Pashmak (cotton candy) | Pamuk şeker (peşmek) | Пашмак (кант жүнү) | Пашмак (қанди пахтагӣ)
Cake (cream) | Pasta (kremalı) | Торт (каймакты) | Торт (қаймоқӣ)
Cake (Napoleon) | Pasta (Napolyon) | Торт (Наполеон) | Торт (Наполеон)
Honey cake | Bal pastası | Бал торту | Торти асалӣ
Eclair | Ekler | Эклер | Эклер
Muffin | Muffin | Маффин | Маффин
Brownie | Brownie | Брауни | Брауни
Cheesecake | Cheesecake | Чизкейк | Чизкейк
Tiramisu | Tiramisu | Тирамису | Тирамису
Baklava | Baklava | Баклава | Пахлава
Pudding | Puding | Пудинг | Пудинг
Jelly | Jöle | Желе | Желе
Cream bun | Kremalı çörek | Каймактуу булочка | Булочкаи қаймоқдор
Sugar syrup | Şeker şurubu | Кант сиропу | Шарбати шакар
Cocoa powder | Kakao tozu | Какао порошогу | Хокаи какао
Maple syrup | Akçaağaç şurubu | Клён сиропу | Шарбати заранг
Gozinaki | Gozinaki (cevizli bal tatlısı) | Гозинаки | Гозинаки
Granola bar | Granola bar | Гранола батончиги | Батончики гранола
Rice cakes | Pirinç patlağı | Күрүч галеттери | Галетаи биринҷ
Crispbread | Gevrek ekmek | Хрустящий нан | Нони хруста
Water | Su | Суу | Об
Sparkling water | Maden suyu (gazlı) | Газдалган суу | Оби газдор
Tea (with lemon) | Çay (limonlu) | Чай (лимон менен) | Чой (бо лимӯ)
Tea (with milk, no sugar) | Sütlü çay (şekersiz) | Сүттүү чай (кантсыз) | Чойи ширӣ (бе шакар)
Tea (with 1 sugar cube) | Çay (1 küp şekerli) | Чай (1 кесек кант менен) | Чой (бо 1 пора шакар)
Tea (with honey) | Çay (ballı) | Чай (бал менен) | Чой (бо асал)
Tea (sweet, with 3 sugar cubes) | Çay (tatlı, 3 küp şekerli) | Чай (таттуу, 3 кесек кант менен) | Чой (ширин, бо 3 пора шакар)
Masala chai | Masala çayı | Масала чай | Чойи масала
Matcha latte | Matcha latte | Матча латте | Матча латте
Coffee (black, no sugar) | Kahve (sade, şekersiz) | Кофе (кара, кантсыз) | Қаҳва (сиёҳ, бе шакар)
Coffee (with sugar) | Kahve (şekerli) | Кофе (кант менен) | Қаҳва (бо шакар)
Coffee (with milk) | Sütlü kahve | Сүттүү кофе | Қаҳва бо шир
Cappuccino | Kapuçino | Капучино | Капучино
Latte | Latte | Латте | Латте
Espresso | Espresso | Эспрессо | Эспрессо
Americano | Americano | Американо | Американо
Mocha | Mocha | Мокко | Мокко
Coffee 3 in 1 | Kahve 3'ü 1 arada | Кофе 3 в 1 | Қаҳваи 3 дар 1
Flat white | Flat white | Флэт уайт | Флэт уайт
Hot chocolate | Sıcak çikolata | Ысык шоколад | Шоколади гарм
Cocoa (with milk) | Kakao (sütlü) | Какао (сүт менен) | Какао бо шир
Apple juice | Elma suyu | Алма ширеси | Шарбати себ
Grape juice | Üzüm suyu | Жүзүм ширеси | Шарбати ангур
Pomegranate juice | Nar suyu | Анар ширеси | Шарбати анор
Peach juice | Şeftali suyu | Шабдалы ширеси | Шарбати шафтолу
Tomato juice | Domates suyu | Помидор ширеси | Шарбати помидор
Carrot juice | Havuç suyu | Сабиз ширеси | Шарбати сабзӣ
Pineapple juice | Ananas suyu | Ананас ширеси | Шарбати ананас
Multifruit juice | Karışık meyve suyu | Мультифрукт ширеси | Шарбати мултифрукт
Lemonade | Limonata | Лимонад | Лимонад
Fanta | Fanta | Fanta | Fanta
Sprite | Sprite | Sprite | Sprite
Cola (sugar free) | Kola (şekersiz) | Кола (кантсыз) | Кола (бе шакар)
Soft drink | Gazlı içecek | Газдалган суусундук | Нӯшокии газдор
Energy drink | Enerji içeceği | Энергетикалык суусундук | Нӯшокии энергетикӣ
Compote | Komposto | Компот | Компот
Dried fruit compote | Kuru meyve komposto (hoşaf) | Кургак жемиш компоту (үзвар) | Компоти меваи хушк (шарбат)
Kissel | Kisel (meyve jölesi içeceği) | Кисель | Кисель
Kvass | Kvas | Квас | Квас
Berry fruit drink | Meyve suyu (böğürtlen, mors) | Жемиш сусундугу (морс) | Морс
Iced tea | Soğuk çay | Муздак чай | Чойи сард
Milkshake | Milkshake | Милкшейк | Милкшейк
Drinking yogurt | İçilebilir yoğurt | Ичүүчү йогурт | Йогурти нӯшиданӣ
Smoothie | Smoothie | Смузи | Смузи
Protein shake (ready-made) | Protein shake (hazır) | Протеин коктейли (даяр) | Коктейли протеин (тайёр)
Beer (light) | Bira (açık) | Сыра (ачык) | Пиво (равшан)
Beer (dark) | Bira (koyu) | Сыра (кара) | Пиво (тира)
Beer (non-alcoholic) | Bira (alkolsüz) | Сыра (алкоголсуз) | Пиво (бе спирт)
Wine (red) | Şarap (kırmızı) | Шарап (кызыл) | Шароб (сурх)
Wine (white) | Şarap (beyaz) | Шарап (ак) | Шароб (сафед)
Vodka | Votka | Арак | Арақ
Cognac | Konyak | Коньяк | Коняк
Whiskey | Viski | Виски | Виски
Champagne | Şampanya | Шампан | Шампан
Cider | Elma şarabı (sidr) | Сидр | Сидр
Boza | Boza | Боза | Боза
Coconut water | Hindistan cevizi suyu | Кокос суусу | Оби кокос
Soy milk | Soya sütü | Соя сүтү | Шири соя
Almond milk | Badem sütü | Бадам сүтү | Шири бодом
Oat milk | Yulaf sütü | Сулу сүтү | Шири овёс
Isotonic drink | İzotonik içecek | Изотоник суусундук | Нӯшокии изотонӣ
Mass gainer | Kilo aldırıcı (gainer) | Гейнер | Гейнер
Whey isolate | Whey izolat | Whey изолят | Изоляти whey
Casein | Kazein | Казеин | Казеин
Protein bar (low sugar) | Protein bar (az şekerli) | Протеин батончиги (кант аз) | Батончики протеин (шакар кам)
Protein cookie | Protein kurabiye | Протеин печеньеси | Кукии протеин
Energy gel | Enerji jeli | Энергетикалык гель | Гели энергетикӣ
Creatine | Kreatin | Креатин | Креатин
BCAA (amino acids) | BCAA (amino asitler) | BCAA (аминокислоталар) | BCAA (аминокислотаҳо)
"""
