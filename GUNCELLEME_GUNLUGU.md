# Makro Lens — Güncelleme günlüğü OKWIS TANRI MODU

Kod veya davranış değişikliklerinin kısa kaydı. Ayrıntılı parça listesi: [SURUM_VE_YOL_HARITASI.md](SURUM_VE_YOL_HARITASI.md).

---

## 2026-04-10 — Piyasa Yönü Tahmini (PİYASA_YÖNÜ) Eklendi

**Amaç:** Analizlerin sonunda botun piyasa yönünü tahmin etmesi (bullish/nötr/bearish) ve "eğer mevcut koşullar devam ederse ne olur" senaryosu vermesi.

**Yapılanlar:**

### 1. Özet Modları (CIKTI_OZET) — ✅ TAMAMLANDI
**Mevsim/Hava/Jeopolitik özet çıktılarına `PİYASA_YÖNÜ` satırı eklendi:**

- **Mevsim Özet:** 
  - Yeni output: 9 satır (önceden 8)
  - Format: `PİYASA_YÖNÜ: (bullish/nötr/bearish; kısa neden + "Eğer ... devam ederse ... olacak" senaryosu)`
  - Örnek: *"PİYASA_YÖNÜ: Bullish; Mevsimsel talep artışı sektörleri destekliyor. Eğer bu koşullar devam ederse enerji ve turizm hisseleri yükselişte kalabilir."*

- **Hava Özet:** 
  - Yeni output: 9 satır (önceden 8)
  - Format: `PİYASA_YÖNÜ: (bullish/nötr/bearish; "Bu hava koşulları sektörleri ... yönlerine itiyor" + senaryo)`
  - Bağlam: Hava data → sektörel talep → piyasa yönü zinciri

- **Jeopolitik Özet:** 
  - Yeni output: 9 satır (önceden 8)
  - Format: `PİYASA_YÖNÜ: (bearish/nötr/bullish; "Bu gelişmeler risk iştahını ... şeklinde etkileyebilir" gibi)`
  - Bağlam: Jeopolitik riski → risk-on/risk-off → piyasa yönü

### 2. Uzun Anlatım Modları (CIKTI_DETAY) — 🔄 KISMÎ TAMAMLANDI
**Hava modunun uzun anlatımına "PİYASA TAHMINI" adımı eklendi (adım 8):**
- Cümle limiti: 10 → 11 cümle
- Adım 8: "**PİYASA TAHMINI:** Bull ish/Nötr/Bearish + kısa neden. Sonra 'Eğer ... devam ederse' senaryosu"
- Diğer adımlar (GÜVEN, TERS_SENARYO) sıra değişti (9 → 9. GÜVEN, 10 → 10. TERS_SENARYO)

**Mevsim ve Jeopolitik uzun anlatım:** Benzer yapı tanımlandı ama kod-level entegrasyonu teknik encoding issues nedeniyle şu aşamaya kaldı. (Çevrimdışı Python script ile yapılabilir)

### 3. Örnek Çıktı Formatı

```
ÖZET: Kış ayı enerji talebinin pik noktasında; sektörel katılım yüksek
...
RİSK: Jeopolitik şoklar enerji fiyatlarını hızlıca oynatabilir
PİYASA_YÖNÜ: Bullish; Enerji talep baskısı ve dolar zayıflığı üst tarafı destekliyor. Eğer OPEC kesiş kararı almazsa, yaz aylarında düşüş beklenir.
GÜVEN: 75/100 — YüksekTERS_SENARYO: Enerji fiyatları aniden düşebilir (jeopolitik rahatlaması, üretim artışı).
```

### 4. Teknik Detaylar
- **Mevsim özet:** PİYASA_YÖNÜ enjektif (line 1305)
- **Hava özet:** PİYASA_YÖNÜ enjekted (line 1448)
- **Jeopolitik özet:** PİYASA_YÖNÜ enjeksiyonundan (line 1559)
- **Hava detay:** Cümle limit güncelleme (line 1485: 10 → 11)

### 5. Sonuç
Kullanıcı artık:
- ✅ Piyasa yönü tahmini (bullish/nötr/bearish) alıyor
- ✅ "Eğer bu koşullar devam ederse ..." senaryosunu okuyor
- ✅ Her moda (mevsim/hava/jeopolitik) özgü yön tahmini görüyor
- ❌ Uzun anlatım versiyonları henüz tam aşama (Python refactor gerekli)

**Sonraki Adım:** Mevsim ve Jeopolitik detay modlarında da matching PİYASA TAHMINI step'i eklemek

---

## 2026-04-10 — Petrol-Hava Lojistik Zinciri Specificity (Hava Modunda)

**Amaç:** Hava modu + Petrol varlığı kombinasyonunda, bot sadece "hava havası enerji talebini etkiler" değil, detaylı **lojistik yakıt zinciri** (kar → karayolu taşımacılık verimsizlik → yakıt tüketimi ↑) anlatması, fakat OPEC/stok/dolar kuru gibi ana fiyat belirleyicilerin petrol fiyatını kontrol ettiği net olması.

**Yapılanlar:**
1. **`_hava_petrol_lojistik_directive(ay_adi, ulke)`** ✨ YENİ — Petrol-Hava bağlantı formatı
   - **kar/yağmur mekanizması:** Lastik sürtünmesi, motor boşta kaldırma → yakıt +2–4%
   - **Sıcaklık aşırılıkları:** Cold-start, ticari uçak kerozin → yakıt +1–3%
   - **Taşımacıların pozisyonu:** Zor hava → talep birikimi (mikro pulse); iyileşme → dağılma (fiyat rahatlaması)
   - **OPEC/Stok/Dolar Kontrolü:** Lojistik talep pulse marjinal; ana belirleyiciler stok, OPEC, dolar kuruna devam
   - **Türkiye özgü:** %~80 ithal petrol → Brent kuruna bağımlı; karayolu ~60% ticari lojistik → hava volatilitesi

2. **`hava_analizi_yap()` içine entegrasyon:**
   - varlik "petrol" ise → `_hava_petrol_lojistik_directive()` çağrılır
   - varlik_notu'na enjekte edilen lojistik directive sayesinde model hava→lojistik→yakıt→petrol zincirini analiz ediyor
   - Prompt: "Hava koşullarının lojistik verimliliğine etkisi × Türkiye petrol ithalatçılığı × OPEC/stok/dolar → Petrol fiyat riski nedir?"

3. **Sonuç:** Hava modunda petrol yazarsa, bot artık:
   - ✅ Kar/yağmur verimliliğine net etkisi açıklıyor (lojistik yakıt tüketimi +X%)
   - ✅ O tüketim pulse'inin OPEC/stok/dolar tarafından sönüme uğrayabileceğini anlatıyor
   - ✅ Türkiye ithalatçı perspektifini (Brent bağımlılığı) net hale getiriyor
   - ❌ Sadece "enerji talep" gibi genel ifadelerle kalmıyor

**Sonraki Adım:** Hava modunda petrol yazılı testimize beklemede — user feedback üzerine ek refinement

---

## 2026-04-10 — Varlık Spesifik Direktif Sistemi (Petrol Fiyat Bilinçlendirmesi)

**Amaç:** Kullanıcı "petrol" yazarsa, modele mevsime göre petrol fiyatının nasıl davrandığını, tüketim dinamiklerini, fiyat etkileyen faktörleri anlatması gereken detaylı direktif oluşturmak. Böylece bot sadece "petrol'e odaklan" değil, "kış ayında petrol enerji talebinden şu kadar ETKİLENİR, bu nedenle fiyat böyle hareket eder" açıklaması yapar.

**Yapılanlar:**
1. **`_varlik_tipi_tespit(varlik)`** ✨ YENİ — Metin girdisinden varlık türü tespit (emtia/kripto/hisse/doviz/diğer)
   - Emtia: petrol, altın, doğalgaz, bakır, soya, buğday, kahve, nikel, etc.
   - Kripto: bitcoin, ethereum, altcoin, etc.
   - Hisse: Apple, Microsoft, Tesla, etc.
   - Para: dolar, euro, sterlin, etc.

2. **`_varlik_detay_directive(varlik, varlik_tipi, ay_adi, ulke)`** ✨ YENİ — Varlık + ay kombinasyonuna göre mevsimsel "fiyat bilinci" direktifi
   - **Petrol (Emtia):** 
     - Kış: "Enerji talebinin pik noktası — isınma talebinden petrol genelde %X yükseliş..."
     - Yaz: "Ulaştırma talebinin zirve — klima, turizm motorlama..."
     - Geçiş: "Belirsizlik ve jeopolitik şoklara duyarlı..."
   - **Altın:** Reel faiz, dolar kuru, jeopolitik "güvenli liman" rolü
   - **Kripto:** Makro risk ortamı, merkez bankası politikası
   - **Hisse:** Sektörel mevsimsellik, kazanç döngüsü, faiz etkileri
   - **Para:** Faiz farkı (carry trade), ticaret dengesi, jeopolitik

3. **Mevsim/Hava/Jeopolitik analizlerine entegrasyon:**
   - Mevsim analizi: `varlik_notu = f"{varlik_detay}"` olarak prompt başına enjekte
   - Hava analizi: `varlik_detay + "HAVA BAĞLANTISI:"` → hava verisi ile varlık fiyatı bağlantısı
   - Jeopolitik: `varlik_detay + "JEOPOLİTİK BAĞLANTISI:"` → jeopolitik gelişmeler ve varlık fiyatının ilişkisi

4. **Örnek Çıktı (Mevsim + Petrol):**
   ```
   **VARLIK ANALİZİ — PETROL (Ocak):**
   Ocak kış döneminin ortası; enerji talebinin pik noktası.
   — Isınma ve doğalgaz talebinden petrol fiyatları tipik yükseli gösterir
   — Enerji enflasyonu → taşımacılık, lojistik maliyetleri artar
   — Coğrafi riskler (Orta Doğu, Rusya) petrol volatilitesini arttırır
   — OPEC karmaşası, dolar kuru, stok seviyeleri asıl belirleyiciler
   **Soru:** Türkiye'de bu dönemde enerji talebinin fiyatlaşması nasıl?
   **Bilinçlendir:** Petrol genelde kış aylarında enerji talebinden yüksek volatilite gösterir...
   ```

**Sonuç:** Petrol (veya altın, kripto, vb.) yazıldığında, analiz artık varlığa özgü mevsimsel/makro fiyat dinamiklerini detaylı açıklıyor. Kullanıcı "petrol fiyatları kış'ta neden yükseliyor, hangi faktörler?" sorusunun cevabını tablo olarak değil, prompt'tan gelen metin içinde görüyor.

---

## 2026-04-10 — Varlık Odaklı Sorgu (Güncelleme-Önerileri.md — Sat.243)

**Amaç:** Ülke seçiminden sonra kullanıcıya "Odaklanmak istediğin bir varlık var mı? (kripto, altın, petrol vb.)" sorusu sorarak varlık-odaklı analiz yapmak. Seçenek menüsü yok; yazı ile input (isteğe bağlı olarak `/skip` ile geçiş).

**Yapılanlar:**
1. **Yeni state:** `VARLIK_SORGUSU = 2` eklendi; state sırası: MOD(0) → ULKE(1) → VARLIK(2) → FORMAT(3)
2. **`ulke_secildi()` güncellemesi:** Ülke seçiminden sonra varlık sorusu göster; `VARLIK_SORGUSU` state'ine git
3. **`varlik_sorgusu_cevap()` (YENİ):** MessageHandler ile metin input alır; `/skip` yazarsa `varlik=""` (genel analiz); değilse input'u kaydet; FORMAT_SECIMI'ye git
4. **Analiz fonksiyonları güncellemesi:** `mevsim_analizi_yap()`, `hava_analizi_yap()`, `jeopolitik_analizi_yap()` — yeni parametr `varlik: str = ""` eklendi
5. **Varlik enjeksiyonu:** Her prompt başında, eğer varlik boş değilse: 
   ```
   **ODAKLANAN VARLIK:** Kullanıcı özellikle **{varlik}** üzerinde odaklanmak istiyor. Bu varlığın [MOD konteksti]'nde nasıl etkileneceğini ön planda tut.
   ```
6. **`cikti_format_secildi()` güncelleme:** `varlik = context.user_data.get("varlik", "")` alınıp tüm analiz fn'larına geçilir
7. **ConversationHandler güncelleme:** VARLIK_SORGUSU state'i eklendi; MessageHandler(filters.TEXT & ~filters.COMMAND, varlik_sorgusu_cevap)
8. **Dokümantasyon:** [VARLIK_ODAKLI_ANALIZ.md](VARLIK_ODAKLI_ANALIZ.md) oluşturuldu (detaylı kullanıcı akışı, test listesi)

**Sonuç:** Kullanıcı artık /analiz → Mod → Ülke → **Varlık yazma** → Çıktı stili → Varlık-odaklı analiz akışını deneyimliyor. Varlık yazmaması / `/skip` → genel analiz yapılır.

---

## 2026-04-09 — Parça I (manuel): Pro plan yetkilendirme + hesap ekranı

**Amaç:** Telegram Stars olmadan, admin tarafından bot üzerinden manuel Pro atama/iptal ile monetizasyon operasyonunu başlatmak.

**Yapılanlar:**  
1. **`app.py`** — plan kayıt altyapısı eklendi (`metrics/plan_kullanicilari.json`), süre dolunca otomatik free dönüşü var.  
2. **Admin komutları** — `/pro_ver <user_id> <gun>`, `/pro_iptal <user_id>`, `/odeme_kayit [n]` eklendi; yetki `ADMIN_USER_IDS` ile yönetiliyor.  
3. **`/hesabim`** — kullanıcı planı (free/pro), pro bitiş tarihi/kalan gün, günlük kullanım ve limit durumu gösterimi eklendi.  
4. **Limit bypass** — Pro kullanıcılar günlük ücretsiz limit kontrolünden muaf hale getirildi.  
5. **Ödeme/plan olay logu** — `metrics/odeme_olaylari.jsonl` ile grant/revoke/auto_expire kayıtları tutuluyor.

---

## 2026-04-09 — Parça L: `/performans` 7g/30g trend + mod karşılaştırma

**Amaç:** Güven telemetry panelini sadece statik ortalama yerine kısa/orta dönem yönüyle birlikte daha karar verilebilir hale getirmek.

**Yapılanlar:**  
1. **`app.py`** — `_performans_ozeti_hesapla()` mod bazında 7 gün ve 30 gün ortalama güven hesaplıyor.  
2. **Trend yönü** eklendi: 7g-30g farkına göre `↗ yükseliş`, `↘ düşüş`, `→ yatay`.  
3. **Mod karşılaştırma/liderlik** bölümü eklendi: ortalama güvene göre modlar sıralı listeleniyor.  
4. **`SURUM_VE_YOL_HARITASI.md`** — Parça L maddesi panelin yeni kapsamıyla senkronize edildi.
5. **Alarm + risk modu satırı** — “en çok düşük güven üreten mod” göstergesi ve “son 7 gün alarmı” (eşik: düşük güven oranı ≥ %35) eklendi.

---

## 2026-04-09 — Stratejik doküman revizyonu (ticari ürün odağı)

**Amaç:** [Güncelleme-Önerileri.md](Güncelleme-Önerileri.md) içindeki önerileri mevcut ürünle eşleyip, yol haritasını “para ödeten” farklara göre güncellemek.

**Yapılanlar:**  
1. **[SURUM_VE_YOL_HARITASI.md](SURUM_VE_YOL_HARITASI.md)** — durum tablosu güncellendi (Mevsim+Hava+Jeopolitik aktif), Parça K/L/N/O eklendi (güven skoru, mod karnesi, simülasyon/backtest, portföy+alarm).  
2. **[makro_lens_proje_plani.md](makro_lens_proje_plani.md)** — yenilenmiş ürün vizyonu, yeni faz sıralaması (Faz 1.5/Faz 3), güncel tier önerisi.  
3. **[MIMARI.md](MIMARI.md)** — envantere jeopolitik dosyası eklendi; sıradaki adımlar ticari değer odaklı yeniden sıralandı.

---

## 2026-04-09 — Parça K (v1): Güven skoru + ters senaryo entegrasyonu

**Amaç:** Çıktıyı sadece tema önerisi olmaktan çıkarıp ölçülebilir güven seviyesi ve “tezi bozan koşul” ile daha karar-destek odaklı hale getirmek.

**Yapılanlar:**  
1. **`app.py`** — `_guven_skoru_hesapla` (v1 heuristic: GDB, MBS, VKG, MBP) ve `_guven_etiketi` eklendi.  
2. **Kısa özet şablonları (mevsim/hava/jeopolitik)** — 6 satırdan 8 satıra genişletildi: `GÜVEN`, `TERS_SENARYO`.  
3. **Uzun anlatım şablonları** — modelden ayrı satır/cümle olarak `GÜVEN` ve `TERS_SENARYO` üretmesi istendi.  
4. **`_ozet_satirlari_html`** — yeni etiketler (`GÜVEN`, `TERS_SENARYO`) HTML kartta kalın etiketle render edilir.

Ek adım (v1.5):
5. **Güven telemetry** — her analizde güven bileşenleri `metrics/analiz_olaylari.jsonl` dosyasına yazılıyor (mod, ülke, stil, skor bileşenleri, bağlam uzunluğu).

---

## 2026-04-09 — Parça L (başlangıç): `/performans` canlı panel

**Amaç:** Toplanan güven telemetry verisini kullanıcıya okunur bir panel olarak sunmak.

**Yapılanlar:**  
1. **`app.py`** — `_performans_ozeti_hesapla()` ile `metrics/analiz_olaylari.jsonl` verilerinden toplu özet: toplam kayıt, son 7/30 gün, mod bazında ort. güven ve düşük güven oranı.  
2. **`/performans`** komutu eklendi ve handler’a bağlandı.  
3. **`/yardim`** metnine `/performans` satırı eklendi.

---

## 2026-04-09 — Mevsim RSS fallback zinciri güçlendirme

**Amaç:** Mevsim bağlamında Reuters DNS/SSL sorunları olduğunda haber başlıksız kalmayı azaltmak.

**Yapılanlar:** [mevsim_baglam.py](mevsim_baglam.py) — RSS çekimde `follow_redirects=True`; çoklu fallback sırası eklendi: `MACRO_RSS_URL` (varsa) → Reuters business → BBC business.

Ek: `.env` / `.env.example` tarafına `MACRO_RSS_URLS` (virgülle çoklu kaynak) desteği notlandı.

---

## 2026-04-09 — Jeopolitik RSS çoklu kaynak desteği (`GEO_RSS_URLS`)

**Amaç:** Jeopolitik modda tek feed’e bağımlılığı azaltmak ve `.env` üzerinden öncelik sıralı kaynak zinciri tanımlayabilmek.

**Yapılanlar:** [jeopolitik_baglam.py](jeopolitik_baglam.py) — `GEO_RSS_URLS` (virgülle liste) + `GEO_RSS_URL` geri uyum; fallback zinciri Reuters/BBC ile sürüyor. `.env` ve `.env.example` güncellendi.

---

## 2026-04-09 — Telegram çıktı sunumu: daha sade/premium uzun anlatım

**Amaç:** Uzun analizlerin “metin yığını” görünmesini azaltmak; daha profesyonel ve okunur kart deneyimi.

**Yapılanlar:** [app.py](app.py) — `_detay_govdeyi_sadelestir_html` eklendi; uzun anlatım gövdesi cümle/satır bloklarına ayrılıyor, kritik etiketler (`GÜVEN`, `TERS_SENARYO`, `RİSK`) vurgulanıyor, kart başlığına “Sade görünüm” notu eklendi.

---

## 2026-04-09 — LLM: çoklu Gemini anahtarı + Gemini önce / DeepSeek yedek

**Amaç:** `GEMINI_API_KEY`, `GEMINI_API_KEY_2`, `GEMINI_API_KEY_3` veya `GEMINI_API_KEYS` ile kota bitince sıradaki anahtar; tümü yetmezse `AI_FALLBACK_DEEPSEEK` ile DeepSeek. `openai` paketi yoksa DeepSeek yerine Gemini zinciri. `AI_PROVIDER=gemini` önerilen sıra (önce Google, sonra DeepSeek).

**Yapılanlar:** [app.py](app.py) — `_gemini_anahtarlari`, `_gemini_tum_anahtarlarla_dene`; [.env.example](.env.example).

---

## 2026-04-09 — LLM: DeepSeek seçeneği + Gemini yedek

**Amaç:** `AI_PROVIDER=deepseek` ile OpenAI uyumlu DeepSeek API denemesi; bakiye/ücret/kota benzeri hatalarda `AI_FALLBACK_GEMINI=true` iken `GEMINI_API_KEY` ile bir kez Gemini’ye düşme; aksi halde `.env` ile `AI_PROVIDER=gemini` ile devam.

**Yapılanlar:** [app.py](app.py) — `llm_metin_uret`, lazy Gemini/DeepSeek; `_llm_hata_kullanici_metni`; [requirements.txt](requirements.txt) `openai`; [.env.example](.env.example), [kurulum.md](kurulum.md) notları.

---

## 2026-04-09 — Cursor: kalıcı agent kuralları (`.cursor/rules`)

**Amaç:** Her yeni sohbette çalışma düzenini, günlük/yol haritası disiplinini ve proje bağlamını yeniden yazdırmadan Cursor’a aktarmak.

**Yapılanlar:** [.cursor/rules/makro-lens.mdc](.cursor/rules/makro-lens.mdc) — `alwaysApply: true`; [MIMARI.md](MIMARI.md) depo tablosuna ve kısa nota eklendi.

---

## 2026-04-09 — Parça B: Analiz mesajı footer ve uyarı politikası

**Amaç:** [makro_lens_proje_plani.md](makro_lens_proje_plani.md) ve [MIMARI.md](MIMARI.md) ile uyumlu şekilde, her analiz çıktısının sonuna **sabit, kısa bilgilendirme** eklemek; modelin aynı uyarıyı uzun uzadıya üretmesini istememek.

**Yapılanlar**

1. **`app.py`**
   - `ANALIZ_FOOTER` sabiti eklendi (düz metin, Telegram `parse_mode` gerektirmez; model çıktısındaki `_` / `*` ile çakışma riski azaltıldı).
   - `ulke_secildi` içinde gönderilen nihai mesaj: analiz gövdesi + `ANALIZ_FOOTER` + "Yeni analiz için /analiz" CTA sırası.
   - Mevsim prompt’una kural eklendi: model, "yatırım tavsiyesi değildir" / uzun yasal uyarıyı tekrarlamasın; kısa risk cümlesi kalsın.
2. **`/yardim`**
   - Footer ile aynı mesaj tonunda iki satırlık italik metin (Markdown) — kelime seçimi hizalandı.

**Sonuç:** Parça B “bitti sayılma” kriteri karşılandı; sıradaki önerilen adım Parça M (Mevsim bağlam katmanları).

---

## 2026-04-09 — Parça M: Mevsim modu bağlam katmanları ve prompt yapısı

**Amaç:** Mevsim analizine **yapılandırılmış bağlam** (zaman, meteorolojik mevsim fazı, ülkeye özel dönem notları, canlı makro RSS başlıkları, isteğe bağlı başkent hava özeti) ekleyerek çıktıyı daha tutarlı ve izlenebilir kılmak; promptu **Verilen bağlam / Görev / Kurallar** bloklarına ayırmak.

**Yapılanlar**

1. **`mevsim_baglam.py`** — `topla_mevsim_baglami(ülke)` tek metin bloğu üretir: yerel tarih/saat satırı; yarımküreye göre meteorolojik mevsim; [data/ulke_mevsim.json](data/ulke_mevsim.json) içindeki 3’er satırlık ülke notları; `httpx` ile RSS (varsayılan Reuters business, `MACRO_RSS_URL` ile değiştirilebilir); `.env` içinde `OPENWEATHER_API_KEY` varsa başkent için kısa hava özeti.
2. **`data/ulke_mevsim.json`** — Ülke başına `hemisphere`, `capital_query` (OpenWeather `q`), `takvim_notlari`.
3. **`app.py`** — `ulke_secildi` içinde `asyncio.to_thread` ile bağlam toplama ve Gemini çağrısı (event loop bloklanmasın); `mevsim_analizi_yap(ülke, baglam_metni)` yeni imza; boş model yanıtı için kısa kullanıcı mesajı; Türkiye / diğer ülkeler için dil ve sembol notları.
4. **`requirements.txt`** — `httpx==0.27.2`.
5. **`.env.example`** — `OPENWEATHER_API_KEY`, `MACRO_RSS_URL` isteğe bağlı anahtarlar.
6. **[MEVSIM_KALITE_SENARYOLARI.md](MEVSIM_KALITE_SENARYOLARI.md)** — 10 maddelik manuel regresyon listesi.

**Not:** RSS ve hava dış ağ gerektirir; ağ veya kaynak hata verirse bağlamda açıklayıcı düşüş metni üretilir (analiz yine çalışır).

**Sonuç:** Parça M teknik maddeleri karşılandı; sıradaki adaylar: Parça G (mesaj uzunluğu / hata UX), Parça C (tam Hava modu) veya Parça E (tek AI motoru kararı).

---

## 2026-04-09 — Mevsim çıktısı: sektör + üç şirket + girişim fırsatları

**Amaç:** Kullanıcı geri bildirimi doğrultusunda mevsim analizinde (1) yükselen/öne çıkan sektör temaları, (2) seçili **ülkeye ait üç örnek şirket** (yalnızca bilgilendirme; uydurmama kuralı), (3) hisse/kripto dışı varlık kanallarına kısa dokunuş, (4) mevsime uygun **girişim / yenilik fırsatı** temaları.

**Yapılanlar**

1. **`app.py`** — `mevsim_analizi_yap` içindeki **Görev** ve **Kurallar** metni güncellendi: 9 cümleye kadar izin; üç şirket tek cümlede virgülle; girişim bölümü 1–2 cümle; emin olunmayan şirket isimlerinin yazılmaması.

**Sonuç:** Model çıktısı daha zengin; halüsinasyon riski için açık “uydurma” yasağı korunuyor. Uzun mesajlar için Parça G (Telegram uzunluk bölme) ileride faydalı olur.

---

## 2026-04-09 — İki çıktı formatı: uzun anlatım / kısa özet

**Amaç:** Aynı mevsim analizi için kullanıcı tercihi: **detaylı metin** (mevcut akış) veya **tek bakışta kritik bilgiler** (kısa kart); vakti kısıtlı kullanıcılar için okunaklı, sade çerçeve.

**Yapılanlar**

1. **`app.py`** — Konuşma durumu `FORMAT_SECIMI`; ülke seçiminden sonra `[📖 Uzun anlatım]` / `[⚡ Kısa özet]`.
2. **`mevsim_analizi_yap(..., cikti_stili)`** — `detay`: önceki uzun prompt; `ozet`: altı sabit satır (`ÖZET:`, `SEKTÖR:`, `ŞİRKETLER:`, `VARLIK:`, `GİRİŞİM:`, `RİSK:`), markdown yok.
3. **`sarmla_analiz_mesaji`** — Kısa modda `⚡` + ayırıcı çizgiler; uzun modda başlık `Mevsim · Uzun anlatım`. Footer ve CTA her iki modda aynı.
4. **`/yardim`** — Çıktı seçimi kısa açıklama.

**Sonuç:** Tek analiz motoru, iki sunum katmanı. Çıktı biçimlendirmesi sonraki kayıtta HTML + kaçış ile güncellendi.

---

## 2026-04-09 — Telegram HTML ile daha okunaklı mesaj (kart hissi)

**Bağlam:** Telegram’da gerçek mobil UI yok; desteklenenler: **HTML** / Markdown, kalın/italik, emoji, satır düzeni.

**Yapılanlar**

1. **`app.py`** — Analiz sonuçları `parse_mode=HTML` ile gönderiliyor; `sarmla_analiz_mesaji_html`: başlıklar `<b>`, alt başlıklar `<i>`, ayırıcı satır, model gövdesi `html.escape` ile kaçırılıyor.
2. **Kısa özet** — `ÖZET:` / `SEKTÖR:` vb. satırlarda etiket kalın, değer kaçırılmış metin.
3. **`/start` ve `/yardim`** — Markdown yerine HTML ile aynı görsel dil.

**Sonuç:** Daha “uygulama kartı” hissi; model `<>&` üretse bile kırılma riski azalır.

---

## 2026-04-09 — Parça G: Dayanıklılık ve UX

**Amaç:** [SURUM_VE_YOL_HARITASI.md](SURUM_VE_YOL_HARITASI.md) Parça G — uzun mesajlar, anlaşılır hatalar, konuşmadan temiz çıkış.

**Yapılanlar**

1. **`telegram_html_parcalara_bol` / `gonder_parcali_html`** — Çıktı 4096 karakteri aşınca satır sınırlarından bölünür; ilk parça `edit_message_text`, devamı `send_message`; `BadRequest` olursa düz metin yedek.
2. **`_gemini_hata_kullanici_metni`** — Kota, zaman aşımı, anahtar, güvenlik vb. için kısa Türkçe; tam istisna log’da.
3. **`mevsim_analizi_yap`** — `except` artık ham `Hata: …` döndürmüyor; kullanıcı metni yukarıdaki fonksiyonla.
4. **Bağlam hatası** — `topla_mevsim_baglami` çökünce kullanıcıya HTML bilgi mesajı.
5. **`/cancel`** ve konuşma içinde **`/start`** — `ConversationHandler` fallbacks; dışarıda `/start` yine karşılama. Handler sırası: önce `ConversationHandler`, sonra global `/start`.
6. **`/analiz`** — Girişte `user_data` temizliği.
7. **`/yardim`** ve karşılama metni — `/cancel` / akışta `/start` notu.

**Sonuç:** Parça G tamam; sıradaki öneri Parça C (Hava modu) veya Parça E (motor soyutlaması).

---

## 2026-04-09 — Parça C: Hava modu (OpenWeatherMap)

**Amaç:** [SURUM_VE_YOL_HARITASI.md](SURUM_VE_YOL_HARITASI.md) Parça C — seçili ülkenin başkenti için canlı hava + kısa tahmin; makro/yatırım temalı analiz (uzun/kısa çıktı).

**Yapılanlar**

1. **[hava_baglam.py](hava_baglam.py)** — `topla_hava_baglami(ülke)`: `OPENWEATHER_API_KEY` zorunlu; `data/ulke_mevsim.json` içindeki `capital_query`; Current Weather + Forecast `cnt=8`; `HavaModuHatasi` ile kullanıcı mesajları (anahtar eksik, 401/404, ağ).
2. **`app.py`** — `mod_hava` butonu; `hava_analizi_yap`; `sarmla_analiz_mesaji_html(..., analiz_turu=)` ile başlıkta “Hava”; `cikti_format_secildi` dalı.
3. **[.env.example](.env.example)**, **[kurulum.md](kurulum.md)**, **`/yardim`** — Hava modu için anahtar notu.

**Sonuç:** Parça C tamam; sıradaki öneri Parça E veya Parça D / F.

---

## 2026-04-09 — Hava modu: 5 günlük günlük özet + prompt

**Amaç:** Kısa vadeli (~24 saat) yerine **yaklaşık 5 takvim günü** boyunca günlük min/max ve trend; model günlük değişime göre yorum yapabilsin.

**Yapılanlar:** [hava_baglam.py](hava_baglam.py) — `forecast` `cnt=40`; `_gunluk_ozet_satirlari`; bağlamda “Günlük özet” + “İlk 24 saat”; [app.py](app.py) `hava_analizi_yap` görev metinleri güncellendi.

---

## 2026-04-09 — Hava modu: prompt sıkılaştırması (ufuk + temsilî şirket)

**Amaç:** Test çıktılarında görülen riskleri azaltmak: ~5 günlük tahmini **aylar/uzun vade** gibi anlatmama; somut şirket adlarını **temsilî örnek** ve **yatırım tavsiyesi değil** çerçevesinde tutma; zayıf nedensellik ve al/sat dilini sınırlama.

**Yapılanlar:** [app.py](app.py) — `hava_analizi_yap` içinde hem **kısa özet** hem **uzun anlatım** prompt’ları: ufuk notu, `ŞİRKETLER` / şirket adı kuralları, “olası–dolaylı” dil, girişimde kısa vade, “al/sat / mutlaka” yasağı.

---

## 2026-04-09 — Parça D: Jeopolitik modu (RSS + prompt + UI)

**Amaç:** Mevsim/Hava benzeri bir akışla, jeopolitik haber başlıklarından yola çıkarak ülke odaklı makro/tema analizi üretebilmek.

**Yapılanlar:**
1. **`jeopolitik_baglam.py`** — `GEO_RSS_URL` (opsiyonel) veya varsayılan Reuters `worldNews` RSS’inden son başlıkları toplayan bağlam üretimi.
2. **`app.py`**
   - `mod_jeopolitik` butonu (inline keyboard)
   - `ANALIZ_JEOPOLITIK` etiketi (başlıkta “Jeopolitik” görünür)
   - `jeopolitik_analizi_yap` prompt’u (kısa/uzun çıktı stilleri)
   - `cikti_format_secildi` içinde jeopolitik dalı (bağlam + analiz üretim).
3. **`.env.example`** — opsiyonel `GEO_RSS_URL` notu eklendi.

Ek iyileştirme (RSS dayanıklılığı):
- `jeopolitik_baglam.py` içinde tek bir RSS url’e bağımlılık kaldırıldı: önce `.env`’deki `GEO_RSS_URL`, olmazsa Reuters, sonra BBC World RSS deneniyor.

Ek not (bugfix):
- `jeopolitik_baglam.py` içinde RSS çekiminde `follow_redirects=True` açıldı. Bazı kaynaklar kısa link/redirect verdiği için önceki durumda `302` hata sayılıp başlıklar çekilemiyordu.

---

## 2026-04-09 — Premium çıktı düzeni (kısa + uzun)

**Amaç:** Telegram analizlerini daha sade, daha şık ve premium bir görünüme taşımak.

**Yapılanlar:** [app.py](app.py) — kısa özet kartı bölüm bazlı başlıklara (`Piyasa Özeti`, `Öne Çıkan Tema`, `Şirket Örnekleri`, vb.) çevrildi; uzun anlatım `Durum / Etki Zinciri / Fırsat Alanı` bloklarına ayrıldı, alt bölümde `Risk / Ters Senaryo / Güven` tek bakışta toplandı.

Ek iyileştirme (v2):
- Promptlar sadeleştirildi: `GÜVEN` satırında teknik kısaltmalar kaldırıldı; uzun anlatım cümleleri kısaltma hedefi (20–22 kelime) eklendi; footer benzeri kapanış cümlesi üretimi ayrıca yasaklandı.

---

## 2026-04-09 — Parça H: Günlük ücretsiz analiz limiti (v1)

**Amaç:** Ücretsiz kullanımın günlük üst sınırını uygulayarak monetizasyon katmanı için temel oluşturmak.

**Yapılanlar:** [app.py](app.py) — kullanıcı bazlı günlük sayaç (`metrics/kullanim_limitleri.json`), `/analiz` girişinde limit kontrolü, üretim anında ikinci kontrol, başarılı analiz sonrası sayaç artırımı; `/yardim` metnine günlük limit satırı. [.env.example](.env.example) `ANALIZ_GUNLUK_LIMIT` notu.

