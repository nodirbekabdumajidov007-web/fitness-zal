"""Turkish / Kyrgyz / Tajik UI text, part 6. Line: key||Turkish||Kyrgyz||Tajik (see gym/i18n.py)."""

RAW = """
ftr_auto||boşsa otomatik||бош болсо, автоматтык||агар холӣ бошад, худкор
ftr_resting_hr||İstirahat nabzı||Эс алуудагы пульс||Набзи истироҳат
ftr_bf_hint||Vücut yağı boşsa; cinsiyet, boy, bel ve boyundan (kadınlarda kalçadan) US Navy formülüyle tahmin edilir.||Дененин майы бош болсо, жынысы, бою, бели жана моюну (аялдарда жамбашы) боюнча US Navy формуласы менен болжолдонот.||Агар чарбуи бадан холӣ бошад, он аз рӯи ҷинс, қад, камар ва гардан (барои занон рон) бо формулаи US Navy тахмин карда мешавад.
ftr_err_range||Değer aralık dışında veya geçersiz||Маани чектен тышкары же жараксыз||Қимат берун аз ҳудуд ё нодуруст аст
ftr_err_date||Geçersiz tarih (gelecekte olamaz; hedef son tarihi gelecekte olmalı)||Дата жараксыз (келечекте болбошу керек; максаттын мөөнөтү келечекте болушу керек)||Санаи нодуруст (дар оянда набошад; муҳлати ҳадаф бояд дар оянда бошад)
ftr_err_notfound||Kayıt bulunamadı||Жазуу табылган жок||Сабт ёфт нашуд
ftr_err_set||Setleri kontrol edin: ad ve tekrar (1-100) gerekli, ağırlık 0-500 kg, RPE 1-10||Топтомдорду текшериңиз: ат жана кайталоо (1-100) керек, салмак 0-500 кг, RPE 1-10||Сетҳоро санҷед: ном ва такрор (1-100) лозим, вазн 0-500 кг, RPE 1-10
ftr_goals||Hedefler||Максаттар||Ҳадафҳо
ftr_goal||Hedef||Максат||Ҳадаф
ftr_no_goals||Henüz hedef yok.||Азырынча максат жок.||Ҳоло ҳадаф нест.
ftr_goal_nodata||Hedef belirlendi. İlerlemeyi görmek için bir ölçüm ekleyin.||Максат коюлду. Жыйынтыкты көрүү үчүн өлчөм кошуңуз.||Ҳадаф гузошта шуд. Барои дидани пешрафт андоза илова кунед.
ftr_set_goal||Hedef belirle||Максат коюу||Гузоштани ҳадаф
ftr_goal_type||Hedef türü||Максат түрү||Навъи ҳадаф
ftr_goal_metric||Ölçüt||Көрсөткүч||Нишондиҳанда
ftr_target||Hedef değer||Максаттуу маани||Қимати ҳадаф
ftr_deadline||Son tarih||Мөөнөтү||Муҳлат
ftr_remaining||Kalan||Калганы||Боқимонда
ftr_trend||Eğilim (son 4 hafta)||Тренд (акыркы 4 жума)||Равандаш (4 ҳафтаи охир)
ftr_week||hafta||жума||ҳафта
ftr_projected||Tahmini tarih||Болжолдуу дата||Санаи тахминӣ
ftr_state_nodata||Veri yok||Маалымат жок||Маълумот нест
ftr_state_reached||Ulaşıldı||Жетилди||Ба даст омад
ftr_state_on_track||Yolunda||Жолунда||Дар роҳи дуруст
ftr_state_off_track||Yoldan sapmış||Жолдон чыккан||Аз роҳ дур
ftr_state_no_trend||Eğilim için yeterli veri yok||Тренд үчүн маалымат жетишсиз||Барои раванд маълумот кофӣ нест
ftr_period||Dönem||Мезгил||Давра
ftr_p_1m||1 ay||1 ай||1 моҳ
ftr_p_3m||3 ay||3 ай||3 моҳ
ftr_p_6m||6 ay||6 ай||6 моҳ
ftr_p_1y||1 yıl||1 жыл||1 сол
ftr_p_all||Tümü||Баары||Ҳама
ftr_ma7||7 günlük ortalama||7 күндүк орточо||Миёнаи 7-рӯза
ftr_projection||Tahmin||Болжол||Пешбинӣ
ftr_measures||Vücut ölçüleri||Дене өлчөмдөрү||Андозаҳои бадан
ftr_strength||Güç (tahmini 1RM)||Күч (болжолдуу 1RM)||Қувват (1RM-и тахминӣ)
ftr_est1rm||Tahmini 1RM||Болжолдуу 1RM||1RM-и тахминӣ
ftr_volume||Haftalık hacim (kg x tekrar)||Жумалык көлөм (кг x кайталоо)||Ҳаҷми ҳафтаина (кг x такрор)
ftr_volume_short||Hacim||Көлөм||Ҳаҷм
ftr_activity||Haftalık aktivite||Жумалык активдүүлүк||Фаъолияти ҳафтаина
ftr_workouts||Antrenmanlar||Машыгуулар||Машқҳо
ftr_visits||Salon ziyaretleri||Зал визиттери||Ташрифҳо ба толор
ftr_calories||Kalori||Калория||Калория
ftr_adherence||Günlerin %{pct}'i hedefte ({n}/{total})||Күндөрдүн {pct}% максатта ({n}/{total})||{pct}% рӯзҳо дар ҳадаф ({n}/{total})
ftr_streak||Seri: {d} gün, {w} hafta||Серия: {d} күн, {w} жума||Силсила: {d} рӯз, {w} ҳафта
ftr_table||Tablo||Таблица||Ҷадвал
ftr_no_data||Bu dönem için veri yok||Бул мезгилге маалымат жок||Барои ин давра маълумот нест
ftr_date||Tarih||Дата||Сана
ftr_value||Ölçüt||Көрсөткүч||Нишондиҳанда
ftr_diff||Fark||Айырма||Тафовут
ftr_compare||Önce / sonra||Мурун / кийин||Пеш / баъд
ftr_before||Önce (tarih)||Мурун (дата)||Пеш (сана)
ftr_after||Sonra (tarih)||Кийин (дата)||Баъд (сана)
ftr_compare_go||Karşılaştır||Салыштыруу||Муқоиса кардан
ftr_pick_two||İki tarihi de seçin||Эки датаны тең тандаңыз||Ҳарду санаро интихоб кунед
ftr_enter_weight||Kilo girin||Салмак киргизиңиз||Вазнро ворид кунед
ftr_log_sets||Setleri kaydet||Топтомдорду жазуу||Сабти сетҳо
ftr_add_set||Set||Топтом||Сет
ftr_add_exercise||Egzersiz ekle||Көнүгүү кошуу||Илова кардани машқ
ftr_add_help||Bir egzersiz adı yazın (listeden seçin veya kendiniz yazın), sonra her set için tekrar ve ağırlığı girin.||Көнүгүүнүн атын териңиз (тизмеден тандаңыз же өзүңүз жазыңыз), анан ар бир топтом үчүн кайталоо жана салмакты киргизиңиз.||Номи машқро нависед (аз рӯйхат интихоб кунед ё худатон нависед), баъд барои ҳар сет такрор ва вазнро ворид кунед.
ftr_plan_day||Plan günü (isteğe bağlı)||План күнү (милдеттүү эмес)||Рӯзи нақша (ихтиёрӣ)
ftr_no_sessions||Henüz kayıtlı antrenman yok.||Азырынча машыгуу жазылган жок.||Ҳоло машқе сабт нашудааст.
ftr_session_saved||Antrenman kaydedildi||Машыгуу сакталды||Машқ захира шуд
ftr_pr_toast||Yeni kişisel rekor: {exercise} - tahmini 1RM {value} kg!||Жаңы жеке рекорд: {exercise} - болжолдуу 1RM {value} кг!||Рекорди нави шахсӣ: {exercise} - 1RM-и тахминӣ {value} кг!
ftr_readonly||salt okunur||окуу үчүн гана||танҳо барои хондан
sw_open||Yardım ve mesajları aç||Жардам жана билдирүүлөрдү ачуу||Кушодани кӯмак ва паёмҳо
sw_close||Kapat||Жабуу||Пӯшидан
sw_tab_home||Ana sayfa||Башкы||Асосӣ
sw_tab_msgs||Mesajlar||Билдирүүлөр||Паёмҳо
sw_tab_help||Yardım||Жардам||Кӯмак
sw_hello||Merhaba, {name}||Салам, {name}||Салом, {name}
sw_guest||misafir||конок||меҳмон
sw_title||Nasıl yardımcı olabiliriz?||Кантип жардам бере алабыз?||Чӣ тавр кӯмак карда метавонем?
sw_last||Son mesaj||Акыркы билдирүү||Паёми охирин
sw_send_us||Bize mesaj gönderin||Бизге билдирүү жөнөтүңүз||Ба мо паём фиристед
sw_find_help||Yardım ara||Жардам издөө||Ҷустуҷӯи кӯмак
sw_search_ph||Sorunuzu yazın||Суроону териңиз||Саволро нависед
sw_telegram||Telegram'dan bize yazın||Бизге Telegram аркылуу жазыңыз||Дар Telegram ба мо нависед
sw_just_now||az önce||азыр эле||ҳозир
sw_min_ago||{n} dk önce||{n} мүн мурун||{n} дақ пеш
sw_hour_ago||{n} sa önce||{n} саат мурун||{n} соат пеш
sw_day_ago||{n} gün önce||{n} күн мурун||{n} рӯз пеш
sw_you||Siz||Сиз||Шумо
sw_team||Fitnes Zal ekibi||Fitnes Zal командасы||Дастаи Fitnes Zal
sw_photo||Fotoğraf||Сүрөт||Акс
sw_msg_ph||Bir mesaj yazın...||Билдирүү жазыңыз...||Паём нависед...
sw_send||Gönder||Жөнөтүү||Фиристодан
sw_attach||Fotoğraf ekle||Сүрөт тиркөө||Замима кардани акс
sw_remove_photo||Fotoğrafı kaldır||Сүрөттү алып салуу||Бардоштани акс
sw_empty_thread||Henüz mesaj yok. Sorunuzu yazın, ekibimiz cevaplasın.||Азырынча билдирүү жок. Суроо жазыңыз, командабыз жооп берет.||Ҳоло паём нест. Саволро нависед, дастаи мо ҷавоб медиҳад.
sw_guest_intro||Size dönebilmemiz için adınızı ve telefonunuzu bırakın.||Сиз менен байланышуу үчүн атыңызды жана телефонуңузду калтырыңыз.||Номи худ ва телефонро гузоред, то бо шумо тамос гирем.
sw_name||Adınız||Атыңыз||Номи шумо
sw_phone||Telefon (90 123 45 67)||Телефон (90 123 45 67)||Телефон (90 123 45 67)
sw_email||E-posta||E-mail||E-mail
sw_email_opt||E-posta (isteğe bağlı)||E-mail (милдеттүү эмес)||E-mail (ихтиёрӣ)
sw_closed_note||Bu konuşma kapatıldı. Yeni bir mesaj onu yeniden açar.||Бул сүйлөшүү жабылган. Жаңы билдирүү аны кайра ачат.||Ин сӯҳбат баста шудааст. Паёми нав онро дубора мекушояд.
sw_err_net||Bağlantı sorunu. Lütfen tekrar deneyin.||Байланыш көйгөйү. Кайра аракет кылыңыз.||Мушкили пайвастшавӣ. Лутфан дубора кӯшиш кунед.
sw_err_contact||Adınızı ve geçerli bir telefon numarası girin.||Атыңызды жана жарактуу телефон номерин киргизиңиз.||Номи худ ва рақами телефони дурустро ворид кунед.
sw_err_email||E-posta adresi geçerli değil.||E-mail дареги жараксыз.||Суроғаи e-mail нодуруст аст.
sw_err_long||Mesaj çok uzun (en fazla 1000 karakter).||Билдирүү өтө узун (эң көбү 1000 белги).||Паём аз ҳад дароз аст (ҳадди аксар 1000 аломат).
sw_err_empty||Bir mesaj yazın veya fotoğraf ekleyin.||Билдирүү жазыңыз же сүрөт тиркеңиз.||Паём нависед ё акс замима кунед.
sw_err_notfound||Bulunamadı.||Табылган жок.||Ёфт нашуд.
sw_err_bad||Geçersiz istek.||Жараксыз өтүнүч.||Дархости нодуруст.
sw_help_hint||Bir soru yazın veya bir konu seçin||Суроо жазыңыз же теманы тандаңыз||Савол нависед ё мавзӯъро интихоб кунед
sw_results||Eşleşen makaleler||Дал келген макалалар||Мақолаҳои мувофиқ
sw_no_results||Hiçbir şey bulunamadı. Mesajlar bölümünden ekibimize yazın.||Эч нерсе табылган жок. «Билдирүүлөр» бөлүмүндө командабызга жазыңыз.||Ҳеҷ чиз ёфт нашуд. Дар бахши «Паёмҳо» ба дастаи мо нависед.
sw_ask_assistant||Asistan cevabı||Жардамчынын жообу||Ҷавоби ёвар
sw_assistant_says||Otomatik asistan||Автоматтык жардамчы||Ёвари худкор
sw_categories||Konular||Темалар||Мавзӯъҳо
sw_back||Geri||Артка||Бозгашт
sw_helpful||Bu yararlı oldu mu?||Бул пайдалуу болдубу?||Оё ин муфид буд?
sw_yes||Evet||Ооба||Бале
sw_no||Hayır||Жок||Не
sw_thanks||Geri bildiriminiz için teşekkürler!||Пикириңиз үчүн рахмат!||Барои фикри шумо ташаккур!
sw_voice||Sesle sor||Үн менен суроо||Бо овоз пурсед
sw_voice_sub||Sorunuzu söyleyin, asistan cevaplasın||Суроону айтыңыз, жардамчы жооп берет||Саволро бигӯед, ёвар ҷавоб медиҳад
sw_new_msgs||Yeni mesajlar||Жаңы билдирүүлөр||Паёмҳои нав
sw_sending||Gönderiliyor...||Жөнөтүлүүдө...||Фиристода мешавад...
sw_seen||Görüldü||Көрүлдү||Дида шуд
sw_status_open||Açık||Ачык||Кушода
sw_status_pending||Cevaplandı||Жооп берилди||Ҷавоб дода шуд
sw_status_closed||Kapalı||Жабык||Баста
sw_unread||Okunmamış mesajlar||Окулбаган билдирүүлөр||Паёмҳои нахонда
sw_loading||Yükleniyor...||Жүктөлүүдө...||Бор мешавад...
sw_retry||Tekrar dene||Кайра аракет||Дубора кӯшиш
sw_help_for_you||Faydalı makaleler||Пайдалуу макалалар||Мақолаҳои муфид
sw_notif_title||Fitnes Zal ekibinden yeni yanıt||Fitnes Zal командасынан жаңы жооп||Ҷавоби нав аз дастаи Fitnes Zal
sw_notif_photo||Bir fotoğraf aldınız||Сүрөт алдыңыз||Шумо акс гирифтед
sw_cat_general||Genel||Жалпы||Умумӣ
sw_cat_membership||Üyelik||Абонемент||Абонемент
sw_cat_payment||Ödemeler||Төлөмдөр||Пардохтҳо
sw_cat_classes||Dersler||Сабактар||Машғулиятҳо
sw_cat_shop||Mağaza||Дүкөн||Мағоза
sw_cat_account||Hesap||Аккаунт||Аккаунт
chat_months||Oca,Şub,Mar,Nis,May,Haz,Tem,Ağu,Eyl,Eki,Kas,Ara||янв,фев,мар,апр,май,июн,июл,авг,сен,окт,ноя,дек||янв,фев,мар,апр,май,июн,июл,авг,сен,окт,ноя,дек
chat_day_fmt||{d} {m}||{d} {m}||{d} {m}
chat_masked||Herkese açık odada kişisel bilgi paylaşmayın: özel sohbet kullanın. Telefon, kart veya e-posta gizlendi.||Жалпы бөлмөдө жеке маалыматты бөлүшпөңүз: жеке чатты колдонуңуз. Телефон, карта же e-mail жашырылды.||Дар ҳуҷраи умумӣ маълумоти шахсиро нагузоред: аз чати хусусӣ истифода баред. Телефон, корт ё e-mail пинҳон карда шуд.
chat_mention_title||{name} sohbette sizden bahsetti||{name} чатта сизди белгиледи||{name} шуморо дар чат ёдовар шуд
chat_reply_bad||Yanıtladığınız mesaj bulunamadı.||Жооп берип жаткан билдирүү табылган жок.||Паёме, ки ба он ҷавоб медиҳед, ёфт нашуд.
chat_bad_reaction||Bilinmeyen tepki.||Белгисиз реакция.||Реаксияи номаълум.
chat_edit_expired||Bir mesaj yalnızca 15 dakika içinde düzenlenebilir.||Билдирүүнү 15 мүнөттүн ичинде гана түзөтүүгө болот.||Паёмро танҳо дар давоми 15 дақиқа таҳрир кардан мумкин аст.
chat_reply||Yanıtla||Жооп берүү||Ҷавоб додан
chat_copy||Kopyala||Көчүрүү||Нусха бардоштан
chat_copied||Kopyalandı||Көчүрүлдү||Нусха бардошта шуд
chat_edit||Düzenle||Түзөтүү||Таҳрир
chat_edited||düzenlendi||түзөтүлдү||таҳрир шуд
chat_editing||Düzenleniyor||Түзөтүлүүдө||Таҳрир мешавад
chat_pin||Sabitle||Кадоо||Васл кардан
chat_unpin||Sabitlemeyi kaldır||Кадоону алуу||Бозкарди васл
chat_pinned||Sabitlenmiş mesaj||Кадалган билдирүү||Паёми васлшуда
chat_new_msgs||Yeni mesajlar||Жаңы билдирүүлөр||Паёмҳои нав
chat_to_bottom||Sonuncuya git||Акыркысына өтүү||Ба охирин гузаштан
chat_search_ph||Mesajlarda ara||Билдирүүлөрдөн издөө||Ҷустуҷӯ дар паёмҳо
chat_search_open||Ara||Издөө||Ҷустуҷӯ
chat_search_none||Hiçbir şey bulunamadı||Эчтеке табылган жок||Ҳеҷ чиз ёфт нашуд
chat_jump_fail||Mesaj bulunamadı||Билдирүү табылган жок||Паём ёфт нашуд
chat_members_n||{n} üye||{n} мүчө||{n} аъзо
chat_online_n||{n} çevrimiçi||{n} онлайн||{n} онлайн
chat_mute||Bildirimleri sessize al||Билдирмелерди өчүрүү||Хомӯш кардани огоҳиномаҳо
chat_unmute||Bildirimlerin sesini aç||Билдирмелерди күйгүзүү||Фаъол кардани огоҳиномаҳо
chat_react||Tepki ver||Реакция коюу||Реаксия додан
chat_reacted_by||Tepkiler||Реакциялар||Реаксияҳо
chat_menu||Mesaj işlemleri||Билдирүү аракеттери||Амалҳои паём
chat_replying||{name} kişisine yanıt veriliyor||{name} адамына жооп берилүүдө||Ҷавоб ба {name}
chat_close||Kapat||Жабуу||Пӯшидан
chat_more||Daha fazla||Дагы||Бештар
chat_mention_ph||Bir üye seçin||Мүчөнү тандаңыз||Аъзоро интихоб кунед
profile_saved||Profil bilgileri kaydedildi||Профиль маалыматтары сакталды||Маълумоти профил захира шуд
pw_changed||Şifre değiştirildi||Сырсөз өзгөртүлдү||Рамз тағйир дода шуд
pt_cancel_ok||Kişisel antrenman isteği iptal edildi||Жеке машыгуу өтүнүчү жокко чыгарылды||Дархости машқи шахсӣ бекор шуд
pt_confirmed_ok||Kişisel antrenman isteği onaylandı||Жеке машыгуу өтүнүчү ырасталды||Дархости машқи шахсӣ тасдиқ шуд
pt_declined_ok||Kişisel antrenman isteği reddedildi||Жеке машыгуу өтүнүчү четке кагылды||Дархости машқи шахсӣ рад шуд
body_saved||Ölçüm kaydedildi||Өлчөм сакталды||Андоза захира шуд
weight_saved||Bugünün kilosu güncellendi||Бүгүнкү салмак жаңыртылды||Вазни имрӯза навсозӣ шуд
goal_saved||Hedef kaydedildi||Максат сакталды||Ҳадаф захира шуд
ftr_goal_reached||🎯 Hedefe ulaşıldı! Tebrikler!||🎯 Максатка жетилди! Куттуктайбыз!||🎯 Ба ҳадаф расидед! Муборак!
sw_st_open||Şu an açık · cevap veriyoruz||Азыр ачык · жооп беребиз||Ҳозир кушода · ҷавоб медиҳем
sw_st_closed||Kapalı · {time} saatinden itibaren cevap veririz||Жабык · {time}ден баштап жооп беребиз||Баста · аз соати {time} ҷавоб медиҳем
sw_hours_ans||Salon her gün {hours} saatleri arasında açıktır.||Зал күн сайын {hours} иштейт.||Толор ҳар рӯз {hours} кушода аст.
sw_qa_label||Hızlı işlemler||Тез аракеттер||Амалҳои зуд
sw_qa_prices||Fiyatlar||Баалар||Нархҳо
sw_qa_hours||Çalışma saatleri||Иш убактысы||Соатҳои корӣ
sw_qa_member||Üyeliğim||Менин абонементим||Абонементи ман
sw_qa_coach||Antrenör asistanı||Машыктыруучу жардамчысы||Ёвари мураббӣ
sw_call||Bizi arayın||Бизге чалыңыз||Ба мо занг занед
sw_write||Yaz||Жазуу||Навиштан
nav_plans_short||Tarifeler||Тарифтер||Тарифҳо
app_link||Android uygulaması||Android тиркемеси||Барномаи Android
app_title||Fitnes Zal uygulaması||Fitnes Zal тиркемеси||Барномаи Fitnes Zal
app_sub||Üyelik, QR kart, program ve mağaza telefonunuzda: ana ekrandan tek dokunuşla açılır.||Абонемент, QR карта, расписание жана дүкөн телефонуңузда: башкы экрандан бир басуу менен ачылат.||Обуна, корти QR, ҷадвал ва мағоза дар телефони шумо: аз экрани асосӣ бо як ламс кушода мешавад.
app_btn||APK'yı indir||APK жүктөп алуу||APK-ро боргирӣ кунед
app_how||Nasıl kurulur||Кантип орнотуу керек||Чӣ тавр насб кардан
app_s1||“APK'yı indir” düğmesine dokunun.||«APK жүктөп алуу» баскычын басыңыз.||Тугмаи «APK-ро боргирӣ кунед»-ро пахш кунед.
app_s2||İndirilen dosyayı açın. Telefon sorarsa bu tarayıcıdan kuruluma izin verin.||Жүктөлгөн файлды ачыңыз. Телефон сураса, ушул браузерден орнотууга уруксат бериңиз.||Файли боргиришударо кушоед. Агар телефон пурсад, аз ин браузер насб карданро иҷозат диҳед.
app_s3||“Yükle”ye dokunun: uygulama ana ekranda görünür.||«Орнотуу» баскычын басыңыз: тиркеме башкы экранда пайда болот.||«Насб»-ро пахш кунед: барнома дар экрани асосӣ пайдо мешавад.
app_warn||Uygulama Google Play dışında dağıtıldığı için Android uyarı gösterebilir, bu normaldir. Dosyayı yalnızca bu sayfadan indirin.||Тиркеме Google Play'ден тышкары таратылгандыктан Android эскертүү көрсөтүшү мүмкүн, бул кадимки көрүнүш. Файлды ушул беттен гана жүктөп алыңыз.||Азбаски барнома берун аз Google Play паҳн мешавад, Android метавонад огоҳӣ нишон диҳад, ин муқаррарӣ аст. Файлро танҳо аз ҳамин саҳифа боргирӣ кунед.
app_ios||iPhone'da siteyi Safari'de açın, Paylaş → Ana Ekrana Ekle'yi seçin.||iPhone'до сайтты Safari'де ачып, «Бөлүшүү» → «Башкы экранга кошуу» тандаңыз.||Дар iPhone сайтро дар Safari кушоед ва «Мубодила» → «Ба экрани асосӣ илова кардан»-ро интихоб кунед.
app_soon||Uygulama dosyası yakında burada olacak.||Тиркеменин файлы жакында ушул жерде болот.||Файли барнома ба зудӣ дар ин ҷо хоҳад буд.
sw_ask_title||Asistana sorun||Жардамчыдан сураңыз||Аз ёвар пурсед
sw_ask_ph||örn. üyeliğimi nasıl dondururum?||мис. абонементимди кантип тоңдурам?||масалан, абонементамро чӣ тавр яхбандӣ мекунам?
sw_ask_go||Sor||Суроо||Пурсидан
sw_continue||Yardım bölümünde devam et||Жардам бөлүмүндө улантуу||Дар бахши «Кӯмак» идома додан
sw_ms_left||Üyelik: {n} gün kaldı||Абонемент: {n} күн калды||Абонемент: {n} рӯз монд
sw_ms_today||Üyelik bugün bitiyor||Абонемент бүгүн бүтөт||Абонемент имрӯз тамом мешавад
sw_ms_none||Aktif üyelik yok||Активдүү абонемент жок||Абонементи фаъол нест
sw_ms_extend||Uzat||Узартуу||Тамдид
sw_ms_buy||Seç||Тандоо||Интихоб
sw_online||Ekip çevrimiçi||Команда онлайн||Даста онлайн аст
sw_pg_title||Yardım merkezi||Жардам борбору||Маркази кӯмак
sw_pg_sub||Sorunuzu yazın, ekibimiz cevaplasın.||Суроону жазыңыз, командабыз жооп берет.||Саволро нависед, дастаи мо ҷавоб медиҳад.
sw_pg_chat||Ekiple sohbet||Команда менен чат||Чат бо даста
sw_pg_faq||Sık sorulan sorular||Көп берилүүчү суроолор||Саволҳои асосӣ
sw_pg_all||Tüm sorular||Бардык суроолор||Ҳамаи саволҳо
sw_pg_search||Sorularda ara||Суроолордон издөө||Ҷустуҷӯ дар саволҳо
sw_pg_widget_note||Bu, köşedeki yardım penceresiyle aynı konuşmadır.||Бул бурчтагы жардам терезеси менен бирдей сүйлөшүү.||Ин ҳамон сӯҳбат бо тирезаи кӯмак дар гӯшаи экран аст.
promo_eyebrow||Salonla tanışın||Зал менен таанышыңыз||Бо толор шинос шавед
promo_title||Salonumuzun içinde neler var?||Залыбыздын ичинде эмне бар?||Дар толори мо чӣ ҳаст?
promo_play||Videoyu oynat||Видеону ойнотуу||Пахши видео
theme_to_dark||Koyu temaya geç||Караңгы темага өтүү||Гузаштан ба мавзӯи торик
theme_to_light||Açık temaya geç||Жарык темага өтүү||Гузаштан ба мавзӯи равшан
ec_tab||E-posta koduyla giriş||E-mail коду менен кирүү||Воридшавӣ бо рамзи e-mail
ec_title||E-postayla gelen kodla giriş||E-mailге келген код менен кирүү||Воридшавӣ бо рамзи e-mail
ec_help||E-postanızı (veya kullanıcı adınızı) girin, hesabın gelen kutusuna 6 haneli bir kod gönderelim. Şifre gerekmez.||E-mailиңизди (же колдонуучу атыңызды) киргизиңиз, аккаунттун кутусуна 6 сандуу код жөнөтөбүз. Сырсөз керек эмес.||E-mail (ё номи корбар)-ро ворид кунед, мо ба қуттии паёми аккаунт рамзи 6-рақамӣ мефиристем. Рамз лозим нест.
ec_login_label||E-posta veya kullanıcı adı||E-mail же колдонуучу аты||E-mail ё номи корбар
ec_send||Kodu gönder||Кодду жөнөтүү||Фиристодани рамз
ec_code_title||E-postanıza gelen kod||E-mailге келген код||Рамзи омада ба e-mail
ec_code_help||Böyle bir hesap varsa gelen kutusuna bir kod gönderildi (10 dakika geçerli). Spam klasörünü de kontrol edin.||Мындай аккаунт болсо, анын кутусуна код жөнөтүлдү (10 мүнөт жарактуу). «Спам» папкасын да текшериңиз.||Агар чунин аккаунт мавҷуд бошад, ба қуттии он рамз фиристода шуд (10 дақиқа эътибор дорад). Папкаи «Спам»-ро низ санҷед.
ec_code_help_to||Doğrulama kodu şu adrese gönderildi:||Ырастоо коду төмөнкү дарекке жөнөтүлдү:||Рамзи тасдиқ ба ин суроға фиристода шуд:
ec_code_label||6 haneli kod||6 сандуу код||Рамзи 6-рақамӣ
ec_bad||Kod yanlış veya süresi dolmuş.||Код туура эмес же мөөнөтү бүткөн.||Рамз нодуруст ё муҳлати он гузаштааст.
ec_locked||Çok fazla deneme. Yeni bir kod isteyin.||Аракеттер түгөндү. Жаңы код сураңыз.||Кӯшишҳо тамом шуданд. Рамзи навро дархост кунед.
ec_wait||Tekrar göndermeden önce biraz bekleyin (60 saniye).||Кайра жөнөтүүдөн мурун бир аз күтүңүз (60 секунд).||Пеш аз фиристодани дубора каме интизор шавед (60 сония).
ec_resent||Kod tekrar gönderildi (hesap varsa).||Код кайра жөнөтүлдү (аккаунт бар болсо).||Рамз дубора фиристода шуд (агар аккаунт мавҷуд бошад).
ec_subject||Fitnes Zal: giriş kodunuz {code}||Fitnes Zal: кирүү кодуңуз {code}||Fitnes Zal: рамзи воридшавии шумо {code}
ec_mail_title||Giriş kodu||Кирүү коду||Рамзи воридшавӣ
ec_mail_intro||{gym} hesabınıza giriş yapmak için bu kodu kullanın:||{gym} аккаунтуна кирүү үчүн ушул кодду колдонуңуз:||Барои ворид шудан ба аккаунти {gym} ин рамзро истифода баред:
ec_mail_valid||Kod {minutes} dakika geçerlidir ve yalnızca bir kez kullanılır.||Код {minutes} мүнөт жарактуу жана бир жолу гана колдонулат.||Рамз {minutes} дақиқа эътибор дорад ва танҳо як маротиба истифода мешавад.
ec_mail_secret||Bu kodu kimseyle paylaşmayın.||Бул кодду эч кимге айтпаңыз.||Ин рамзро ба ҳеҷ кас нагӯед.
ec_mail_ignore||Bunu siz istemediyseniz bu e-postayı yok sayın: hesabınıza kimse giremez.||Муну сиз сурабаган болсоңуз, бул катты эске албаңыз: аккаунтуңузга эч ким кире албайт.||Агар шумо инро дархост накарда бошед, ин мактубро нодида гиред: ба аккаунти шумо ҳеҷ кас даромада наметавонад.
ec_2fa_label||Girişte e-posta doğrulama kodu||Кирүүдө e-mail ырастоо коду||Рамзи тасдиқи e-mail ҳангоми воридшавӣ
ec_2fa_help||Açıkken, doğru şifreden (veya Google'dan) sonra bile e-postanızdan gelen 6 haneli kod gerekir.||Күйгүзүлгөндө, туура сырсөздөн (же Googleдан) кийин да e-mailден келген 6 сандуу код талап кылынат.||Агар фаъол бошад, ҳатто баъд аз рамзи дуруст (ё Google) рамзи 6-рақамӣ аз e-mail лозим мешавад.
ec_2fa_staff||Personel için önerilir: yönetici hesabının korumasını güçlendirir.||Кызматкерлер үчүн сунушталат: администратор аккаунтунун коргоосун күчөтөт.||Барои кормандон тавсия мешавад: ҳифзи аккаунти администраторро қавӣ мекунад.
legal_notice||Resmî metin Özbekçedir; kolaylık için Özbekçe gösterilmektedir.||Расмий текст өзбек тилинде; ыңгайлуулук үчүн өзбекче көрсөтүлдү.||Матни расмӣ бо забони ӯзбекӣ аст; барои роҳатӣ бо ӯзбекӣ нишон дода мешавад.
legal_notice_ru||Resmî metin Özbekçedir; kolaylık için Rusça sürüm gösterilmektedir.||Расмий текст өзбек тилинде; ыңгайлуулук үчүн орусча версия көрсөтүлдү.||Матни расмӣ бо забони ӯзбекӣ аст; барои роҳатӣ нусхаи русӣ нишон дода мешавад.
reset_mail_hello||Merhaba {name},||Саламатсызбы, {name}!||Салом, {name}!
reset_mail_asked||Fitnes Zal sitesinde şifre sıfırlama istendi (kullanıcı adı: {login}).||Fitnes Zal сайтында сырсөздү калыбына келтирүү суралды (логин: {login}).||Дар сайти Fitnes Zal барқарор кардани рамз дархост шуд (логин: {login}).
reset_mail_open||Yeni şifre belirlemek için aşağıdaki bağlantıyı açın (3 saat geçerli):||Жаңы сырсөз коюу үчүн төмөнкү шилтемени ачыңыз (3 саат жарактуу):||Барои таъини рамзи нав пайванди зеринро кушоед (3 соат эътибор дорад):
reset_mail_ignore||Bunu siz istemediyseniz bu e-postayı yok sayın: şifreniz değişmeyecek.||Муну сиз сурабаган болсоңуз, катты эске албаңыз: сырсөзүңүз өзгөрбөйт.||Агар шумо инро дархост накарда бошед, ин мактубро нодида гиред: рамзи шумо тағйир намеёбад.
reset_subject||Fitnes Zal: şifre sıfırlama||Fitnes Zal: сырсөздү калыбына келтирүү||Fitnes Zal: барқарор кардани рамз
scan_session||Oturum sona erdi: sayfayı yenileyin ve yönetici olarak tekrar giriş yapın||Сессия бүттү: баракты жаңыртып, администратор катары кайра кириңиз||Ҷаласа анҷом ёфт: саҳифаро навсозӣ карда, ҳамчун администратор дубора ворид шавед
"""
