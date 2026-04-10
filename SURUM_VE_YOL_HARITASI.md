# Makro Lens — Sürüm notları ve parçalı yol haritası

Bu dosya **şu ana kadar yapılanları** (Versiyon 1 / mevcut taban) özetler ve **sonraki güncellemeleri** küçük, tamamlanabilir parçalara böler. Ana vizyon için bkz. [makro_lens_proje_plani.md](makro_lens_proje_plani.md). **Mimari kurallar ve dosya envanteri:** [MIMARI.md](MIMARI.md).

---

## Versiyon 1 — Şu ana kadar yapılanlar (mevcut taban)

### Dokümantasyon

- **[makro_lens_proje_plani.md](makro_lens_proje_plani.md):** Ürün konsepti, mod listesi, mimari, prompt çerçevesi, uyarı politikası (model + bot şablonu ayrımı), web arama stratejisi (harici API vs tool use), teknik stack hedefi, haftalık yol haritası, monetizasyon fazları (Hafta 4–5 ayrımı), maliyet birimi düzeltmesi (~$0.003/analiz).
- **[kurulum.md](kurulum.md):** Sıfırdan kurulum (Python, BotFather, Gemini API, `.env`, `pip`, çalıştırma, sorun giderme).
- **[MIMARI.md](MIMARI.md):** Mimari kurallar, dosya envanteri, ilk kod adımı sırası.
- **[GUNCELLEME_GUNLUGU.md](GUNCELLEME_GUNLUGU.md):** Uygulama sonrası yapılanların kısa kaydı.
- **[main.py](main.py), [.gitignore](.gitignore), [.env.example](.env.example):** Giriş noktası, git güvenliği, ortam şablonu.

### Çalışan yazılım (`app.py` — kod içi etiket: MVP v0.1)

| Özellik | Durum |
|--------|--------|
| `python-telegram-bot` v20 (async) | Var |
| `.env` + `python-dotenv` | Var (`TELEGRAM_TOKEN`, `GEMINI_API_KEY`) |
| `/start`, `/yardim`, `/analiz` | Var |
| Mod seçimi (inline keyboard) | Mevsim + Hava + Jeopolitik aktif; diğerleri “Yakında” |
| Ülke seçimi (7 ülke + Diğer) | Var |
| `ConversationHandler` state machine | Var (`MOD_SECIMI`, `ULKE_SECIMI`) |
| AI analizi | **Gemini + (opsiyonel) DeepSeek fallback**, mod bazlı promptlar |
| Plan dokümanındaki Claude + `httpx` + harici veri katmanı | Henüz koda yansımadı |

### Bağımlılıklar ([requirements.txt](requirements.txt))

- `python-telegram-bot==20.7`
- `google-generativeai==0.8.3`
- `python-dotenv==1.0.0`

### Plan ↔ kod uyumsuzlukları (bilerek kayıt altında)

1. **AI sağlayıcı:** Plan Anthropic Claude öngörüyor; mevcut bot Gemini kullanıyor — bir sonraki büyük parçada “tek motor” kararı netleştirilmeli.
2. **Kurulum / giriş noktası:** [kurulum.md](kurulum.md) ve [main.py](main.py) ile `app.py` hizalandı (Parça A tamam).
3. **Uyarı politikası:** Parça B tamam — analiz çıktısında `ANALIZ_FOOTER` ([app.py](app.py)); bkz. [GUNCELLEME_GUNLUGU.md](GUNCELLEME_GUNLUGU.md).

### Bilinen teknik not

- (Giderildi) `except` bloğu girintisi düzeltildi.

---

## Yeni sürümde eklenebilecek başlıklar (özet)

Aşağıdakiler [makro_lens_proje_plani.md](makro_lens_proje_plani.md) ve mevcut kod boşluklarına göre önceliklendirilebilir:

- Sabit bilgilendirme satırının her analiz mesajına eklenmesi (plan ile uyum).
- Hava / jeopolitik / özel günler modları (önce veri kaynağı + prompt, sonra UI).
- Gerçek zamanlı bağlam: OpenWeatherMap, NewsAPI veya RSS, isteğe bağlı arama API’si (`httpx`).
- Claude’a geçiş veya Gemini’de kalma + tek tip “motor” soyutlaması.
- Hata yönetimi (timeout, boş yanıt, Telegram mesaj uzunluğu).
- Günlük kullanım limiti (Faz 1 monetizasyon).
- Deploy (Railway/Render), logging, opsiyonel Redis/DB.

---

## Strateji — Önce derinlik, sonra yeni mod

**Görüş:** Yeni mod eklemeden önce mevcut **Mevsim** modunu “vizyoner” ama **sınırlı kapsamlı** şekilde güçlendirmek genelde daha mantıklıdır.

- **Tekrar kullanılabilir kalıp:** Prompt, bağlam enjeksiyonu, footer, hata yönetimi ve (ileride) motor soyutlaması bir kez oturunca; Hava veya Jeopolitik sadece yeni veri + prompt varyantı olur. Aksi halde aynı zayıflıkları her modda yeniden üretirsiniz.
- **Ölçülebilirlik:** Tek modda kaliteyi iyileştirmek, A/B veya manuel skorlamayı mümkün kılar; mod sayısı artınca değerlendirme maliyeti katlanır.
- **“Bütün olasılıklar” uyarısı:** Profesyonel yaklaşım, sonsuz senaryo listesi değil; **öncelikli sinyal kümesi** tanımlamaktır (aşağıda Parça M). Her sürümde 2–3 sinyal katmanı eklemek sürdürülebilir; hepsini bir anda hedeflemek kapsam şişmesine yol açar.

Bu strateji, aşağıdaki parça sırasına **Parça M** ile yansıtıldı; Hava/Jeopolitik (eski C/D) bilinçli olarak **Mevsim kalitesi belirli bir eşiğe geldikten sonra** önerilir.

---

## Parçalı yapılacaklar (sırayla veya paralel)

Her parça **tek başına tamamlanabilir** olacak şekilde tanımlandı. Bitince bu dosyada ilgili satırları işaretleyebilirsin.

### Parça A — Doküman ve proje tutarlılığı

- [x] `kurulum.md`: `Makro-Lens`, `app.py` / `python main.py` ve proje kökü yolları hizalandı.
- [x] Kökte `main.py` — `app.main()` çağıran ince giriş noktası.
- [x] `.gitignore` — `.env` ve sanal ortam/önbellek.

**Bitti sayılma:** Yeni gelen biri dokümana göre projeyi açıp botu çalıştırabiliyor.

---

### Parça B — Çıktı şablonu ve uyarı politikası

- [x] Analiz sonucunu gönderen yerde (`ulke_secildi`) plana uygun **sabit kısa footer** (`ANALIZ_FOOTER` — [app.py](app.py)).
- [x] `/yardim` metni footer ile aynı ton ve ifadelerle hizalandı.

**Bitti sayılma:** Her analiz mesajı aynı bilgilendirme satırıyla bitiyor; model prompt’unda uzun uyarı istenmiyor (mevcut mevsim prompt’u ile uyumlu). **Kayıt:** [GUNCELLEME_GUNLUGU.md](GUNCELLEME_GUNLUGU.md) (2026-04-09).

---

### Parça M — Mevsim modunu mükemmelleştirme (yeni modlardan önce)

Amaç: Aynı ürün yüzeyinde (Mevsim + ülke) **daha tutarlı, zengin bağlamlı ve kontrol edilebilir** çıktı; sonraki modlar bu iskeleti kopyalar.

**1 — Bağlam katmanları (öncelik sırasıyla seç ve uygula)**

- [x] **Zaman:** Bot sunucusu yerel tarih/saat + hedef ülke için meteorolojik mevsim fazı — [mevsim_baglam.py](mevsim_baglam.py).
- [x] **Takvim / dönem notları:** [data/ulke_mevsim.json](data/ulke_mevsim.json) içinde ülke başına 3 madde (genişletilebilir).
- [x] **Makro (hafif):** RSS başlık özeti — varsayılan Reuters business; `MACRO_RSS_URL` ile özelleştirme.
- [x] **Hava (opsiyonel):** `OPENWEATHER_API_KEY` + `capital_query` ile başkent tek cümle özeti.

**2 — Prompt ve çıktı disiplini**

- [x] Tek prompt içinde **Verilen bağlam / Görev / Kurallar** bölümleri — [app.py](app.py) `mevsim_analizi_yap`.
- [x] İki adımlı neden-sonuç, 2–3 tema, risk cümlesi, uydurmama / emin değilsen belirt.
- [x] Dil: Türkiye için yerel tutarlılık notu; diğer ülkelerde İngilizce sembol parantezi serbest.

**3 — Kalite ve sürdürülebilirlik**

- [x] 10 maddelik manuel set — [MEVSIM_KALITE_SENARYOLARI.md](MEVSIM_KALITE_SENARYOLARI.md).
- [x] Boş model yanıtı için kısa mesaj; tam hata UX Parça G’de genişletilebilir.

**Bitti sayılma:** Mevsim akışı, **statik ülke notları + canlı RSS** (ve isteğe bağlı hava) ile çalışıyor; güncellenmiş prompt devrede. **Kayıt:** [GUNCELLEME_GUNLUGU.md](GUNCELLEME_GUNLUGU.md) (2026-04-09, Parça M).

---

### Parça C — Hava durumu modu (MVP)

*Öneri: Parça M ve isteğe bağlı Parça E (motor birliği) sonrasına alın.*

- [x] OpenWeatherMap anahtarı `.env` (`OPENWEATHER_API_KEY`) — [hava_baglam.py](hava_baglam.py).
- [x] Ülke → başkent `capital_query` — [data/ulke_mevsim.json](data/ulke_mevsim.json).
- [x] `httpx` ile anlık + kısa tahmin; Gemini’ye bağlam; [app.py](app.py) `hava_analizi_yap`.
- [x] Inline keyboard’da `mod_hava` akışı (ülke + uzun/kısa çıktı).
- [x] Mod-spesifik prompt (hava → sektör / şirket / girişim / risk).

**Bitti sayılma:** Kullanıcı Hava → Ülke seçince gerçek hava verisi + analiz alıyor. **Kayıt:** [GUNCELLEME_GUNLUGU.md](GUNCELLEME_GUNLUGU.md) (Parça C).

---

### Parça D — Jeopolitik modu (MVP)

*Öneri: Parça M sonrası; haber boru hattı mevsimde denendiyse burada hızlanır.*

- [x] Haber özeti kaynağı: RSS (`httpx`); varsayılan Reuters worldNews; istersen `.env` ile `GEO_RSS_URL`.
- [x] Bağlam string’ini modele ilet; jeopolitik prompt’u (`jeopolitik_baglam.py` + `app.py` `jeopolitik_analizi_yap`).
- [x] UI: callback `mod_jeopolitik` aktif (inline keyboard + `cikti_format_secildi` dalı).

**Bitti sayılma:** Jeopolitik seçildiğinde en az bir gerçek veri kaynağından gelen özet + analiz.

---

### Parça E — AI motoru birliği (Claude veya Gemini/DeepSeek)

- [ ] Karar: üretimde tek sağlayıcı (plan: Claude + Anthropic SDK) veya Gemini’de kalıp plan dokümanını güncelleme.
- [x] Ortak fonksiyon: `(mod, ulke, ek_baglam) -> str` tek giriş noktası (`llm_metin_uret` akışı).
- [ ] `.env` ve `requirements.txt` güncellemesi.

**Bitti sayılma:** Tüm modlar aynı arayüzden modele gidiyor; doküman ve kod uyumlu.

---

### Parça F — Web arama (plan: harici API veya tool use)

- [ ] Bir arama sağlayıcı seçimi (Tavily, SerpAPI vb.) veya Claude tool use tasarımı.
- [ ] Önce **Mevsim** bağlamına enjekte etme; doğrulandıktan sonra diğer modlara yayma.

**Bitti sayılma:** En az bir modda “canlı arama/RSS dışı” web özeti kullanılıyor (veya bilinçli olarak MVP’de devre dışı bırakıldığı dokümante edildi).

---

### Parça G — Dayanıklılık ve UX

- [x] API hatalarında kullanıcıya anlaşılır Türkçe mesaj — Gemini istisnaları `_gemini_hata_kullanici_metni`, bağlam hataları ayrı metin ([app.py](app.py)).
- [x] Telegram 4096 karakter sınırı — `telegram_html_parcalara_bol` + `gonder_parcali_html` (devam mesajları aynı sohbette).
- [x] `/cancel` ve konuşma içinde `/start` fallbacks; dışarıda `/start` karşılama; `/analiz` girişinde `user_data` temizliği.

**Bitti sayılma:** Yaygın hata senaryolarında bot çökmeden cevap veriyor. **Kayıt:** [GUNCELLEME_GUNLUGU.md](GUNCELLEME_GUNLUGU.md) (2026-04-09, Parça G).

---

### Parça H — Monetizasyon Faz 1 (limit)

- [x] Kullanıcı kimliği: `update.effective_user.id`.
- [x] Günde 3 analiz sayacı (dosya tabanlı v1: `metrics/kullanim_limitleri.json`; varsayılan limit `ANALIZ_GUNLUK_LIMIT=3`).
- [x] Limit aşımında kısa mesaj + (ileride) Stars yönlendirmesi için placeholder metin.

**Bitti sayılma:** Ücretsiz tier günlük 3 analizle sınırlanıyor.

---

### Parça I — Monetizasyon Faz 2 ve operasyon

- [ ] Telegram Stars entegrasyonu.
- [x] Manuel Pro operasyonu (admin komutları: `pro_ver`, `pro_iptal`; `ADMIN_USER_IDS` ile yetki).
- [x] `/hesabim` komutu (plan + pro bitiş/kalan gün + günlük kullanım durumu).
- [x] Ödeme/plan olay kaydı (jsonl log) ve admin izleme komutu.
- [ ] Affiliate link şablonları (isteğe bağlı, ToS’a uygun).
- [ ] Basit metrik: analiz sayısı / kullanıcı sayısı (log veya mini dashboard).

**Bitti sayılma:** Ödeme veya en azından metrik toplama yolundan biri üretimde denenebilir.

---

### Parça J — Deploy

- [ ] Railway veya Render için `Procfile` / start komutu, ortam değişkenleri listesi.
- [ ] README veya kurulum bölümüne deploy özeti.

**Bitti sayılma:** Repo dışında 7/24 çalışan bir örnek ortam tanımlı.

---

## Önerilen sıra (özet) — derinlik öncelikli

1. **Parça A** (doküman) → **Parça B** (footer) — hızlı kazanım, plan uyumu.  
2. **Parça M** (Mevsim mükemmelleştirme: bağlam katmanları + prompt + mini kalite seti) — **yeni modlardan önce**.  
3. İsteğe bağlı erken: **Parça G**’nin bir kısmı (uzun mesaj / API hata metinleri) M ile paralel.  
4. **Parça C** (Hava) — tamam.  
5. **Parça E** (tek AI motoru kararı + mevcut çoklu sağlayıcı düzenini netleştirme).  
6. **Parça F** — mevsim/jeopolitik bağlamına web arama kalitesi.  
7. **Parça H** → **I** → **J** — limit, gelir, deploy.  
8. **Yeni ticari katmanlar (K/L/N/O)** — güven skoru, performans karnesi, portföy/senaryo, alarm.

İlerledikçe bu dosyadaki kutuları işaretleyerek veya sürüm numarası ekleyerek (ör. v1.1, v1.2) geçmişi koruyabilirsin.

---

## Ürün-Pazar Uyumunu Güçlendiren Yeni Parçalar (v1.2+)

Bu blok, `Güncelleme-Önerileri.md` içindeki “para ödeten” fikirlerin uygulamaya dönük versiyonudur.

### Parça K — Güven Skoru + Başarısızlık Senaryosu (Core Differentiator)

- [x] Çıktıya `GÜVEN: 0-100` ve `NEDEN` alt bileşenleri (GDB, MBS, VKG, MBP) ekle. (v1 prompt + skorlayıcı)
- [x] Her analizde tek satır `TERS SENARYO` üret (hangi koşulda tez bozulur?). (v1 prompt kuralı)
- [x] Skor aralığına göre kullanıcı dili (yeşil/sarı/turuncu/kırmızı etiket). (🟢/🟡/🟠/🔴)
- [x] Güven skorunu logla (zaman içinde tahmin başarısı korelasyonu ölçülsün). (`metrics/analiz_olaylari.jsonl`)

**Bitti sayılma:** Mevsim/Hava/Jeopolitik çıktılarında güven skoru + başarısızlık senaryosu standart.

---

### Parça L — Mod Bazlı Uzmanlık Karnesi (Şeffaflık & Güven)

- [ ] Her mod için son N analizde yön doğruluğu ve oynaklık metrikleri.
- [x] `/performans` komutu: mod bazlı canlı güven paneli (7g/30g ortalama, trend yönü, mod karşılaştırma/liderlik).
- [ ] Aylık “hata analizi” kısa raporu üretimi (otomatik metin + metrik).

**Bitti sayılma:** Kullanıcı hangi modun ne kadar güvenilir olduğunu sayısal görebiliyor.

---

### Parça N — Simülasyon / Backtest (Pro Feature)

- [ ] Tarihsel olay replay: seçilen tarihte model ne derdi + gerçekte ne oldu.
- [ ] 1g/1h/1a ufuklar için basit başarı ölçümü.
- [ ] Ücretli katmanda “kullanıcı stratejisi” girdisiyle simülasyon.

**Bitti sayılma:** En az jeopolitik ve hava modunda tarihsel replay çalışıyor.

---

### Parça O — Portföy Etki Analizi + Gerçek Zamanlı Alarm

- [ ] Kullanıcı portföy giriş formatı (sembol,ağırlık) ve senaryo bazlı etki tahmini.
- [ ] Eşik bazlı uyarı altyapısı (ör. hava anomali eşiği, jeopolitik risk eşiği).
- [ ] Ücretsiz/Pro ayrımı: alarm sayısı ve portföy analizi limiti.

**Bitti sayılma:** Kullanıcı “benim portföyüm bu olayda ne olur?” sorusuna cevap alıyor.
