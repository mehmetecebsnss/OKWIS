# Makro Lens — Proje Planı

> Sosyolojik ve makro olayları finansal fırsata dönüştüren Telegram tabanlı yatırım asistanı.

---

## Konsept

Kullanıcı bir mod seçer (mevsim, jeopolitik, hava vb.), ardından ülke seçer. Sistem gerçek zamanlı veriyi AI ile birleştirerek neden-sonuç zinciri kurar ve kısa, anlaşılır analiz + risk/ters senaryo üretir.

**Temel fark:** Hisse tahmin botu değil. Büyük resmi okuyan, belirsizliği sayısallaştıran makro dolaylama motoru.

### Ürün vizyonu (yenilenmiş)

Makro Lens’in “para ödeten” çekirdeği:
1. **Karar güveni:** Her analizin yanında güven skoru ve başarısızlık senaryosu.
2. **Doğrulanabilirlik:** Mod bazlı geçmiş performans karnesi ve hata analizi.
3. **Kişiselleştirme:** Portföy etkisi, senaryo simülasyonu, gerçek zamanlı uyarı.
4. **Hız:** Kullanıcının saatler sürecek olay araştırmasını dakikaya indirme.

---

## Tarama Modları

| Mod | Açıklama |
|---|---|
| Mevsimler | Yaklaşan mevsim geçişlerinin sektörel etkileri |
| Özel günler & bayramlar | Seçim, bayram, resmi tatil dönemlerinde harcama/yatırım örüntüleri |
| Aylık hava durumları | Olağandışı hava koşullarının e-ticaret, tarım, enerji üzerindeki etkisi |
| Büyük çaplı doğal afetler | Deprem, sel, kasırga sonrası yeniden yapılanma ekonomisi |
| Dünya trendleri | Google Trends, sosyal medya trendlerinin piyasa yansıması |
| Savaşlar & jeopolitik | Çatışma bölgelerinin emtia, enerji, savunma sektörlerine etkisi |
| Sektör trendleri | Yükselen/düşen sektörlerin öncü sinyalleri |
| Magazin haberleri | Ünlü-marka ilişkileri, viral olayların şirket değerlemelerine etkisi |

---

## Sistem Mimarisi

```
Kullanıcı
  → Mod seçer (Telegram inline keyboard)
  → Ülke seçer
  → Analiz ister

Telegram Bot (Python)
  → State machine ile konuşma yönetimi
  → Kullanıcı tercihlerini hafızada tutar

Veri Katmanı
  → Web arama: aşağıdaki "Web arama stratejisi" bölümüne göre
  → Hava durumu: OpenWeatherMap API
  → Haberler: NewsAPI veya Google News RSS
  → Ekonomik takvim: Investing.com RSS

AI Motoru (Claude API)
  → Mod-spesifik sistem promptu
  → Neden-sonuç zinciri kurma
  → Ülke + mod + güncel veri → dolaylama

Çıktı
  → Maks. 4-5 cümle, arkadaş tonu
  → 2-3 somut varlık önerisi (hisse, kripto, emtia)
  → Kısa risk notu
  → Bot tarafından eklenen sabit kısa bilgilendirme satırı (uyarı politikası)
```

**Kod gerçeği:** Mevcut bot [app.py](app.py) içinde **Gemini** kullanıyor; Claude hedef stack’te. Tek motor ve klasör kuralları için [MIMARI.md](MIMARI.md).

### Web arama stratejisi

**MVP (önerilen):** Sunucu tarafında `httpx` ile harici bir arama API’si (ör. Tavily, SerpAPI, Brave Search API veya benzeri) çağrılır; dönen özet/snippet’ler string olarak Claude isteğine **bağlam** olarak eklenir. Haber RSS/NewsAPI ile birlikte kullanılır.

**Alternatif:** Anthropic Messages API üzerinde **tool use** ile modelin bir `web_search` (veya özel) aracını çağırması; arama sağlayıcısı bu araçta implemente edilir. Daha fazla esneklik, biraz daha karmaşık orchestration.

**Not:** “Sadece Claude” ile gerçek web taraması yoktur; ya araç zinciri ya da önceden çekilmiş veri gerekir.

---

## Prompt Mimarisi

Her mod için ayrı bir sistem promptu olacak. Tüm promptlar şu yapıyı takip eder:

```
Sen bir makro yatırım analistsin.
Kullanıcı [ÜLKE] için [MOD] analizi istiyor.
Güncel veri: [VERİ]

Görevin:
1. Bu durumun geçmişteki benzer örneklerini hatırla
2. Neden-sonuç zinciri kur (en az 2 katman derinliğinde)
3. Etkilenecek sektörleri belirle
4. Somut yatırılabilir varlık öner (hisse kodu, kripto sembolü veya emtia)
5. Yanıtı maksimum 5 cümle, samimi arkadaş tonunda yaz

Kesinlikle yapma: Uzun rapor yazma. Metnin içinde tekrarlayan veya paragraf halinde yasal uyarı yazma (bunu bot mesaj şablonu halleder). Belirsiz kal.
```

### Uyarı politikası (tek kaynak)

- Claude yalnızca analiz metnini üretir; **uzun veya tekrarlayan yasal disclaimer** model çıktısında istenmez.
- Her analiz mesajının sonuna Telegram botu **sabit, kısa** bir bilgilendirme satırı ekler (ör. bilgilendirme amaçlıdır; yatırım kararı için kendi araştırmanı yap). Böylece risk azaltılır ve prompt ile ürün davranışı çelişmez.

### Mod Bazlı Prompt Örnekleri

**Mevsim modu:**
> Kış ayı yaklaşıyor, Türkiye. Doğal gaz tüketimi artacak → BOTAŞ bağlantılı şirketler, ısınma ekipmanları perakendecileri. Aynı zamanda tatil dönemi e-ticaret ivmelenir → Trendyol rakipleri, kargo şirketleri. Emlak kiraları Aralık'ta genelde düşer ama Ocak'ta toparlanır.

**Hava durumu modu:**
> Amerika'da 1 hafta kar fırtınası bekleniyor. İnsanlar evden çıkamayacak → Amazon, DoorDash, Netflix talep artışı. Havayolları ve dışarıda çalışan sektörler (inşaat, turizm) kısa vadeli baskı görür. Bitcoin geçmişte böyle dönemlerde nötr kalmış.

**Savaş/jeopolitik modu:**
> İran bölgesinde gerilim tırmandı. İran petrol ihracatçısı → ham petrol fiyatı yükselebilir (Brent). Altın güvenli liman olarak talep görür. Risk iştahı azalır → Bitcoin ve küçük cap kripto kısa vadede baskıda kalabilir. Savunma hisseleri (Roketsan, Aselsan) bu dönemlerde öne çıkar.

---

## Teknik Stack

### Zorunlu
- **Python 3.11+**
- **python-telegram-bot** (v20+, async)
- **Anthropic Python SDK** (Claude API)
- **httpx** (API çağrıları için)
- **python-dotenv** (API key yönetimi)

### Opsiyonel / Sonraki Aşama
- **Redis** (kullanıcı state yönetimi, ölçeklenince)
- **PostgreSQL** (analiz geçmişi kaydetme)
- **Railway veya Render** (hosting, ücretsiz tier yeterli başlangıç için)

### Harici API'lar
| Servis | Kullanım | Fiyat |
|---|---|---|
| Anthropic Claude API | AI motoru | Kullanım başına (~$0.003/analiz) |
| OpenWeatherMap | Hava verisi | Ücretsiz (1000 çağrı/gün) |
| NewsAPI | Haber akışı | Ücretsiz tier (100 istek/gün) |
| Telegram Bot API | Ücretsiz | - |

---

## Geliştirme Yol Haritası

**Strateji:** Önce **Mevsim modunun derinliği** (bağlam, prompt, çıktı şablonu, kalite); ardından Hava/Jeopolitik ve diğer modlar. Ayrıntılı parçalar için bkz. [SURUM_VE_YOL_HARITASI.md](SURUM_VE_YOL_HARITASI.md) ve [MIMARI.md](MIMARI.md).

### Hafta 1 — İskelet (mevcut kod tabanı)
- [x] Telegram bot kurulumu (`app.py`, `python-telegram-bot` v20)
- [x] Mod seçim ekranı (inline keyboard; şu an yalnızca Mevsim aktif)
- [x] Ülke seçim ekranı
- [x] Conversation state machine (hangi mod, hangi ülke)
- [x] `/start`, `/analiz`, `/yardim` komutları

### Hafta 2 — Mevsim modu derinliği (yeni modlardan önce)
- [ ] Bağlam katmanları: hedef ülke için mevsim fazı + kısa takvim notları; isteğe bağlı hafif makro/etkinlik özeti (ör. RSS); isteğe bağlı başkent hava özeti (tam Hava modu değil)
- [ ] Prompt ve çıktı disiplini: sistem/kullanıcı ayrımı veya net bölümler; [Uyarı politikası](#uyarı-politikası-tek-kaynak) ile uyumlu **bot footer** (sabit kısa satır)
- [ ] AI motoru netliği: hedef **Claude** (plan) veya mevcut **Gemini** — tek sağlayıcı kararı ve tek analiz giriş noktası (`mod`, `ülke`, `ek_bağlam`)
- [ ] Web arama / arama API: önce Mevsim isteğine bağlam olarak bağla; doğrulandıktan sonra diğer modlara yay
- [ ] Mini kalite seti: birkaç ülke+ay için iç regresyon / ton kontrolü

### Hafta 3 — Yeni modlar, dayanıklılık ve test
- [x] Hava durumu modu (OpenWeatherMap + mod prompt’u)
- [x] Jeopolitik modu (RSS + mod prompt’u)
- [ ] Kalan modlar (özel günler, doğal afet, dünya trendleri, sektör, magazin) — aşamalı
- [ ] Hata yönetimi (API timeout, geçersiz ülke, boş model yanıtı, Telegram mesaj uzunluğu)
- [ ] Beta test (10-20 kullanıcı) ve mesaj kalitesi ince ayarı

### Hafta 4 — Monetizasyon (Faz 1)
- [ ] Kullanım limiti sistemi (günde 3 ücretsiz)

### Hafta 5 — Güven ve şeffaflık (Faz 1.5)
- [ ] Güven skoru (GDB/MBS/VKG/MBP) ve “ters senaryo” çıktısı
- [ ] Mod bazlı uzmanlık karnesi (`/performans`) + aylık hata raporu

### Hafta 6 — Monetizasyon (Faz 2)
- [ ] Telegram Stars ödeme entegrasyonu
- [ ] Affiliate link sistemi (Binance referral vb.)
- [ ] Basit dashboard (kaç kullanıcı, kaç analiz)

### Hafta 7 — Premium değer katmanı (Faz 3)
- [ ] Tarihsel replay/backtest (mod bazlı)
- [ ] Portföy etki analizi (senaryo bazlı)
- [ ] Eşik bazlı gerçek zamanlı alarm

---

## Monetizasyon Modeli

### Tier Yapısı (güncel öneri)
| Plan | Fiyat | Özellik |
|---|---|---|
| Ücretsiz | $0 | Mevsim + Hava, gecikmeli/limitli analiz, temel risk cümlesi |
| Pro | $49/ay | Tüm modlar + güven skoru + ters senaryo + mod karnesi + canlı analiz |
| Kurumsal | $499/ay | API erişimi, portföy etki analizi, özel senaryo, performans raporları |

### Gelir Kanalları
1. **Telegram Stars** — Platforma özel ödeme, banka hesabı gerekmez
2. **Affiliate komisyon** — Önerilen varlıklar için Binance/BIST referans linkleri
3. **Sponsorluk** — Belirli bir kullanıcı kitlesine ulaşınca broker sponsorluğu

### Maliyet Tahmini (100 aktif kullanıcı/gün)

**Birim fiyat (tek kaynak):** Ortalama ~**$0.003/analiz** (token kullanımına göre oynar; tablo ve hesap bu varsayıma göre).

- Günlük analiz: 100 kullanıcı × 3 analiz = **300 analiz/gün**
- Claude API: 300 × $0.003 ≈ **$0,90/gün** → ~**$27/ay** (30 gün)
- Hosting: $0-5/ay (Railway ücretsiz tier)
- **Toplam değişken + barındırma: ~$27–32/ay** (API fiyatı değişirse yeniden hesaplanır)

**Kâra geçiş (sipariş-of-magnitude):** Örn. yalnızca Claude API ~$27/ay için Pro abonelik ($7) ile **~4 aktif Pro kullanıcı** API maliyetini karşılar; gerçek marj token kullanımı ve ücretsiz tier kullanımına bağlıdır.

---

## Örnek Kullanıcı Akışı

```
Kullanıcı: /analiz
Bot: Hangi modu seçmek istersin?
     [Mevsim] [Hava] [Jeopolitik] [Trendler]
     [Özel Günler] [Doğal Afet] [Sektör] [Magazin]

Kullanıcı: [Mevsim]
Bot: Hangi ülke için analiz yapalım?
     [Türkiye] [ABD] [Almanya] [Diğer...]

Kullanıcı: [Türkiye]
Bot: 🔍 Analiz hazırlanıyor...

     Kış kapıya dayandı ve Türkiye'de bu dönem
     birkaç şey neredeyse garanti gibi: doğal gaz
     tüketimi patlar, insanlar içeride vakit geçirir,
     online alışveriş ivme kazanır.

     Bakabileceğin şeyler:
     → SNGAZ (doğalgaz dağıtımı)
     → TTKOM + e-ticaret lojistiği
     → Kısa vadeli AVISA (enerji ETF benzeri)

     Risk: Hükümet gaz fiyatlarına müdahale edebilir,
     bu sektörü frenleyebilir. Geniş pozisyon alma.

     ℹ️ Bilgilendirme amaçlıdır; yatırım kararı için kendi araştırmanı yap.
     (Bu satır bot şablonuyla otomatik eklenir; Claude metni değildir.)
```

---

## Rekabet Analizi

| Rakip | Güçlü yön | Zayıf yön |
|---|---|---|
| TradingView sinyalleri | Teknik analiz güçlü | Makro/sosyolojik boyut yok |
| ChatGPT direkt sorgu | Esnek | Odaksız, mod yok, hatırlamıyor |
| Investing.com | Veri zengin | Analiz yok, kullanıcı yorumlamalı |
| **Makro Lens** | Neden-sonuç zinciri, mod odaklı, Telegram native | Yeni, henüz güven yok |

---

## Riskler & Çözümler

| Risk | Çözüm |
|---|---|
| Yanlış analiz → kullanıcı zarar görür | Uyarı politikası: Claude metninde uzun uyarı yok; bot her mesajın sonuna sabit kısa bilgilendirme satırı ekler |
| Claude API maliyeti artar | Kullanıcı başına günlük limit + cache mekanizması |
| Telegram ban (finansal bot) | ToS'a uygun içerik, sinyal botu değil bilgilendirme botu konumlandırması |
| Rakip kopyalar | Prompt kalitesi + topluluk + veri kaynaklarının çeşitliliği ile savunma |

---

## Sonraki Adımlar

1. **MIMARI.md** — Mimari kurallar ve dosya envanteri (yeni geliştirme öncesi oku).
2. **Parça M (SURUM_VE_YOL_HARITASI)** — Mevsim modunu bağlam + prompt + footer ile güçlendir; yeni mod ekleme.
3. **AI motoru kararı** — Claude (plan) veya Gemini (mevcut); tek soyutlama katmanı.
4. **Hafta 3** — Hava ve Jeopolitik; ardından kalan modlar ve dayanıklılık.
5. **Monetizasyon** — Hafta 4–5 (limit, Stars, operasyon).
