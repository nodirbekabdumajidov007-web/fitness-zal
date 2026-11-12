"""Turkish / Kyrgyz / Tajik UI text, part 5. Line: key||Turkish||Kyrgyz||Tajik (see gym/i18n.py)."""

RAW = """
cal_f_limit||En fazla 200 kendi yiyeceğinizi saklayabilirsiniz||200гө чейин өз тамагыңызды сактай аласыз||То 200 хӯроки худро нигоҳ дошта метавонед
cal_my||Yiyeceklerim||Менин тамактарым||Хӯрокҳои ман
cal_my_empty||Henüz kendi yiyeceğiniz yok. Arama bir şey bulamazsa ekleyin.||Азырынча өз тамагыңыз жок. Издөө таппаса, кошуңуз.||Ҳоло хӯроки худатон нест. Агар ҷустуҷӯ чизеро наёбад, илова кунед.
cal_edit||Düzenle||Түзөтүү||Таҳрир
cal_quick||Hızlı ekle (kaydedilmez)||Тез кошуу (сакталбайт)||Зуд илова кардан (захира намешавад)
cal_quick_hint||Yalnızca bir ad ve girdiğiniz miktarın kalorisi. Bir sonraki sefer için saklanmaz.||Аты жана киргизген санга ылайык калория гана. Кийинки жолу үчүн сакталбайт.||Танҳо ном ва калорияи миқдори ворид кардаатон. Барои дафъаи оянда нигоҳ дошта намешавад.
cal_confirm_del||Bu yiyecek silinsin mi?||Бул тамак өчүрүлсүнбү?||Ин хӯрок нест карда шавад?
tl_save||Sonucu kaydet||Жыйынтыкты сактоо||Захира кардани натиҷа
tl_save_help||Kilonuz ve boyunuz bugünün ölçümü olarak kaydedilir, seçilen hedef profilinize gider.||Салмагыңыз менен бойуңуз бүгүнкү өлчөм катары сакталат, тандалган максат профилге барат.||Вазн ва қади шумо ҳамчун андозаи имрӯз захира мешавад ва ҳадафи интихобшуда ба профил меравад.
tl_save_login||Kaydetmek için giriş yapın||Сактоо үчүн кириңиз||Барои захира кардан ворид шавед
tl_save_bad||Geçerli bir kilo (30–250 kg) ve boy (120–230 cm) girin||Жарактуу салмак (30–250 кг) жана бой (120–230 см) киргизиңиз||Вазни дуруст (30–250 кг) ва қади дуруст (120–230 см) ворид кунед
tl_saved_new||Kaydedildi: bugünün ölçümü profilinize eklendi||Сакталды: бүгүнкү өлчөм профилиңизге кошулду||Захира шуд: андозаи имрӯза ба профили шумо илова шуд
tl_saved_upd||Güncellendi: bugünün ölçümü değiştirildi||Жаңыртылды: бүгүнкү өлчөм өзгөртүлдү||Навсозӣ шуд: андозаи имрӯза тағйир дода шуд
ms_title||Üyeliğim||Менин абонементим||Абонементи ман
renew_btn||Yenile||Узартуу||Тамдид
renew_note||Seçili üyeliği burada yenileyin: ödeme yöntemini seçin ve Yenile'ye basın.||Тандалган абонементти ушул жерден узартыңыз: төлөм ыкмасын тандап, «Узартуу» баскычын басыңыз.||Абонементи интихобшударо дар ин ҷо тамдид кунед: усули пардохтро интихоб карда, «Тамдид»-ро пахш кунед.
welcome_disc||Davet edilen arkadaş olarak ilk üyeliğinizde otomatik %{pct} indirim alırsınız.||Чакырылган дос катары биринчи абонементиңизге автоматтык түрдө {pct}% арзандатуу аласыз.||Ҳамчун дӯсти даъватшуда шумо ба абонементи аввалини худ худкор {pct}% тахфиф мегиред.
freeze_off||Dondurma kapalı.||Тоңдуруу өчүрүлгөн.||Яхбандӣ хомӯш аст.
freeze_no_member||Dondurmak için aktif bir üyelik gerekir.||Тоңдуруу үчүн активдүү абонемент керек.||Барои яхбандӣ абонементи фаъол лозим аст.
freeze_busy||Bir dondurma zaten aktif veya planlanmış.||Тоңдуруу мурунтан эле активдүү же пландалган.||Яхбандӣ аллакай фаъол ё ба нақша гирифта шудааст.
freeze_none_left||Bu üyelik için dondurma günü kalmadı.||Бул абонемент үчүн тоңдуруу күндөрү калган жок.||Барои ин абонемент рӯзҳои яхбандӣ намондааст.
freeze_bad_date||Yanlış tarih: bugün ile üyelik bitişi arasında bir gün seçin.||Дата туура эмес: бүгүн менен абонемент бүтүшүнүн ортосунан күн тандаңыз.||Санаи нодуруст: рӯзеро байни имрӯз ва анҷоми абонемент интихоб кунед.
freeze_min||Dondurma en az {min} gün olmalı.||Тоңдуруу кеминде {min} күн болушу керек.||Яхбандӣ бояд ақаллан {min} рӯз бошад.
freeze_too_long||Bu üyelikte {left} gün daha dondurabilirsiniz.||Бул абонементте дагы {left} күн тоңдура аласыз.||Дар ин абонемент боз {left} рӯз яхбандӣ карда метавонед.
freeze_rules||Her seferinde en az {min} gün, üyelik başına en fazla {max} gün. Bitiş tarihi aynı miktarda kayar; dondurulmuşken giriş yapamazsınız.||Бир жолу кеминде {min} күн, абонемент боюнча эң көбү {max} күн. Бүтүү күнү ошончого жылат; тоңдурулганда кире албайсыз.||Ҳар дафъа ақаллан {min} рӯз, барои як абонемент то {max} рӯз. Санаи анҷом ба ҳамон қадар мегузарад; ҳангоми яхбандӣ даромада наметавонед.
freeze_used_left||Kullanılan: {used} gün, kalan: {left} gün||Колдонулган: {used} күн, калган: {left} күн||Истифода шуд: {used} рӯз, боқимонда: {left} рӯз
freeze_active_now||Üyelik donduruldu. {until} tarihinde geri dönüyorsunuz.||Абонемент тоңдурулган. {until} күнү кайтасыз.||Абонемент яхбандӣ шудааст. Шумо дар {until} бармегардед.
freeze_scheduled||Dondurma planlandı: {start} – {until}.||Тоңдуруу пландалды: {start} – {until}.||Яхбандӣ ба нақша гирифта шуд: аз {start} то {until}.
unfreeze_btn||Dondurmayı bitir||Тоңдурууну бүтүрүү||Анҷоми яхбандӣ
freeze_cancel_btn||Planlanan dondurmayı iptal et||Пландалган тоңдурууну жокко чыгаруу||Бекор кардани яхбандии ба нақша гирифташуда
freeze_start||Başlangıç tarihi||Башталыш датасы||Санаи оғоз
freeze_end||Bitiş tarihi||Бүтүү датасы||Санаи анҷом
freeze_ok_future||Dondurma {date} – {until} için planlandı.||Тоңдуруу {date} – {until} аралыгына пландалды.||Яхбандӣ аз {date} то {until} ба нақша гирифта шуд.
unfreeze_ok||Dondurma bitti. {n} kullanılmayan gün iade edildi.||Тоңдуруу бүттү. Колдонулбаган {n} күн кайтарылды.||Яхбандӣ анҷом ёфт. {n} рӯзи истифоданашуда баргардонида шуд.
unfreeze_none||Bitirilecek bir dondurma yok.||Бүтүрүүгө тоңдуруу жок.||Яхбандие барои анҷом додан нест.
scan_frozen||Üyelik donduruldu: {date} tarihine kadar giriş kapalı||Абонемент тоңдурулган: {date} чейин кирүү жабык||Абонемент яхбандӣ шудааст: то {date} воридшавӣ баста аст
rem_title||Üyeliğiniz {days} gün sonra bitiyor||Абонементиңиз {days} күндөн кийин бүтөт||Абонементи шумо баъди {days} рӯз тамом мешавад
rem_title_today||Üyeliğiniz bugün bitiyor||Абонементиңиз бүгүн бүтөт||Абонементи шумо имрӯз тамом мешавад
rem_body||«{plan}» üyeliğiniz {date} tarihinde bitiyor. Tek tıkla yenileyin: {link}||«{plan}» абонементиңиз {date} бүтөт. Бир басуу менен узартыңыз: {link}||Абонементи «{plan}»-и шумо дар {date} тамом мешавад. Бо як пахш тамдид кунед: {link}
gp_title||Misafir davetiyesi||Конок чакыруусу||Даъватномаи меҳмон
gp_help||Kalan davetiye: {left} / {total}. Arkadaşınızın adını ve bir tarih girin, sonra bağlantıyı ona gönderin.||Калган чакыруу: {left} / {total}. Досуңуздун атын жана күндү киргизип, шилтемени ага жөнөтүңүз.||Даъватномаҳои боқимонда: {left} / {total}. Номи дӯст ва санаро ворид карда, пайвандро ба ӯ фиристед.
gp_name_label||Arkadaşın adı||Достун аты||Номи дӯст
gp_date||Tarih||Дата||Сана
gp_create||Davetiye oluştur||Чакыруу түзүү||Эҷоди даъватнома
gp_not_in_plan||Üyeliğinizde misafir davetiyesi yok.||Абонементиңизде конок чакыруусу жок.||Абонементи шумо даъватномаи меҳмон надорад.
gp_link||Bağlantı||Шилтеме||Пайванд
gp_state_valid||Geçerli||Жарактуу||Эътибор дорад
gp_state_today||Bugün geçerli||Бүгүн жарактуу||Имрӯз эътибор дорад
gp_state_used||Kullanıldı||Колдонулду||Истифода шуд
gp_state_expired||Süresi doldu||Мөөнөтү бүттү||Муҳлаташ гузашт
gp_state_cancelled||İptal edildi||Жокко чыгарылды||Бекор шуд
gp_invited_by||{name} sizi salona davet ediyor||{name} сизди залга чакырат||{name} шуморо ба толор даъват мекунад
gp_show_desk||QR kodu resepsiyonda gösterin. Bir kez geçerlidir.||QR кодду кабыл алууда көрсөтүңүз. Бир жолу гана иштейт.||QR-кодро дар қабулгоҳ нишон диҳед. Он як маротиба амал мекунад.
gp_guest||Misafir||Конок||Меҳмон
gp_host||Davet eden||Чакырган||Даъваткунанда
gp_created||Davetiye oluşturuldu. Bağlantıyı arkadaşınıza gönderin.||Чакыруу түзүлдү. Шилтемени досуңузга жөнөтүңүз.||Даъватнома эҷод шуд. Пайвандро ба дӯстатон фиристед.
gp_cancelled_ok||Davetiye iptal edildi.||Чакыруу жокко чыгарылды.||Даъватнома бекор шуд.
gp_no_member||Misafir davetiyesi için aktif bir üyelik gerekir.||Конок чакыруусу үчүн активдүү абонемент керек.||Барои даъватномаи меҳмон абонементи фаъол лозим аст.
gp_none_left||Bu üyelikte misafir davetiyesi kalmadı.||Бул абонементте конок чакыруусу калган жок.||Дар ин абонемент даъватномаи меҳмон намондааст.
gp_name||Arkadaşınızın adını girin.||Достуңуздун атын киргизиңиз.||Номи дӯстатонро ворид кунед.
gp_bad_date||Yanlış tarih: bugün ile üyelik bitişi arasında seçin.||Дата туура эмес: бүгүн менен абонемент бүтүшүнүн ортосунан тандаңыз.||Санаи нодуруст: байни имрӯз ва анҷоми абонемент интихоб кунед.
gp_cancelled||Davetiye iptal edilmişti||Чакыруу жокко чыгарылган||Даъватнома бекор шуда буд
gp_used||Davetiye zaten kullanıldı||Чакыруу мурун колдонулган||Даъватнома қаблан истифода шудааст
gp_expired||Davetiyenin süresi doldu||Чакыруунун мөөнөтү бүткөн||Муҳлати даъватнома гузаштааст
gp_early||Davetiye daha ileri bir tarih için||Чакыруу кийинки датага арналган||Даъватнома барои санаи баъдтар аст
gp_owner_out||Davet eden üyenin üyeliği şu an aktif değil||Чакырган мүчөнүн абонементи азыр активдүү эмес||Абонементи аъзои даъваткунанда ҳоло фаъол нест
gp_ok||Misafir girişi kaydedildi||Конок кирүүсү катталды||Воридшавии меҳмон сабт шуд
gp_guest_of||{name} misafiri||{name} коногу||Меҳмони {name}
ref_earned||Kazanılan bonus: {days} gün||Алынган бонус: {days} күн||Бонуси ба даст омада: {days} рӯз
ref_reward_title||Arkadaşınız katıldı: +{days} gün||Досуңуз кошулду: +{days} күн||Дӯстатон ҳамроҳ шуд: +{days} рӯз
ref_reward_body||{name} bağlantınızla ilk üyeliğini aldı. {days} bonus gün eklendi.||{name} шилтемеңиз аркылуу биринчи абонементин алды. {days} бонус күн кошулду.||{name} бо пайванди шумо абонементи аввалини худро гирифт. {days} рӯзи бонус илова шуд.
book_limited||30 günde {n} dersi kaçırdınız, bu yüzden aynı anda yalnızca 1 rezervasyon tutabilirsiniz.||30 күндө {n} сабакты калтырдыңыз, ошондуктан бир эле учурда 1 гана брондоо кармай аласыз.||Шумо дар 30 рӯз {n} машғулиятро аз даст додед, бинобар ин як вақт танҳо 1 брон дошта метавонед.
noshow_limited||30 günde {n} no-show: şimdilik aynı anda yalnızca 1 rezervasyon. Sınır kendiliğinden kalkar.||30 күндө {n} no-show: азырынча бир эле учурда 1 гана брондоо. Чектөө өзү алынат.||{n} no-show дар 30 рӯз: ҳоло як вақт танҳо 1 брон. Маҳдудият худ бардошта мешавад.
cancel_late||İptal edilemez: derse {hours} saatten az kaldı.||Жокко чыгаруу мүмкүн эмес: сабакка {hours} сааттан аз калды.||Бекор кардан мумкин нест: то машғулият камтар аз {hours} соат монд.
cancel_late_hint||Başlangıçtan en geç {hours} saat önce iptal edin||Башталганга чейин {hours} саатка чейин жокко чыгарыңыз||То {hours} соат пеш аз оғоз бекор кунед
wl_join||Bekleme listesine katıl||Күтүү тизмесине кошулуу||Ба рӯйхати интизорӣ ворид шудан
wl_leave||Bekleme listesinden ayrıl||Күтүү тизмесинен чыгуу||Аз рӯйхати интизорӣ баромадан
wl_pos||Bekleme listesi: #{n}||Күтүү тизмеси: #{n}||Рӯйхати интизорӣ: №{n}
wl_waiting_n||Bekleyen: {n}||Күткөндөр: {n}||Мунтазир: {n}
wl_joined||Bekleme listesindesiniz: #{n}. Yer boşaldığında otomatik olarak kaydedileceksiniz.||Күтүү тизмесиндесиз: #{n}. Орун бошогондо автоматтык түрдө жазыласыз.||Шумо дар рӯйхати интизорӣ ҳастед: №{n}. Вақте ҷой холӣ шавад, худкор сабт мешавед.
wl_left||Bekleme listesinden ayrıldınız.||Күтүү тизмесинен чыктыңыз.||Шумо аз рӯйхати интизорӣ баромадед.
wl_seats||Yer var: doğrudan yer ayırtın.||Орун бар: түз жазылыңыз.||Ҷой ҳаст: бевосита ном нависед.
wl_booked_title||Sıra sizde: yer ayrıldı||Кезек сизде: орун брондолду||Навбати шумо: ҷой сабт шуд
wl_booked_body||«{name}», {date} saat {time}. Dersler sayfasından iptal edebilirsiniz.||«{name}», {date} саат {time}. Сабактар бетинен жокко чыгара аласыз.||«{name}», {date} соати {time}. Дар саҳифаи «Машғулиятҳо» бекор карда метавонед.
dc_title||Bugünkü dersler: kim geldi||Бүгүнкү сабактар: ким келди||Машғулиятҳои имрӯз: кӣ омад
dc_came||Geldi||Келди||Омад
dc_noshow||No-show||No-show||No-show
dc_not_started||Ders henüz başlamadı||Сабак азырынча башталган жок||Машғулият ҳанӯз оғоз нашудааст
cal_title||Takvime ekle||Календарга кошуу||Ба тақвим илова кардан
cal_help||Kişisel bağlantıya abone olun, ayırttığınız dersler telefonunuzun takviminde görünsün. Bağlantıyı paylaşmayın.||Жеке шилтемеге жазылыңыз, брондогон сабактар телефонуңуздун календарында көрүнөт. Шилтемени бөлүшпөңүз.||Ба пайванди шахсӣ обуна шавед, машғулиятҳои бронкардаатон дар тақвими телефон пайдо мешаванд. Пайвандро ба каси дигар надиҳед.
cal_reset||Bağlantıyı sıfırla (eskisi çalışmaz)||Шилтемени баштапкы абалга келтирүү (эскиси иштебей калат)||Барқарор кардани пайванд (пайванди кӯҳна кор намекунад)
cal_reset_ok||Takvim bağlantısı sıfırlandı.||Календарь шилтемеси баштапкы абалга келтирилди.||Пайванди тақвим барқарор карда шуд.
tr_reviews||Antrenör puanları||Машыктыруучунун баалары||Баҳои мураббиён
tr_rate_label||Puan||Баа||Баҳо
tr_comment||Yorumunuz (isteğe bağlı)||Пикириңиз (милдеттүү эмес)||Фикри шумо (ихтиёрӣ)
tr_rate_send||Puanla||Баа коюу||Баҳо додан
tr_rate_edit||Puanı güncelle||Бааны жаңыртуу||Навсозии баҳо
tr_rate_only_trained||Yalnızca bu antrenörle çalışan veya dersine katılan üyeler puan verebilir.||Бул машыктыруучу менен машыккан же анын сабагына катышкан мүчөлөр гана баа бере алат.||Танҳо аъзоёне, ки бо ин мураббӣ машқ кардаанд ё ба машғулияти ӯ омадаанд, баҳо дода метавонанд.
tr_rate_bad||Puan 1 ile 5 arasında olmalı.||Баа 1ден 5ке чейин болушу керек.||Баҳо бояд аз 1 то 5 бошад.
tr_rate_not_allowed||Puan vermek için bu antrenörle tamamlanmış bir seans veya ders gerekir.||Баа берүү үчүн бул машыктыруучу менен аякталган сеанс же сабак болушу керек.||Барои баҳо додан бо ин мураббӣ сеанс ё машғулияти анҷомёфта лозим аст.
tr_rate_ok||Teşekkürler! Puanınız kaydedildi.||Рахмат! Бааңыз сакталды.||Ташаккур! Баҳои шумо захира шуд.
wk_streak||Haftalık seri (haftada 2+ ziyaret)||Жумалык серия (жумасына 2+ визит)||Силсилаи ҳафтаина (ҳафтае 2+ ташриф)
wk_this||Bu hafta: {done} / {need}||Бул жума: {done} / {need}||Ин ҳафта: {done} / {need}
board_on||Aylık liderlik tablosundasınız (ad ve soyadın baş harfi gösterilir).||Сиз айлык лидерборддосуз (аты жана фамилиянын биринчи тамгасы көрсөтүлөт).||Шумо дар ҷадвали пешсафони моҳона ҳастед (ном ва ҳарфи аввали насаб нишон дода мешавад).
board_off||Liderlik tablosu isteğe bağlıdır: katılana kadar gizli kalırsınız.||Лидерборд ыктыярдуу: кошулмайынча жашыруун каласыз.||Ҷадвали пешсафон ихтиёрӣ аст: то ҳамроҳ нашавед, пинҳон мемонед.
board_join||Liderlik tablosuna katıl||Лидербордго кошулуу||Ба ҷадвали пешсафон ҳамроҳ шудан
board_leave||Liderlik tablosundan ayrıl||Лидербордтон чыгуу||Аз ҷадвали пешсафон баромадан
board_joined||Liderlik tablosuna katıldınız.||Лидербордго кошулдуңуз.||Шумо ба ҷадвали пешсафон ҳамроҳ шудед.
board_left||Liderlik tablosundan ayrıldınız.||Лидербордтон чыктыңыз.||Шумо аз ҷадвали пешсафон баромадед.
gift_title||Hediye çeki||Белек сертификаты||Сертификати тӯҳфа
gift_sub||Bir üyelik veya tutar hediye edin||Абонемент же сумма белек кылыңыз||Абонемент ё маблағ тӯҳфа кунед
gift_buy_title||Çek satın al||Сертификат сатып алуу||Харидани сертификат
gift_buy_help||Bir üyelik veya {min} ile {max} UZS arasında bir tutar seçin. Kod bir kez geçerlidir ve 1 yıl sürer. Üyelik fiyatını aşarsa kalan iade edilmez.||Абонемент же {min}ден {max} UZSге чейинки сумманы тандаңыз. Код бир жолу иштейт жана 1 жыл жарактуу. Абонемент баасынан ашса, калганы кайтарылбайт.||Абонемент ё маблағро аз {min} то {max} UZS интихоб кунед. Код як маротиба амал мекунад ва 1 сол эътибор дорад. Агар аз нархи абонемент зиёд бошад, боқимонда баргардонида намешавад.
gift_for_plan||Bir üyelik için||Абонемент үчүн||Барои абонемент
gift_or_amount||veya bir tutar girin||же сумманы киргизиңиз||ё маблағ ворид кунед
gift_amount_label||Tutar (UZS)||Сумма (UZS)||Маблағ (UZS)
gift_redeem_title||Kodu kullan||Кодду колдонуу||Истифодаи рамз
gift_code||Hediye kodu||Белек коду||Рамзи тӯҳфа
gift_redeem_btn||Kullan||Колдонуу||Истифода бурдан
gift_mine||Satın aldığım çekler||Мен сатып алган сертификаттар||Сертификатҳои харидаи ман
gift_until||şu tarihe kadar geçerli||чейин жарактуу||то ин сана эътибор дорад
gift_state_valid||Geçerli||Жарактуу||Эътибор дорад
gift_state_unpaid||Ödeme bekleniyor||Төлөм күтүлүүдө||Мунтазири пардохт
gift_state_redeemed||Kullanıldı||Колдонулду||Истифода шуд
gift_state_expired||Süresi doldu||Мөөнөтү бүттү||Муҳлаташ гузашт
gift_pay||Hediye çeki||Белек сертификаты||Сертификати тӯҳфа
gift_amount||İzin verilen aralıkta bir tutar girin veya bir üyelik seçin.||Уруксат берилген чекте сумма киргизиңиз же абонемент тандаңыз.||Маблағро дар ҳудуди иҷозатдодашуда ворид кунед ё абонемент интихоб намоед.
gift_bad||Çek kodu bulunamadı||Сертификат коду табылган жок||Рамзи сертификат ёфт нашуд
gift_used||Çek zaten kullanıldı||Сертификат мурун колдонулган||Сертификат қаблан истифода шудааст
gift_expired||Çekin süresi doldu||Сертификаттын мөөнөтү бүткөн||Муҳлати сертификат гузаштааст
gift_unpaid||Çekin ödemesi henüz onaylanmadı||Сертификаттын төлөмү азырынча ырасталган жок||Пардохти сертификат ҳанӯз тасдиқ нашудааст
gift_plan||Bu çek başka bir üyelik içindir||Бул сертификат башка абонементке арналган||Ин сертификат барои абонементи дигар аст
gift_amount_checkout||Bu bir tutar çekidir: satın alırken «Hediye kodu» kutusuna girin.||Бул сумма сертификаты: сатып алып жатканда «Белек коду» талаасына киргизиңиз.||Ин сертификати маблағӣ аст: ҳангоми харид онро ба майдони «Рамзи тӯҳфа» ворид кунед.
gift_amount_ok||Kod geçerli: {amount} UZS indirim. Satın alırken «Hediye kodu» kutusuna {code} girin.||Код жарактуу: {amount} UZS арзандатуу. Сатып алып жатканда «Белек коду» талаасына {code} киргизиңиз.||Рамз эътибор дорад: {amount} UZS тахфиф. Ҳангоми харид {code}-ро ба майдони «Рамзи тӯҳфа» ворид кунед.
gift_redeemed||Çek kullanıldı: üyelik etkinleştirildi.||Сертификат колдонулду: абонемент иштетилди.||Сертификат истифода шуд: абонемент фаъол шуд.
gift_bought||Çek hazır: kodu aşağıdaki listede bulun.||Сертификат даяр: кодду төмөнкү тизмеден табыңыз.||Сертификат тайёр аст: рамзро дар рӯйхати зер ёбед.
gift_bought_pending||Kod, ödeme onaylandığında çalışır.||Код төлөм ырасталганда иштейт.||Рамз пас аз тасдиқи пардохт кор мекунад.
faq_title||SSS||Көп берилүүчү суроолор||Саволҳои зуд-зуд додашаванда
faq_sub||En çok duyduğumuz sorular||Эң көп берилген суроолор||Саволҳое, ки аз ҳама зиёд мешунавем
faq_more||Cevap bulamadınız mı? Arayın:||Жооп таппадыңызбы? Чалыңыз:||Ҷавоб наёфтед? Занг занед:
legal_updated||Güncellendi||Жаңыртылды||Навсозӣ шуд
ft_oferta||Genel teklif (ofert)||Жалпыга ачык оферта||Оферти оммавӣ
ft_privacy||Gizlilik politikası||Купуялуулук саясаты||Сиёсати махфият
ft_refund||İade kuralları||Кайтаруу эрежелери||Қоидаҳои баргардонӣ
consent_pre||Kabul ediyorum:||Мен кабыл алам:||Ман қабул мекунам:
consent_and||ve||жана||ва
consent_post||ve verilerimin işlenmesine onay veriyorum||жана маалыматтарымды иштетүүгө макулмун||ва ба коркарди маълумоти худ розӣ ҳастам
consent_note||Ödeme yaparak genel teklifi ve gizlilik politikasını kabul ettiğinizi onaylarsınız.||Төлөм жасап, жалпыга ачык офертаны жана купуялуулук саясатын кабыл алгандыгыңызды ырастайсыз.||Бо пардохт тасдиқ мекунед, ки оферти оммавӣ ва сиёсати махфиятро қабул кардаед.
err_consent||Devam etmek için genel teklifi ve gizlilik politikasını kabul ettiğinizi belirten kutuyu işaretleyin.||Улантуу үчүн жалпыга ачык офертаны жана купуялуулук саясатын кабыл алганыңызды белгилеңиз.||Барои идома додан катчаеро, ки оферти оммавӣ ва сиёсати махфиятро қабул мекунед, қайд кунед.
del_title||Hesabımı sil||Аккаунтумду өчүрүү||Нест кардани аккаунти ман
del_help||Hesabınız kapatılır ve kişisel veriler (ad, telefon, e-posta, fotoğraf, ölçümler, kayıtlar) silinir. Ödemeler ve siparişler muhasebe için anonimleştirilerek saklanır. Bu işlem geri alınamaz.||Аккаунтуңуз жабылат жана жеке маалыматтар (аты, телефон, e-mail, сүрөт, өлчөмдөр, жазуулар) өчүрүлөт. Төлөмдөр жана заказдар бухгалтерия үчүн аты жок түрдө сакталат. Муну кайра кайтаруу мүмкүн эмес.||Аккаунти шумо баста мешавад ва маълумоти шахсӣ (ном, телефон, e-mail, акс, андозаҳо, сабтҳо) нест карда мешавад. Пардохтҳо ва фармоишҳо барои ҳисобдорӣ беном нигоҳ дошта мешаванд. Инро баргардонидан мумкин нест.
del_type_code||Onaylamak için üye kodunuzu yazın:||Ырастоо үчүн мүчө кодуңузду териңиз:||Барои тасдиқ рамзи аъзои худро нависед:
del_sure||Hesabımın silineceğini anlıyorum||Аккаунтум өчүрүлөөрүн түшүнөм||Мефаҳмам, ки аккаунти ман нест карда мешавад
del_btn||Hesabı sil||Аккаунтту өчүрүү||Нест кардани аккаунт
del_wrong||Şifre yanlış veya onay kutusu işaretlenmemiş.||Сырсөз туура эмес же ырастоо белгиленген эмес.||Рамз нодуруст аст ё тасдиқ қайд нашудааст.
del_staff||Personel ve yönetici hesapları buradan silinemez.||Персонал жана администратор аккаунттарын бул жерден өчүрүүгө болбойт.||Аккаунтҳои кормандон ва администраторро аз ин ҷо нест кардан мумкин нест.
del_done||Hesap silindi. Hoşça kalın!||Аккаунт өчүрүлдү. Кош болуңуз!||Аккаунт нест карда шуд. Хайр!
entry_title||Giriş geçmişi||Кирүү тарыхы||Таърихи воридшавӣ
entry_month||Bu ayki girişler||Ушул айдагы кирүүлөр||Воридшавиҳои ин моҳ
entry_total||Toplam giriş||Жалпы кирүүлөр||Ҷамъи воридшавиҳо
entry_time||Saat||Убакыт||Вақт
entry_method||Yöntem||Ыкма||Усул
entry_repeat||aynı gün tekrar||ошол эле күнү кайра||ҳамон рӯз бори дигар
entry_m_qr||QR kod||QR код||QR-код
entry_m_manual||Resepsiyonda||Кабыл алууда||Дар қабулгоҳ
entry_m_self||Çevrimiçi giriş yapıldı||Онлайн кирүү белгиленди||Воридшавии онлайн
entry_m_guest||Misafir davetiyesi||Конок чакыруусу||Даъватномаи меҳмон
entry_m_old||Eski kayıt||Мурунку жазуу||Сабти қаблӣ
trainers_empty||Antrenör listesi yakında||Машыктыруучулар тизмеси жакында||Рӯйхати мураббиён ба қарибӣ
trainers_empty_sub||Henüz aktif antrenör yok. Yine de grup dersi programına bakabilirsiniz.||Азырынча активдүү машыктыруучу жок. Бирок топтук сабактардын графигин көрө аласыз.||Ҳоло мураббии фаъол нест. Бо вуҷуди ин ҷадвали машғулиятҳои гурӯҳиро дида метавонед.
rv_empty_title||Henüz yorum yok||Азырынча пикир жок||Ҳоло фикр нест
rv_empty_sub||Düşüncelerinizi paylaşan ilk kişi olun: formu kullanın.||Ойлоруңузду биринчи бөлүшүңүз: форманы колдонуңуз.||Аввалин шуда фикри худро мубодила кунед: аз шакл истифода баред.
rv_write_btn||Yorum bırak||Пикир калтыруу||Фикр гузоштан
rv_avg_inline||Ortalama puan||Орточо баа||Баҳои миёна
home_final_title||Bugün antrenmana başla||Бүгүн машыга баштаңыз||Имрӯз машқро оғоз кунед
choose_plan||Bir üyelik seçin||Абонемент тандаңыз||Абонемент интихоб кунед
classes_schedule||Ders programı||Сабактардын графиги||Ҷадвали машғулиятҳо
tl_tabs_aria||Hesaplayıcı bölümleri||Эсептегич бөлүмдөрү||Бахшҳои ҳисобкунак
tl_tab_body||Vücut analizi||Дене анализи||Таҳлили бадан
tl_tab_food||Beslenme||Тамактануу||Ғизо
tl_tab_train||Antrenman||Машыгуу||Машқ
tl_yrs||yaş||жаш||сола
tl_cm||cm||см||см
tl_how||Nasıl hesaplanır?||Кантип эсептелет?||Чӣ тавр ҳисоб мешавад?
tl_ideal_t||İdeal kilo aralığı||Идеалдуу салмак диапазону||Ҳудуди вазни идеалӣ
tl_target||Hedef kalori||Максаттуу калория||Калорияи ҳадаф
tl_disc_body||Sonuçlar VKİ (DSÖ), vücut yağı (US Navy) ve ideal kilo (Devine) formüllerine dayalı tahminlerdir ve gerçek değerlerinizden farklı olabilir. Sağlık sorununuz varsa veya hamileyseniz doktora danışın.||Жыйынтыктар БМИ (ДДСУ), дененин майы (US Navy) жана идеалдуу салмак (Devine) формулаларына негизделген болжолдор жана чыныгы маанилерден айырмаланышы мүмкүн. Ден соолук көйгөйү болсо же кош бойлуу болсоңуз дарыгер менен кеңешиңиз.||Натиҷаҳо тахминҳо аз рӯи формулаҳои ИМТ (ТУТ), чарбуи бадан (US Navy) ва вазни идеалӣ (Devine) мебошанд ва аз арзишҳои воқеӣ фарқ карда метавонанд. Агар мушкили саломатӣ дошта бошед ё ҳомиладор бошед, бо духтур маслиҳат кунед.
tl_disc_food||Sonuçlar Mifflin–St Jeor formülüne, aktivite çarpanlarına ve 1 kg yağ ≈ 7700 kcal kuralına dayalı tahminlerdir ve gerçek ihtiyacınızdan farklı olabilir. Sağlık sorununuz varsa veya hamileyseniz doktora danışın.||Жыйынтыктар Mifflin–St Jeor формуласына, активдүүлүк коэффициенттерине жана 1 кг май ≈ 7700 ккал эрежесине негизделген болжолдор жана чыныгы муктаждыгыңыздан айырмаланышы мүмкүн. Ден соолук көйгөйү болсо же кош бойлуу болсоңуз дарыгер менен кеңешиңиз.||Натиҷаҳо тахминҳо аз рӯи формулаи Mifflin–St Jeor, зарибҳои фаъолият ва қоидаи 1 кг чарбу ≈ 7700 ккал мебошанд ва аз эҳтиёҷоти воқеии шумо фарқ карда метавонанд. Агар мушкили саломатӣ дошта бошед ё ҳомиладор бошед, бо духтур маслиҳат кунед.
tl_disc_train||Sonuçlar Epley ve Brzycki (1RM), Tanaka (maks. nabız) ve Karvonen (bölgeler) formüllerine dayalı tahminlerdir ve gerçek değerlerinizden farklı olabilir. Kalp rahatsızlığı veya hamilelikte ağır antrenmandan önce doktora danışın.||Жыйынтыктар Epley жана Brzycki (1RM), Tanaka (макс. пульс) жана Karvonen (зоналар) формулаларына негизделген болжолдор жана чыныгы маанилерден айырмаланышы мүмкүн. Жүрөк оорусу болсо же кош бойлуу болсоңуз, оор машыгуудан мурун дарыгер менен кеңешиңиз.||Натиҷаҳо тахминҳо аз рӯи формулаҳои Epley ва Brzycki (1RM), Tanaka (набзи макс.) ва Karvonen (минтақаҳо) мебошанд ва аз арзишҳои воқеӣ фарқ карда метавонанд. Ҳангоми бемории дил ё ҳомиладорӣ пеш аз машқи вазнин бо духтур маслиҳат кунед.
tl_how_ideal||Devine formülü: erkekler için 50 kg veya kadınlar için 45,5 kg, boyun 152,4 cm'yi (60 inç) aşan her inç'i için 2,3 kg eklenir. Aralık bu değerin ±%10'udur.||Devine формуласы: эркектер үчүн 50 кг же аялдар үчүн 45,5 кг, бойдун 152,4 смден (60 дюйм) ашкан ар бир дюймуна 2,3 кг кошулат. Диапазон ушул маанинин ±10%ы.||Формулаи Devine: барои мардон 50 кг ё барои занон 45,5 кг, барои ҳар инчи қад аз 152,4 см (60 инч) зиёд 2,3 кг илова мешавад. Ҳудуд ±10%-и ин қимат аст.
tl_how_bf||US Navy yöntemi boyun, bel (kadınlarda kalça) ve boy logaritmalarını kullanır. Yağsız kütle = kilo × (1 − vücut yağı oranı).||US Navy ыкмасы моюн, бел (аялдарда жамбаш) жана бойдун логарифмдерин колдонот. Майсыз масса = салмак × (1 − дененин май үлүшү).||Усули US Navy логарифмҳои гардан, камар (барои занон рон) ва қадро истифода мебарад. Массаи бечарбу = вазн × (1 − ҳиссаи чарбуи бадан).
tl_how_macro||Önce protein (kg başına 1,8–2,2 g) ve yağ (kg başına 0,8–1,0 g) belirlenir, kalan kaloriler karbonhidrata gider. 1 g protein veya karbonhidrat = 4 kcal, 1 g yağ = 9 kcal.||Адегенде протеин (кг үчүн 1,8–2,2 г) жана май (кг үчүн 0,8–1,0 г) аныкталат, калган калория углеводго кетет. 1 г протеин же углевод = 4 ккал, 1 г май = 9 ккал.||Аввал сафеда (барои ҳар кг 1,8–2,2 г) ва чарбу (барои ҳар кг 0,8–1,0 г) муайян мешавад, калорияи боқимонда ба карбогидрат меравад. 1 г сафеда ё карбогидрат = 4 ккал, 1 г чарбу = 9 ккал.
tl_hr_how||Bölgeler, maksimum nabzınızın (veya istirahat nabzı girerseniz nabız rezervinizin) yüzdesidir.||Зоналар максималдуу пульсуңуздун (же эс алуудагы пульсту киргизсеңиз, пульс резервиңиздин) пайызы.||Минтақаҳо фоизи набзи максималии шумо (ё агар набзи истироҳатро ворид кунед, захираи набз) мебошанд.
pwa_install||Uygulamayı yükle||Тиркемени орнотуу||Насб кардани барнома
pwa_install_sub||Ana ekrandan açılır; üye kartınız çevrimdışı da çalışır.||Башкы экрандан ачылат; мүчө картаңыз интернетсиз да иштейт.||Аз экрани асосӣ кушода мешавад; корти аъзогии шумо бе интернет низ кор мекунад.
pwa_later||Şimdi değil||Азыр эмес||Ҳозир не
pwa_close||Kapat||Жабуу||Пӯшидан
pwa_ios_title||iPhone'a yükle||iPhone'го орнотуу||Насб дар iPhone
pwa_ios_1||Safari'nin altındaki Paylaş düğmesine dokunun (oklu kare).||Safariнин ылдый жагындагы «Бөлүшүү» баскычын басыңыз (жебелүү чарчы).||Тугмаи «Мубодила»-ро дар поёни Safari пахш кунед (мураббаъ бо тир).
pwa_ios_2||Aşağı kaydırın ve “Ana Ekrana Ekle”yi seçin.||Ылдый жылдырып, “Башкы экранга кошуу” дегенди тандаңыз.||Ба поён ҳаракат карда, “Илова ба экрани асосӣ”-ро интихоб кунед.
pwa_ios_3||“Ekle”ye dokunun: uygulama ana ekranınızda görünür.||“Кошуу” баскычын басыңыз: тиркеме башкы экранда пайда болот.||“Илова кардан”-ро пахш кунед: барнома дар экрани асосии шумо пайдо мешавад.
pwa_ios_note||Yalnızca Safari'de çalışır.||Safariде гана иштейт.||Танҳо дар Safari кор мекунад.
pwa_update||Yeni sürüm hazır||Жаңы версия даяр||Нусхаи нав тайёр аст
pwa_update_btn||Güncelle||Жаңыртуу||Навсозӣ
pwa_offline_banner||Çevrimdışısınız||Интернет жок||Шумо оффлайн ҳастед
pwa_push_title||Bildirimler||Билдирмелер||Огоҳиномаҳо
pwa_push_sub||Bu cihaza planınız, mesajlarınız ve sipariş durumunuz hakkında bildirim göndereceğiz.||Бул түзмөккө планыңыз, билдирүүлөрүңүз жана заказ абалы жөнүндө билдирмелерди жөнөтөбүз.||Мо ба ин дастгоҳ дар бораи нақша, паёмҳо ва ҳолати фармоиш огоҳинома мефиристем.
pwa_push_on||Aç||Күйгүзүү||Фаъол кардан
pwa_push_off||Kapat||Өчүрүү||Хомӯш кардан
pwa_push_enabled||Bu cihazda açık||Бул түзмөктө күйүк||Дар ин дастгоҳ фаъол аст
pwa_push_disabled||Bu cihazda kapalı||Бул түзмөктө өчүк||Дар ин дастгоҳ хомӯш аст
pwa_push_denied||Bildirimler engellendi: tarayıcı ayarlarından izin verin.||Билдирмелер бөгөттөлгөн: браузер жөндөөлөрүнөн уруксат бериңиз.||Огоҳиномаҳо масдуд шудаанд: дар танзимоти браузер иҷозат диҳед.
pwa_push_unsupported||Bu tarayıcı push bildirimlerini desteklemiyor (iPhone'da önce uygulamayı ana ekrana ekleyin).||Бул браузер push билдирмелерин колдобойт (iPhone'до адегенде тиркемени башкы экранга кошуңуз).||Ин браузер push-огоҳиномаҳоро дастгирӣ намекунад (дар iPhone аввал барнома ба экрани асосӣ илова кунед).
pwa_push_err||Bir şeyler ters gitti: tekrar deneyin.||Бир нерсе туура эмес болду: кайра аракет кылыңыз.||Чизе нодуруст рафт: дубора кӯшиш кунед.
offline_card||Üye kartım (QR)||Мүчө картам (QR)||Корти аъзогии ман (QR)
ftr_title||Fitness takibi||Фитнес трекер||Трекери фитнес
ftr_sub||Kilo, vücut ölçüleri, antrenmanlar ve hedefler tek yerde. Verilerinizi yalnızca siz görürsünüz.||Салмак, дене өлчөмдөрү, машыгуулар жана максаттар бир жерде. Маалыматыңызды сиз гана көрөсүз.||Вазн, андозаҳои бадан, машқҳо ва ҳадафҳо дар як ҷо. Маълумоти шуморо танҳо худи шумо мебинед.
ftr_weight||Kilo||Салмак||Вазн
ftr_this_week||Bu hafta||Бул жума||Ин ҳафта
ftr_workouts_n||antrenman||машыгуу||машқ
ftr_add_workout||Antrenman ekle||Машыгуу кошуу||Илова кардани машқ
ftr_history||Antrenman geçmişi||Машыгуу тарыхы||Таърихи машқҳо
ftr_history_body||Ölçüm geçmişi||Өлчөмдөр тарыхы||Таърихи андозаҳо
ftr_csv_body||ölçümler||өлчөмдөр||андозаҳо
ftr_csv_workouts||antrenmanlar||машыгуулар||машқҳо
ftr_quick_entry||Hızlı giriş: bugünün ölçümleri||Тез киргизүү: бүгүнкү өлчөмдөр||Воридкунии зуд: андозаҳои имрӯз
ftr_edit_entry||Kaydı düzenle||Жазууну түзөтүү||Таҳрири сабт
ftr_edit||Düzenle||Түзөтүү||Таҳрир
ftr_sex||Cinsiyet||Жынысы||Ҷинс
ftr_sex_m||Erkek||Эркек||Мард
ftr_sex_f||Kadın||Аял||Зан
ftr_more||Daha fazla ölçüm (cm), vücut yağı, nabız||Дагы өлчөмдөр (см), дененин майы, пульс||Андозаҳои бештар (см), чарбуи бадан, набз
ftr_m_waist||Bel (cm)||Бел (см)||Камар (см)
ftr_m_chest||Göğüs (cm)||Көкүрөк (см)||Сина (см)
ftr_m_hips||Kalça (cm)||Жамбаш (см)||Рон (см)
ftr_m_neck||Boyun (cm)||Моюн (см)||Гардан (см)
ftr_m_arm||Kol, biceps (cm)||Кол, бицепс (см)||Даст, бицепс (см)
ftr_m_thigh||Uyluk (cm)||Сан (см)||Рон (см)
ftr_m_calf||Baldır (cm)||Балтыр (см)||Соқи по (см)
ftr_body_fat||Vücut yağı (%)||Дененин майы (%)||Чарбуи бадан (%)
"""
