"""Turkish / Kyrgyz / Tajik UI text, part 2. Line: key||Turkish||Kyrgyz||Tajik (see gym/i18n.py)."""

RAW = """
pt_sent||İstek gönderildi. Onaylandığında haber alacaksınız.||Өтүнүч жөнөтүлдү. Ырасталганда билдиребиз.||Дархост фиристода шуд. Пас аз тасдиқ хабар хоҳед гирифт.
pt_requests||Kişisel antrenman istekleri||Жеке машыгуу өтүнүчтөрү||Дархостҳои машқи шахсӣ
click_online||Click (çevrimiçi)||Click (онлайн)||Click (онлайн)
tg_help||Merhaba! Hesabınızı bağlamak için sitedeki profilinizde Telegram düğmesine basın.||Салам! Аккаунтуңузду байланыштыруу үчүн сайттагы профилиңизде Telegram баскычын басыңыз.||Салом! Барои пайваст кардани аккаунт дар профили сайт тугмаи Telegram-ро пахш кунед.
tg_linked||{name}, hesabınız bağlandı. Hatırlatmalar buraya gelecek. /status, /stop||{name}, аккаунтуңуз байланышты. Эскертмелер ушул жерге келет. /status, /stop||{name}, аккаунти шумо пайваст шуд. Хотиррасониҳо ба ин ҷо меоянд. /status, /stop
tg_unlinked||Telegram bağlantısı kaldırıldı.||Telegram ажыратылды.||Telegram ҷудо карда шуд.
tg_status_active||Üyeliğiniz {date} tarihine kadar aktif ({days} gün kaldı).||Абонементиңиз {date} чейин активдүү ({days} күн калды).||Абонементи шумо то {date} фаъол аст ({days} рӯз монд).
tg_status_none||Şu anda aktif bir üyeliğiniz yok.||Азыр активдүү абонементиңиз жок.||Ҳоло абонементи фаъол надоред.
tg_expiring||Üyeliğiniz {date} tarihinde bitiyor ({days} gün kaldı). Önceden yenileyin.||Абонементиңиз {date} бүтөт ({days} күн калды). Алдын ала узартыңыз.||Абонементи шумо дар {date} тамом мешавад ({days} рӯз монд). Пешакӣ тамдид кунед.
tg_class_tomorrow||Yarın saat {time}'de "{name}" dersine kayıtlısınız.||Эртең саат {time}до «{name}» сабагына жазылгансыз.||Фардо соати {time} шумо ба «{name}» сабт шудаед.
tg_pt_confirmed||Kişisel antrenman onaylandı: {trainer}, {time}.||Жеке машыгуу ырасталды: {trainer}, {time}.||Машқи шахсӣ тасдиқ шуд: {trainer}, {time}.
tg_pt_cancelled||Kişisel antrenman iptal edildi: {trainer}.||Жеке машыгуу жокко чыгарылды: {trainer}.||Машқи шахсӣ бекор шуд: {trainer}.
tg_pt_soon||Kişisel antrenmanınız yaklaşıyor: {trainer}, {time}.||Жеке машыгууңуз жакында: {trainer}, {time}.||Машқи шахсии шумо наздик аст: {trainer}, {time}.
tg_connect||Telegram'ı bağla||Telegram'ды байланыштыруу||Telegram-ро пайваст кардан
tg_connected||Telegram bağlı||Telegram байланышкан||Telegram пайваст аст
tg_disconnect||Bağlantıyı kes||Ажыратуу||Ҷудо кардан
card_transfer||Karta havale||Картага которуу||Интиқол ба корт
transfer_title||Karta havale ile ödeme||Картага которуу менен төлөө||Пардохт тавассути интиқол ба корт
transfer_step1||1. Adım. Aşağıdaki karta tam bu tutarı gönderin (Payme, Click, Uzum veya banka uygulamanızla).||1-кадам. Төмөнкү картага так ушул сумманы которуңуз (Payme, Click, Uzum же банк тиркемеси аркылуу).||Қадами 1. Айнан ҳамин маблағро ба корти зерин интиқол диҳед (тавассути Payme, Click, Uzum ё барномаи бонк).
transfer_step2||2. Adım. Havaleden sonra ödeme yaptığınız kartın son 4 hanesini girip «Ödedim»e basın.||2-кадам. Которгондон кийин төлөгөн картаңыздын акыркы 4 санын киргизип, «Төлөдүм» баскычын басыңыз.||Қадами 2. Пас аз интиқол 4 рақами охирини кортеро, ки аз он пардохт кардед, ворид карда, «Пардохт кардам»-ро пахш кунед.
card_number||Kart numarası||Карта номери||Рақами корт
card_holder||Kart sahibi||Карта ээси||Соҳиби корт
transfer_amount||Tutar||Сумма||Маблағ
transfer_comment||Havale açıklaması (bu kodu yazın)||Которуу комментарийи (ушул кодду жазыңыз)||Шарҳи интиқол (ин рамзро нависед)
transfer_exact||Tutar tam eşleşmeli ve ödemenizi hızlıca bulabilmemiz için kodu açıklamaya yazın.||Сумма так дал келиши керек, төлөмүңүздү тез табуу үчүн кодду комментарийге жазыңыз.||Маблағ бояд айнан мувофиқ бошад ва барои зуд ёфтани пардохти шумо рамзро дар шарҳ нависед.
transfer_what||Ne için||Эмне үчүн||Барои чӣ
transfer_reported||Ödeme bildiriminiz gönderildi (gönderen kart ••••{sender}). Personel paranın geldiğini kontrol edip onaylayacak.||Төлөм билдирүүңүз жөнөтүлдү (жөнөтүүчү карта ••••{sender}). Персонал акчанын келгенин текшерип, ырастайт.||Огоҳиномаи пардохти шумо фиристода шуд (корти фиристанда ••••{sender}). Кормандон воридшавии пулро санҷида, тасдиқ мекунанд.
sender_last4||Kartınızın son 4 hanesi||Картаңыздын акыркы 4 саны||4 рақами охири корти шумо
sender_last4_help||Yalnızca 4 hane. Kart numaranızın tamamını asla yazmayın.||Болгону 4 сан. Картаңыздын толук номерин эч качан жазбаңыз.||Танҳо 4 рақам. Рақами пурраи кортро ҳаргиз ворид накунед.
i_paid||Ödedim||Төлөдүм||Пардохт кардам
transfer_deadline||Son tarih:||Мөөнөтү:||Муҳлат:
pay_cancel||Ödemeyi iptal et||Төлөмдү жокко чыгаруу||Бекор кардани пардохт
pay_cancelled||Ödeme iptal edildi.||Төлөм жокко чыгарылды.||Пардохт бекор шуд.
pay_now||Şimdi öde||Азыр төлөө||Ҳозир пардохт кардан
no_card_note||Şu anda bağlı bir kart yok. Salonda nakit ödeyin veya yönetici ile iletişime geçin.||Азыр туташтырылган карта жок. Залда накталай төлөңүз же администратор менен байланышыңыз.||Ҳоло корти пайваст нест. Дар толор нақд пардохт кунед ё бо администратор тамос гиред.
report_sent||Ödeme bildirimi gönderildi. Ödeme onaylandığında üyeliğiniz/siparişiniz etkinleşir.||Төлөм билдирүүсү жөнөтүлдү. Төлөм ырасталганда абонемент/заказ иштей баштайт.||Огоҳиномаи пардохт фиристода шуд. Пас аз тасдиқи пардохт абонемент/фармоиш фаъол мешавад.
err_last4||Kartın son 4 hanesini girin||Картанын акыркы 4 санын киргизиңиз||4 рақами охири кортро ворид кунед
proof_yes||Ödendi diyor||Төлөдү дейт||Мегӯяд пардохт шуд
proof_no||Henüz bildirilmedi||Азырынча билдирилген жок||Ҳанӯз хабар дода нашудааст
confirm_money||Paranın geldiğini gördünüz mü?||Акчанын келгенин көрдүңүзбү?||Оё воридшавии пулро дидед?
reject||Reddet||Четке кагуу||Рад кардан
pending_card_note||Karta havaleniz tamamlanmamış veya onay bekliyor. Ödemeler sayfasını açın.||Картага которууңуз аякталган эмес же ырастоону күтүүдө. Төлөмдөр бетин ачыңыз.||Интиқол ба корти шумо анҷом наёфтааст ё мунтазири тасдиқ аст. Саҳифаи пардохтҳоро кушоед.
tg_payment_ok||Ödeme onaylandı: {amount} UZS ({ref}). Teşekkürler!||Төлөм ырасталды: {amount} UZS ({ref}). Рахмат!||Пардохт тасдиқ шуд: {amount} UZS ({ref}). Ташаккур!
tg_payment_rejected||Ödeme ({ref}) reddedildi veya iptal edildi. Sorularınız için resepsiyona başvurun.||Төлөм ({ref}) четке кагылды же жокко чыгарылды. Суроолоруңуз болсо, кабыл алууга кайрылыңыз.||Пардохт ({ref}) рад ё бекор шуд. Агар савол дошта бошед, ба қабулгоҳ муроҷиат кунед.
nav_training||Dersler||Сабактар||Дарсҳо
training||Antrenman dersleri||Машыгуу сабактары||Дарсҳои машқ
training_help||Her gün için antrenmanlar: video, nasıl yapılır ve ipuçları.||Ар бир күнгө машыгуулар: видео, кантип аткарылат жана кеңештер.||Машқҳо барои ҳар рӯз: видео, тарзи иҷро ва маслиҳатҳо.
all_types||Tüm türler||Бардык түрлөр||Ҳамаи навъҳо
level||Seviye||Деңгээл||Дараҷа
level_beginner||Başlangıç||Баштапкы||Навомӯз
level_intermediate||Orta||Орто||Миёна
level_advanced||İleri||Жогорку||Пешрафта
watch||Video||Видео||Видео
every_day||Her gün||Күн сайын||Ҳар рӯз
how_to||Nasıl yapılır||Кантип аткарылат||Тарзи иҷро
muscles||Çalışan kaslar||Иштеген булчуңдар||Мушакҳои кордиҳанда
equipment||Ekipman||Шайман||Таҷҳизот
tips||Hatalar ve ipuçları||Каталар жана кеңештер||Хатогиҳо ва маслиҳатҳо
open_video||Videoyu aç||Видеону ачуу||Кушодани видео
no_video||Bu ders için henüz video yok. Adımları okuyun veya antrenöre sorun.||Бул сабакка азырынча видео жок. Кадамдарды окуңуз же машыктыруучудан сураңыз.||Барои ин дарс ҳанӯз видео нест. Қадамҳоро хонед ё аз мураббӣ пурсед.
related||Bu türden diğer dersler||Ушул түрдөгү башка сабактар||Дарсҳои дигари ҳамин навъ
safety_note||Önce ısının. Ağrı hissederseniz durun. Sağlık sorununuz varsa başlamadan önce doktora veya antrenöre danışın.||Адегенде ысыңыз. Оору сезсеңиз токтоңуз. Ден соолукка байланыштуу көйгөй болсо, баштоодон мурун дарыгер же машыктыруучу менен кеңешиңиз.||Аввал гарм шавед. Агар дард ҳис кунед, қатъ кунед. Агар мушкили саломатӣ дошта бошед, пеш аз оғоз бо духтур ё мураббӣ маслиҳат кунед.
vip_get||VIP al||VIP алуу||VIP гирифтан
vip_extend||VIP'i uzat||VIPти узартуу||VIP-ро тамдид кардан
vip_locked||Yalnızca VIP||VIP үчүн гана||Танҳо барои VIP
vip_unlock_text||Bu dersi açmak için VIP alın. Ayda sadece 50.000 UZS.||Бул сабакты ачуу үчүн VIP алыңыз. Айына болгону 50 000 UZS.||Барои кушодани ин дарс VIP гиред. Моҳе танҳо 50 000 UZS.
vip_tag||Özel dersler, mağaza indirimi ve çift puan.||Өзгөчө сабактар, дүкөндө арзандатуу жана эки эсе упай.||Дарсҳои махсус, тахфиф дар мағоза ва холи дучанд.
vip_active||VIP aktif||VIP активдүү||VIP фаъол аст
vip_via_plan||VIP üyeliğiniz zaten VIP ayrıcalıklarını içerir.||VIP абонементиңизде VIP артыкчылыктары мурунтан эле бар.||Абонементи VIP-и шумо аллакай имтиёзҳои VIP-ро дар бар мегирад.
vip_perks||VIP ayrıcalıkları||VIP артыкчылыктары||Имтиёзҳои VIP
vip_perk_videos||{n} özel ders: haftalık programlar, beslenme, yağ yakımı||{n} өзгөчө сабак: жумалык программалар, тамактануу, май күйгүзүү||{n} дарси махсус: барномаҳои ҳафтаина, ғизо, сӯзондани чарбӣ
vip_perk_discount||Her mağaza alışverişinde %{pct} indirim||Дүкөндөгү ар бир сатып алууда {pct}% арзандатуу||{pct}% тахфиф ба ҳар харид дар мағоза
vip_perk_points||Çift puan: liderlik tablosunda daha hızlı yüksel||Эки эсе упай: лидерборддо тезирээк көтөрүлүңүз||Холи дучанд: дар ҷадвали пешсафон зудтар боло равед
vip_perk_badge||Profilinizde VIP rozeti||Профилиңизде VIP белгиси||Нишони VIP дар профили шумо
vip_days_note||Süre: {days} gün. Tekrar alırsanız günler üzerine eklenir.||Узактыгы: {days} күн. Кайра алсаңыз, күндөр үстүнө кошулат.||Давомнокӣ: {days} рӯз. Агар дубора гиред, рӯзҳо болои он илова мешаванд.
vip_ok||VIP etkinleştirildi. Hoş geldiniz!||VIP иштетилди. Кош келиңиз!||VIP фаъол шуд. Хуш омадед!
vip_pending||VIP ödemeniz onay bekliyor. Onaylandığında VIP başlar.||VIP төлөмүңүз ырастоону күтүүдө. Ырасталганда VIP башталат.||Пардохти VIP-и шумо мунтазири тасдиқ аст. Пас аз тасдиқ VIP оғоз мешавад.
kind_vip||VIP kartı||VIP өтмөк||Гузарномаи VIP
chat||Sohbet||Чат||Чат
chat_rules||Diğer üyelerle sohbet edin. Saygılı olun: hakaret, spam veya telefon numarası istemek yok. Personel bildirilen mesajları inceler.||Башка мүчөлөр менен баарлашыңыз. Сыйлуу болуңуз: мазактоо, спам же телефон номерин суроо жок. Персонал даттанылган билдирүүлөрдү карайт.||Бо аъзоёни дигар сӯҳбат кунед. Бо эҳтиром бошед: таҳқир, спам ё пурсидани рақами телефон мумкин нест. Кормандон паёмҳои шикоятшударо месанҷанд.
chat_banned_notice||Sohbette mesaj yazma izniniz yok. Yönetici ile iletişime geçin.||Чатка жазууга уруксатыңыз жок. Администратор менен байланышыңыз.||Ба шумо навиштан дар чат иҷозат нест. Бо администратор тамос гиред.
room_general||Genel oda||Жалпы бөлмө||Ҳуҷраи умумӣ
room_vip||VIP odası||VIP бөлмөсү||Ҳуҷраи VIP
room_general_help||Her üye için açık bir sohbet||Ар бир мүчөгө ачык чат||Чати кушода барои ҳар аъзо
room_vip_help||Yalnızca VIP üyelere özel sohbet||Тек VIP мүчөлөргө жабык чат||Чати хусусӣ танҳо барои аъзоёни VIP
chat_vip_only||Bu oda yalnızca VIP üyeler içindir.||Бул бөлмө VIP мүчөлөр үчүн гана.||Ин ҳуҷра танҳо барои аъзоёни VIP аст.
chat_people||Üye bul||Мүчөнү табуу||Ёфтани аъзо
chat_search||Ad veya üye numarası||Аты же мүчө номери||Ном ё рақами аъзо
chat_min_search||En az 2 karakter yazın.||Кеминде 2 белги териңиз.||Ақаллан 2 аломат нависед.
chat_start_btn||Mesaj||Жазуу||Паём
chat_mine||Sohbetlerim||Менин чаттарым||Чатҳои ман
chat_blocked_tag||engelli||бөгөттөлгөн||масдуд
chat_deleted||Mesaj silindi||Билдирүү өчүрүлдү||Паём нест карда шуд
chat_blocked_list||Engellediklerim||Бөгөттөгөн адамдарым||Масдудшудагони ман
chat_block||Engelle||Бөгөттөө||Масдуд кардан
chat_unblock||Engeli kaldır||Бөгөттөн чыгаруу||Масдудиятро бардоштан
chat_privacy_note||Diğerleri yalnızca adınızı ve soyadınızın baş harfini görür; telefon numaranız asla gösterilmez. Aramadan gizlemek için:||Башкалар аты-жөнүңүздүн аты менен фамилиянын биринчи тамгасын гана көрөт; телефон номериңиз эч качан көрсөтүлбөйт. Издөөдөн жашыруу үчүн:||Дигарон танҳо номи шумо ва ҳарфи аввали насабро мебинанд; рақами телефони шумо ҳаргиз нишон дода намешавад. Барои пинҳон кардан аз ҷустуҷӯ:
chat_you||Sen||Сиз||Шумо
chat_delete||Sil||Өчүрүү||Нест кардан
chat_report||Bildir||Даттануу||Шикоят кардан
chat_report_sent||Bildiriminiz yöneticiye gönderildi. Teşekkürler.||Даттанууңуз администраторго жөнөтүлдү. Рахмат.||Шикояти шумо ба администратор фиристода шуд. Ташаккур.
chat_empty_room||Henüz mesaj yok. İlk yazan siz olun!||Азырынча билдирүү жок. Биринчи болуп жазыңыз!||Ҳанӯз паём нест. Аввалин шумо нависед!
chat_blocked_notice||Bu sohbete yazamazsınız (engelli).||Бул сүйлөшүүгө жаза албайсыз (бөгөттөлгөн).||Шумо дар ин сӯҳбат навишта наметавонед (масдуд).
chat_type||Bir mesaj yazın...||Билдирүү жазыңыз...||Паём нависед...
chat_send||Gönder||Жөнөтүү||Фиристодан
chat_visible_label||Üyeler beni sohbette bulabilsin||Мүчөлөр мени чатта таба алсын||Аъзоён маро дар чат ёфта тавонанд
chat_banned||Sohbette mesaj yazma izniniz yok.||Чатка жазууга уруксатыңыз жок.||Ба шумо навиштан дар чат иҷозат нест.
chat_forbidden||Bu odaya erişim yok.||Бул бөлмөгө кирүүгө болбойт.||Ба ин ҳуҷра дастрасӣ нест.
chat_empty||Mesaj boş.||Билдирүү бош.||Паём холӣ аст.
chat_long||Mesaj çok uzun (en fazla 1000 karakter).||Билдирүү өтө узун (эң көбү 1000 белги).||Паём аз ҳад дароз аст (ҳадди аксар 1000 аломат).
chat_blocked||Bu üyeye mesaj gönderemezsiniz.||Бул мүчөгө жаза албайсыз.||Ба ин аъзо навишта наметавонед.
vip_videos||VIP videolar||VIP видеолор||Видеоҳои VIP
vip_perk_chat||VIP odası: yalnızca VIP üyelere özel sohbet||VIP бөлмөсү: тек VIP мүчөлөргө жабык чат||Ҳуҷраи VIP: чати хусусӣ танҳо барои аъзоёни VIP
min_short||dk||мүн||дақ
popular||Popüler||Популярдуу||Машҳур
low_stock||Az kaldı||Аз калды||Кам монд
vip_shop_note||VIP olarak her alışverişte %{pct} indirim alırsınız; sepette otomatik uygulanır.||VIP катары ар бир сатып алууда {pct}% арзандатуу аласыз; ал себетте автоматтык түрдө колдонулат.||Ҳамчун VIP шумо ба ҳар харид {pct}% тахфиф мегиред; он дар сабад худкор татбиқ мешавад.
vip_price_hint||VIP üyeler için %{pct} daha ucuz →||VIP мүчөлөр үчүн {pct}% арзаныраак →||Барои аъзоёни VIP {pct}% арзонтар →
related_products||İlgili ürünler||Тектеш буюмдар||Маҳсулоти монанд
free_pt_note||Bu ay {n} ücretsiz danışmanlık hakkınız var: sonraki isteğiniz ücretsiz.||Бул айда {n} акысыз кеңешиңиз бар: кийинки өтүнүчүңүз акысыз.||Шумо дар ин моҳ {n} машварати ройгон доред: дархости оянда ройгон аст.
vip_free||VIP ücretsiz||VIP акысыз||VIP ройгон
trainer_open||Detaylar||Толугураак||Муфассал
trainer_classes||Grup dersleri||Топтук сабактар||Машғулиятҳои гурӯҳӣ
vip_tag2||Daha fazla erişim, daha iyi sonuç: özel dersler, ayrılmış yerler, ücretsiz danışmanlık ve misafir davetiyesi.||Көбүрөөк мүмкүнчүлүк, жакшыраак жыйынтык: өзгөчө сабактар, камдалган орундар, акысыз кеңеш жана конок чакыруусу.||Дастрасии бештар, натиҷаи беҳтар: дарсҳои махсус, ҷойҳои захирашуда, машварати ройгон ва даъватномаи меҳмон.
vip_card||VIP kart||VIP карта||Корти VIP
vip_not_active||Aktif değil||Активдүү эмес||Фаъол нест
vip_guest_left||Misafir davetiyeleri (bu ay)||Коноктук чакыруулар (бул ай)||Даъватномаҳои меҳмон (ин моҳ)
vip_pt_left||Ücretsiz danışmanlıklar (bu ay)||Акысыз кеңештер (бул ай)||Машваратҳои ройгон (ин моҳ)
vip_seats||Her derste sizin için ayrılan yerler||Ар бир сабакта сиз үчүн камдалган орундар||Ҷойҳои барои шумо дар ҳар машғулият захирашуда
perk_t_videos||Özel video dersler||Өзгөчө видео сабактар||Дарсҳои видеоии махсус
perk_t_seats||Ayrılmış yerler||Камдалган орундар||Ҷойҳои захирашуда
vip_perk_seats||Her grup dersinde {n} yer VIP'ler için ayrılır; ders dolsa bile girersiniz.||Ар бир топтук сабакта {n} орун VIP үчүн сакталат, сабак толсо да киресиз.||Дар ҳар машғулияти гурӯҳӣ {n} ҷой барои VIP нигоҳ дошта мешавад, ҳатто агар машғулият пур шавад ҳам ворид мешавед.
perk_t_pt||Ücretsiz danışmanlık||Акысыз кеңеш||Машварати ройгон
vip_perk_pt||Her ay antrenörle {n} ücretsiz birebir danışmanlık.||Ар айда машыктыруучу менен {n} акысыз жекече кеңеш.||Ҳар моҳ {n} машварати ройгони шахсӣ бо мураббӣ.
perk_t_guest||Misafir getir||Конок алып келүү||Меҳмон овардан
vip_perk_guest||Ayda {n} misafir davetiyesi: arkadaşınız bir gün ücretsiz antrenman yapar.||Айына {n} конок чакыруусу: досуңуз бир күн акысыз машыгат.||Дар як моҳ {n} даъватномаи меҳмон: дӯстатон як рӯз ройгон машқ мекунад.
perk_t_discount||Mağaza indirimi||Дүкөндөгү арзандатуу||Тахфиф дар мағоза
perk_t_points||Çift puan||Эки эсе упай||Холи дучанд
perk_t_badge||VIP rozeti||VIP белгиси||Нишони VIP
guest_invite||Misafir davetiyesi||Конок чакыруусу||Даъватномаи меҳмон
guest_help||Misafirin adını ve günü girin. Misafir resepsiyonda QR'ı veya 8 karakterlik kodu gösterir; yalnızca o gün, bir kez geçerlidir.||Коноктун атын жана күндү киргизиңиз. Конок кабыл алууда QR же 8 белгилүү кодду көрсөтөт; ал бир жолу гана жана ошол күнү гана иштейт.||Номи меҳмон ва рӯзро ворид кунед. Меҳмон QR ё рамзи 8-аломатиро дар қабулгоҳ нишон медиҳад; он як маротиба ва танҳо дар ҳамон рӯз амал мекунад.
guest_name||Misafir adı||Коноктун аты||Номи меҳмон
guest_create||Davetiye oluştur||Чакыруу түзүү||Эҷоди даъватнома
guest_limit||Bu ayki davetiyeler bitti. Yenileri gelecek ay verilir.||Бул айдагы чакыруулар түгөндү. Жаңылары кийинки айда берилет.||Даъватномаҳои ин моҳ тамом шуданд. Навҳо моҳи оянда дода мешаванд.
guest_mine||Misafir davetiyelerim||Менин конок чакыруууларым||Даъватномаҳои меҳмони ман
guest_used_tag||Kullanıldı||Колдонулду||Истифода шуд
guest_valid||Geçerli||Жарактуу||Эътибор дорад
guest_host||Davet eden||Чакырган||Даъваткунанда
guest_rules||Misafirin kimliği olmalı. Salon kuralları misafirler için de geçerlidir.||Конокто күбөлүк болушу керек. Зал эрежелери коноктор үчүн да жарактуу.||Меҳмон бояд ҳуҷҷати шахсӣ дошта бошад. Қоидаҳои толор барои меҳмонон низ амал мекунанд.
guest||misafir||конок||меҳмон
guest_ok||Misafir girişi kaydedildi||Конок кирди||Воридшавии меҳмон қайд шуд
guest_used||Bu davetiye daha önce kullanıldı||Бул чакыруу мурун колдонулган||Ин даъватнома қаблан истифода шудааст
guest_wrong_day||Bu davetiye başka bir gün için||Бул чакыруу башка күнгө||Ин даъватнома барои рӯзи дигар аст
guest_name_bad||Misafirin adını girin (2-60 karakter)||Коноктун атын киргизиңиз (2-60 белги)||Номи меҳмонро ворид кунед (2-60 аломат)
guest_date_bad||Önümüzdeki 30 gün içinde bir tarih seçin||Алдыдагы 30 күндүн ичинен дата тандаңыз||Санаеро дар доираи 30 рӯзи оянда интихоб кунед
guests_today||Bugünün misafirleri||Бүгүнкү коноктор||Меҳмонони имрӯз
vip_only_action||Bu yalnızca VIP üyeler içindir||Бул VIP мүчөлөр үчүн гана||Ин танҳо барои аъзоёни VIP аст
vip_seats_note||VIP'siniz: her derste sizin için ek yerler ayrılır.||Сиз VIPсиз: ар бир сабакта сиз үчүн кошумча орундар сакталат.||Шумо VIP ҳастед: дар ҳар машғулият барои шумо ҷойҳои иловагӣ нигоҳ дошта мешавад.
vip_seats_hint||Her derste birkaç yer VIP üyeler için ayrılır. VIP hakkında →||Ар бир сабакта бир нече орун VIP мүчөлөр үчүн сакталат. VIP жөнүндө →||Дар ҳар машғулият якчанд ҷой барои аъзоёни VIP нигоҳ дошта мешавад. Дар бораи VIP →
pt_sent_free||İstek gönderildi. Bu ayki ücretsiz VIP danışmanlığı kullanıldı.||Өтүнүч жөнөтүлдү. Бул айдагы акысыз VIP кеңеши колдонулду.||Дархост фиристода шуд. Машварати ройгони VIP-и ин моҳ истифода шуд.
vip_how||Nasıl çalışır||Кантип иштейт||Чӣ тавр кор мекунад
vip_how_1||Bir ödeme yöntemi seçin ve VIP satın alın (kart, nakit veya Click).||Төлөм ыкмасын тандап, VIP сатып алыңыз (карта, накталай же Click).||Усули пардохтро интихоб карда, VIP харед (корт, нақд ё Click).
vip_how_2||Ödeme onaylanınca VIP hemen başlar ve 30 gün sürer.||Төлөм ырасталгандан кийин VIP дароо башталып, 30 күнгө созулат.||Пас аз тасдиқи пардохт VIP фавран оғоз мешавад ва 30 рӯз давом мекунад.
vip_how_3||İstediğiniz zaman yenileyin: günler bitiş tarihinize eklenir, hiçbir şey kaybolmaz.||Каалаган убакта узартыңыз: күндөр бүтүү күнүңүзгө кошулат, эч нерсе жоголбойт.||Дар ҳар вақт тамдид кунед: рӯзҳо ба санаи анҷом илова мешаванд, ҳеҷ чиз гум намешавад.
chat_rooms||Odalar||Бөлмөлөр||Ҳуҷраҳо
chat_no_dm||Henüz özel sohbet yok. Aşağıdan bir üye bulun ve merhaba deyin.||Азырынча жеке чат жок. Төмөндөн мүчө тапып, салам айтыңыз.||Ҳоло чати шахсӣ нест. Дар поён аъзоеро ёфта, салом диҳед.
chat_photo||Fotoğraf||Сүрөт||Акс
chat_attach||Fotoğraf ekle||Сүрөт тиркөө||Замима кардани акс
chat_remove_photo||Fotoğrafı kaldır||Сүрөттү алып салуу||Бардоштани акс
chat_drop||Fotoğrafı buraya bırakın||Сүрөттү ушул жерге таштаңыз||Аксро ин ҷо гузоред
chat_bad_image||Fotoğraflar jpg, png veya webp olmalı ve en fazla 5 MB olmalı.||Сүрөттөр jpg, png же webp болуп, 5 МБга чейин болушу керек.||Аксҳо бояд jpg, png ё webp ва то 5 МБ бошанд.
chat_sent||Gönderildi||Жөнөтүлдү||Фиристода шуд
chat_read||Okundu||Окулду||Хонда шуд
chat_rules_short||Saygılı olun. Fotoğraf da gönderebilirsiniz.||Сыйлуу болуңуз. Сүрөт да жөнөтө аласыз.||Бо эҳтиром бошед. Акс низ фиристода метавонед.
today_cap||Bugün||Бүгүн||Имрӯз
yesterday||Dün||Кечээ||Дирӯз
online||çevrimiçi||онлайн||онлайн
last_seen_at||son görülme {time}||акыркы жолу {time} көрүндү||бори охир {time} дида шуд
added_to_cart||Sepete eklendi||Себетке кошулду||Ба сабад илова шуд
removed_from_cart||Sepetten çıkarıldı||Себеттен алынды||Аз сабад бардошта шуд
cart_bar_items||{n} ürün||{n} буюм||{n} ашё
go_to_cart||Sepet||Себет||Сабад
cart_max||Stokta daha fazla yok||Запаста башка жок||Дигар захира нест
cart_more||Bir tane daha ekle||Дагы бирди кошуу||Як дона дигар илова кунед
cart_less||Bir tane çıkar||Бирди азайтуу||Як донаро кам кунед
continue_shopping||Alışverişe devam et||Сатып алууну улантуу||Идомаи харид
cart_empty_help||Su, protein veya enerji içeceği seçin: tek dokunuşla eklenir.||Суу, протеин же энергетикалык суусундук тандаңыз: бир басуу менен кошулат.||Об, протеин ё нӯшокии энергетикиро интихоб кунед: бо як пахш илова мешавад.
tg_help_profile||Üyelik, rezervasyon ve antrenman hatırlatmalarını Telegram'da alın.||Абонемент, брондоо жана машыгуу эскертмелерин Telegram'да алыңыз.||Хотиррасониҳои абонемент, брон ва машқро дар Telegram гиред.
otp_sent_to||{phone} numarasına SMS kodu gönderildi||{phone} номерине SMS код жөнөтүлдү||Рамзи SMS ба рақами {phone} фиристода шуд
login_code_title||Telefonunuza gelen kod||Телефонуңуздагы код||Рамз аз телефони шумо
login_code_help||Güvenlik için size SMS ile gönderdiğimiz 6 haneli kodu girin. O olmadan giriş yapamazsınız.||Коопсуздук үчүн SMS менен жөнөткөн 6 сандуу кодду киргизиңиз. Ансыз кире албайсыз.||Барои бехатарӣ рамзи 6-рақамиро, ки бо SMS фиристодем, ворид кунед. Бидуни он ворид шуда наметавонед.
resend_code||Kodu tekrar gönder||Кодду кайра жөнөтүү||Дубора фиристодани рамз
login_expired||Giriş süresi doldu, lütfen tekrar giriş yapın||Кирүү мөөнөтү бүттү, кайра кириңиз||Муҳлати воридшавӣ гузашт, лутфан дубора ворид шавед
google_required||Giriş yalnızca Google hesabıyla yapılır. Aşağıdaki Google düğmesini kullanın.||Кирүү Google аккаунту менен гана жасалат. Төмөнкү Google баскычын колдонуңуз.||Воридшавӣ танҳо бо аккаунти Google имконпазир аст. Тугмаи Google-и зеринро истифода баред.
google_only_register||Kayıt yalnızca Google ile yapılır. Sonra telefon numaranızı isteyip SMS koduyla doğrulayacağız.||Катталуу Google аркылуу гана. Андан кийин телефон номериңизди сурап, SMS код менен ырастайбыз.||Сабти ном танҳо тавассути Google аст. Баъд рақами телефони шуморо пурсида, бо рамзи SMS тасдиқ мекунем.
add_phone_title||Telefon numaranız||Телефон номериңиз||Рақами телефони шумо
add_phone_help||Giriş kodunuz bu numaraya SMS ile gönderilecek.||Кирүү кодуңуз ушул номерге SMS менен жөнөтүлөт.||Рамзи воридшавии шумо бо SMS ба ин рақам фиристода мешавад.
admin_login||Yönetici girişi||Администратор кирүүсү||Воридшавии администратор
start_now||Başla||Баштоо||Оғоз кардан
days_short||gün||күн||рӯз
from_price||Aylık||Айына||Дар як моҳ
home_vip_title||Bir sonraki seviyeniz||Кийинки деңгээлиңиз||Дараҷаи оянда
scroll_more||Aşağı kaydırın||Ылдый жылдырыңыз||Ба поён ҳаракат кунед
ticker_1||Güç||Күч||Қувват
ticker_2||Disiplin||Тартип||Интизом
ticker_3||Sonuç||Жыйынтык||Натиҷа
ticker_4||Her gün||Күн сайын||Ҳар рӯз
stat_members||aktif üye||активдүү мүчө||аъзои фаъол
stat_classes||haftalık ders||жумалык сабак||машғулияти ҳафтаина
stat_lessons||video ders||видео сабак||дарси видеоӣ
feat_training||Video dersler||Видео сабактар||Дарсҳои видеоӣ
feat_training_sub||Günlük antrenmanlar: nasıl yapılır ve hangi kaslar çalışır.||Күнүмдүк машыгуулар: кантип аткарылат жана кайсы булчуңдар иштейт.||Машқҳои рӯзона: тарзи иҷро ва кадом мушакҳо кор мекунанд.
feat_classes_sub||Grup dersine tek dokunuşla yer ayırtın.||Топтук сабакка бир басуу менен жазылыңыз.||Ба машғулияти гурӯҳӣ бо як пахш ном нависед.
feat_shop_sub||Su, protein, enerji içecekleri: salonda hazır.||Суу, протеин, энергетикалык суусундуктар: залда даяр.||Об, протеин, нӯшокиҳои энергетикӣ: дар толор омода.
feat_card_sub||QR kartınızla girin: sıra yok.||QR картаңыз менен кириңиз: кезек жок.||Бо корти QR ворид шавед: навбат нест.
home_plans_title||Size uygun bir üyelik||Сизге ылайыктуу абонемент||Абонементе, ки ба шумо мувофиқ аст
home_trainers_title||Sizi kim çalıştıracak||Сизди ким машыктырат||Кӣ шуморо машқ медиҳад
final_cta||Bugün başla. Yarın farkı gör.||Бүгүн баштаңыз. Эртең айырмасын көрөсүз.||Имрӯз оғоз кунед. Фардо фарқро мебинед.
login_as||Şu olarak giriş yap||Катары кирүү||Ворид шудан ҳамчун
role_member||Üye||Мүчө||Аъзо
role_trainer||Antrenör||Машыктыруучу||Мураббӣ
role_trainer_note||Antrenör paneli: müşterileriniz, dersleriniz ve plan oluşturucu.||Машыктыруучу панели: кардарларыңыз, сабактарыңыз жана план түзүүчү.||Панели мураббӣ: муштариён, машғулиятҳо ва тартибдиҳандаи нақша.
not_trainer||Bu numara bir antrenöre bağlı değil. Yönetici hesabınızı «Antrenörler» bölümünden bağlamalı.||Бул номер машыктыруучуга байланышкан эмес. Администратор аккаунтуңузду «Машыктыруучулар» бөлүмүндө байланыштырышы керек.||Ин рақам ба мураббӣ пайваст нест. Администратор бояд аккаунти шуморо дар «Мураббиён» пайваст кунад.
coach_panel||Antrenör paneli||Машыктыруучу панели||Панели мураббӣ
coach_clients||müşteri||кардар||муштарӣ
coach_attention||ilgi bekliyor||көңүл бурууну талап кылат||таваҷҷуҳ мехоҳад
coach_week_bookings||bu hafta rezervasyon||бул жумадагы брондоолор||бронҳои ин ҳафта
coach_month_pt||bu ay kişisel antrenman||бул айдагы жеке машыгуу||машқи шахсӣ дар ин моҳ
coach_add_client||Müşteri ekle||Кардар кошуу||Илова кардани муштарӣ
coach_add_help||Tam üye kodu veya telefon||Так мүчө коду же телефон||Рамзи дақиқи аъзо ё телефон
coach_today||Bugünkü derslerim||Бүгүнкү сабактарым||Машғулиятҳои имрӯзаи ман
coach_no_class_today||Bugün grup dersi yok||Бүгүн топтук сабак жок||Имрӯз машғулияти гурӯҳӣ нест
coach_upcoming||Onaylı seanslar||Ырасталган сеанстар||Сеансҳои тасдиқшуда
coach_attention_first||önce ilgi bekleyenler||адегенде көңүл бурууну талап кылгандар||аввал онҳое, ки таваҷҷуҳ мехоҳанд
coach_other_plan||başka bir antrenörün planı||башка машыктыруучунун планы||нақшаи мураббии дигар
coach_no_plan||Antrenman planı yok||Машыгуу планы жок||Нақшаи машқ нест
coach_never||hiç gelmedi||эч келген эмес||ҳеҷ гоҳ наомадааст
coach_days_away||gündür yok||күндөн бери жок||рӯз аст нест
coach_needs_plan||plan gerekiyor||план керек||нақша лозим аст
coach_today_in||bugün salonda||бүгүн залда||имрӯз дар толор
coach_days_ago||gün önce||күн мурун||рӯз пеш
coach_no_clients||Henüz müşteri yok. Yukarıdan üye koduyla ekleyin.||Азырынча кардар жок. Жогордон мүчө коду менен кошуңуз.||Ҳоло муштарӣ нест. Аз боло бо рамзи аъзо илова кунед.
coach_week||Haftam||Менин жумам||Ҳафтаи ман
coach_visits_28||Son 4 hafta||Акыркы 4 жума||4 ҳафтаи охир
coach_visits_total||toplam ziyaret||жалпы визит||ҷамъи ташрифҳо
coach_edit_plan||Planı düzenle||Планды түзөтүү||Таҳрири нақша
coach_make_plan||Plan oluştur||План түзүү||Тартиб додани нақша
coach_plan_help||Her satır: gün, egzersiz, set, tekrar ve not. Kaydedince üyenin aktif planı olur ve kendisine bildirim gider.||Ар бир сап: күн, көнүгүү, топтом, кайталоо жана эскертүү. Сактаганда мүчөнүн активдүү планы болот жана ага билдирүү барат.||Ҳар сатр: рӯз, машқ, сет, такрор ва эзоҳ. Пас аз захира он нақшаи фаъоли аъзо мешавад ва ба ӯ огоҳинома меравад.
coach_start_from||Bir programdan başla:||Программадан баштоо:||Аз барнома оғоз кунед:
coach_clear||Temizle||Тазалоо||Тоза кардан
coach_plan_title||Plan adı||План аталышы||Номи нақша
coach_plan_notes||Genel not||Жалпы эскертүү||Эзоҳи умумӣ
coach_add_row||Egzersiz ekle||Көнүгүү кошуу||Илова кардани машқ
coach_save_plan||Planı kaydet||Планды сактоо||Захира кардани нақша
client_not_found||Üye bulunamadı. Tam kodu (FZ-0012) veya telefonu kullanın.||Мүчө табылган жок. Так кодду (FZ-0012) же телефонду колдонуңуз.||Аъзо ёфт нашуд. Рамзи дақиқ (FZ-0012) ё телефонро истифода баред.
plan_empty||Bir ad ve en az bir egzersiz gerekli||Ат жана кеминде бир көнүгүү керек||Ном ва ақаллан як машқ лозим аст
plan_saved||Plan kaydedildi ve üyeye gönderildi! 💪||План сакталып, мүчөгө жөнөтүлдү! 💪||Нақша захира ва ба аъзо фиристода шуд! 💪
tg_plan_new||📈 {trainer} size yeni bir plan hazırladı: "{title}". «Planım»a bakın.||📈 {trainer} сизге жаңы план түздү: «{title}». «Менин планым» бөлүмүн караңыз.||📈 {trainer} барои шумо нақшаи нав тартиб дод: «{title}». «Нақшаи ман»-ро бинед.
day||Gün||Күн||Рӯз
exercise||Egzersiz||Көнүгүү||Машқ
"""
