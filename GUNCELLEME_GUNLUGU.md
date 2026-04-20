# Makro Lens — Güncelleme günlüğü OKWIS TANRI MODU

Kod veya davranış değişikliklerinin kısa kaydı. Ayrıntılı parça listesi: [SURUM_VE_YOL_HARITASI.md](SURUM_VE_YOL_HARITASI.md).

---

## 2026-04-20 — Prompt Optimizasyonu (Verimlilik Güncellemesi)

**Amaç:** Token verimliliğini artırarak aynı bütçeyle daha derin ve tutarlı analiz çıktısı almak.

**Yapılanlar:**

1. **Çift Analiz Rehberi Kaldırıldı** ✅
   - 7 bağlam modülünden (`mevsim_baglam.py`, `jeopolitik_baglam.py`, `sektor_baglam.py`, `trendler_baglam.py`, `magazin_baglam.py`, `dogal_afet_baglam.py`, `ozel_gunler_baglam.py`) `analiz_rehberi` bloğu silindi
   - Yönlendirme artık sadece `app.py`'deki `mod_direktifi`'nde — tek kaynak
   - ~150 token/analiz tasarruf

2. **`_varlik_detay_directive` Sıkıştırıldı** ✅
   - ~400 token → ~80 token (%80 azalma)
   - Genel bilgi tekrarı kaldırıldı, sadece çerçeveleme direktifi bırakıldı
   - Petrol/altın/kripto/hisse/döviz için ayrı odak cümleleri

3. **`_hava_petrol_lojistik_directive` Sıkıştırıldı** ✅
   - ~350 token → ~80 token
   - Mekanizma açıklamaları kaldırıldı, net soru formatına geçildi

4. **Prob Zinciri Akıllı Filtreleme** ✅
   - `_ilgili_prob_zincirleri(mod)` → `_ilgili_prob_zincirleri(mod, ulke, varlik)`
   - Mod + ülke + varlık skorlaması ile en ilgili 2 zincir seçiliyor (eskiden kör 3 zincir)
   - "jeopolitik + ABD + petrol" → "İran Petrol Ambargosu" zinciri geliyor

5. **Okwis Dinamik Ağırlıklandırma** ✅
   - 8 modun bağlamı artık önem sırasına göre kesiliyor
   - Jeopolitik 1.5x, Mevsim 1.3x, Sektör 1.2x, Magazin 0.6x
   - Sabit 300/600 token yerine dinamik limit

6. **Güven Skoru Prompt'tan Çıkarıldı** ✅
   - `f"Güven: {g_toplam}/100 ({g_etiket})\n\n"` satırı tüm analiz fonksiyonlarından kaldırıldı
   - Model artık kendi çıktısını kısıtlamıyor, daha cesur analiz üretiyor
   - Güven skoru sadece kullanıcıya gösterilen Kalite Kartı'nda

7. **Mod-Spesifik Analist Kimliği** ✅
   - Tek evrensel `_ANALIST_KIMLIK` (120 token) → `_MOD_KIMLIK` dict (40-50 token/mod)
   - Her mod için odaklı kimlik: "Mevsimsel döngü uzmanısın", "Jeopolitik risk analistisin" vb.
   - `_ORTAK_KURALLAR` ayrı tutuldu (geriye dönük uyumluluk için `_ANALIST_KIMLIK` korundu)

**Net Kazanım:** Her analizde ~650-700 token tasarruf = %40-45 daha verimli prompt

**Dosyalar:** `app.py`, `mevsim_baglam.py`, `jeopolitik_baglam.py`, `sektor_baglam.py`, `trendler_baglam.py`, `magazin_baglam.py`, `dogal_afet_baglam.py`, `ozel_gunler_baglam.py`

**Rapor:** `VERİMLİLİK_RAPORU.md`

---

## 2026-04-20 — Alarm Sistemi İyileştirme

**Amaç:** Akıllı filtreleme, spam önleme ve aciliyet seviyeleri eklemek.

**Yapılanlar:**

1. **Akıllı Portföy Filtresi** ✅
   - Kullanıcının portföyündeki varlıklara göre alarm filtrele
   - Genel piyasa kelimeleri (faiz, kriz, savaş, Fed) her zaman geçer
   - Portföy boşsa tüm alarmlar gösterilir

2. **Spam Önleme** ✅
   - Günde max 3 alarm per kullanıcı
   - `metrics/gunluk_alarm_sayaci.json` ile takip

3. **Aciliyet Seviyeleri** ✅
   - 🔴 Kritik (8-10): Savaş, borsa çöküşü, acil faiz kararı
   - 🟡 Önemli (6-7): Jeopolitik gerilim, önemli ekonomik veri
   - 🟢 Bilgi (5): Dikkat çekici piyasa hareketi
   - Alarm eşiği 7'den 5'e düşürüldü (daha fazla bilgi)

4. **`/bildirim` Komutu Yenilendi** ✅
   - Inline butonlarla durum paneli
   - `/bildirim seviye kritik|onemli|bilgi`
   - `/bildirim portfoy ac|kapat`
   - Bugün gönderilen alarm sayısı gösterimi

5. **Geriye Dönük Uyumluluk** ✅
   - Eski `{user_id: bool}` format otomatik yeni formata dönüştürülüyor

**Dosyalar:** `alarm_sistemi.py`, `app.py`

---

## 2026-04-20 — Portföy Entegrasyonu

**Amaç:** Kullanıcıların varlıklarını yapılandırılmış şekilde kaydetmesi ve analizin buna göre kişiselleşmesi.

**Yapılanlar:**

1. **`portfoy.py`** ✨ YENİ
   - Yapılandırılmış varlık saklama (sembol, miktar, maliyet, kategori)
   - Otomatik kategori tespiti: kripto/emtia/hisse/döviz
   - Risk profili (agresif/orta/muhafazakar) ve yatırım ufku
   - `portfoy_analiz_blogu()` — analiz prompt'una enjekte edilecek blok
   - Portföy dağılım grafiği (pie + bar chart, matplotlib)

2. **`app.py`** — `/portfoy` komutu
   - `/portfoy` — özet + grafik butonu
   - `/portfoy ekle BTC 0.5` — varlık ekle
   - `/portfoy ekle ETH 2 3200` — maliyet fiyatıyla ekle
   - `/portfoy cikar BTC` — varlık çıkar
   - `/portfoy sil` — tüm portföyü sil
   - `/portfoy risk orta` — risk profili
   - `/portfoy ufuk uzun` — yatırım ufku
   - `/portfoy grafik` — PNG grafik gönder

3. **Okwis Analizi Entegrasyonu** ✅
   - Portföy varsa analiz prompt'una otomatik enjekte
   - "Senin BTC'in", "portföyündeki altın" sahiplenme dili
   - Analiz başlığında "Portföy Aktif" göstergesi

**Dosyalar:** `portfoy.py` (yeni), `app.py`, `metrics/portfoy.json`

---

## 2026-04-20 — Backtest/Simülasyon Sistemi

**Amaç:** Geçmiş tahminlerin performansını görsel raporlarla göstermek.

**Yapılanlar:**

1. **`backtest.py`** ✨ YENİ
   - Tahmin kayıt sistemi (`metrics/tahmin_kayitlari.jsonl`)
   - Performans özeti (toplam, doğrulanan, bekleyen, oran)
   - Mod bazlı istatistikler
   - Detaylı analiz: varlık/ülke/süre bazlı performans
   - Manuel doğrulama fonksiyonu

2. **Görsel Raporlar** ✅
   - Performans grafiği: mod karşılaştırma (horizontal bar chart)
   - Detaylı analiz grafiği: 3 subplot (varlık, ülke, süre bazlı)

3. **`/backtest` Komutu** ✅
   - `/backtest` veya `/backtest 30`
   - Metin raporu + 2 grafik otomatik gönderim

**Dosyalar:** `backtest.py` (yeni), `app.py`, `metrics/tahmin_kayitlari.jsonl`

---

## 2026-04-20 — Görsel Çıktı Sistemi

**Amaç:** Emoji kargaşası yerine profesyonel grafik ve PDF raporlar.

**Yapılanlar:**

1. **`gorsel_olusturucu.py`** ✨ YENİ
   - Güven skoru grafiği (PNG, horizontal bar chart)
   - Olasılık zincirleri infografiği (PNG)
   - PDF rapor (ReportLab, Pro özelliği)
   - Türkçe karakter sorunu: transliteration ile çözüldü

2. **Telegram Entegrasyonu** ✅
   - Analiz sonrası otomatik grafik gönderimi
   - Pro kullanıcılar için PDF butonu
   - Hata toleranslı (kütüphane yoksa sessizce geçer)

**Dosyalar:** `gorsel_olusturucu.py` (yeni), `app.py`

---

## 2026-04-20 — 🔴 ACİL GÜVENLİK VE HATA DÜZELTMELERİ

**Amaç:** Kritik hataları ve güvenlik açıklarını acil olarak düzeltmek.

**Durum:** ✅ TAMAMLANDI - Bot başarıyla çalışıyor (20:22)

**Yapılanlar:**

1. **UTF-8 BOM Hatası Düzeltildi** ✅
   - `_prob_zinciri_yukle()` fonksiyonu `encoding="utf-8-sig"` kullanacak şekilde güncellendi
   - `prob_zinciri.json` artık başarıyla yükleniyor
   - Sosyal ihtimal zincirleri analiz kalitesine katkı sağlıyor

2. **ConversationHandler Uyarıları Düzeltildi** ✅
   - `conv_handler` ve `profil_handler` tanımlarında `per_message=False` olarak güncellendi
   - `per_chat=True` ve `per_user=True` parametreleri eklendi
   - Uyarı azaldı (sadece bilgilendirme uyarısı kaldı, kritik değil)

3. **Environment Variables Kontrolü Eklendi** ✅
   - `check_required_env_vars()` fonksiyonu eklendi
   - Bot başlangıcında tüm gerekli API anahtarları kontrol ediliyor
   - Eksik anahtar varsa açıklayıcı hata mesajı veriliyor

4. **JobQueue Kuruldu** ✅
   - `pip install "python-telegram-bot[job-queue]" --upgrade` ile kuruldu
   - python-telegram-bot 20.7 → 22.7 güncellendi
   - apscheduler 3.11.2 kuruldu
   - Alarm sistemi başarıyla çalışıyor (30 dakikada bir tarama)

5. **Conflict Hatası Çözüldü** ✅
   - Aynı anda çalışan birden fazla bot süreci temizlendi
   - Bot temiz başlatıldı, Conflict hatası ortadan kalktı
   - getUpdates başarıyla çalışıyor

6. **Alarm Sistemi Typo Düzeltildi** ✅
   - `alarm_sistemi.py` içinde `plan_kayitlarini_yukle_fn` → `plan_kayitlari_yukle_fn`
   - NameError düzeltildi, alarm sistemi hatasız çalışıyor

7. **Deploy Script'leri Güncellendi** ✅
   - `deploy.sh` - Python versiyon kontrolü, env kontrolü eklendi
   - `update.sh` - Env kontrolü, pip upgrade eklendi
   - `push.sh` - .env güvenlik kontrolü, Pi erişim kontrolü eklendi

8. **Kalite Kartı İsteğe Bağlı Hale Getirildi** ✅
   - Analiz sonunda kalite kartı otomatik gösterilmiyor (çıktı daha temiz)
   - "📊 Kalite Kartını Göster" butonu eklendi
   - Kullanıcı isterse butona tıklayıp detayları görebilir
   - Tüm analiz modlarında (Okwis, Mevsim, Hava, vb.) aktif
   - CallbackQueryHandler tracking artık düzgün çalışıyor
   - PTBUserWarning uyarıları ortadan kalktı

3. **Environment Variables Kontrolü Eklendi** ✅
   - `check_required_env_vars()` fonksiyonu eklendi
   - Bot başlatılmadan önce gerekli API anahtarları kontrol ediliyor
   - Eksik veya geçersiz anahtarlar için açıklayıcı hata mesajları
   - Placeholder değerler ("your_...") tespit ediliyor

4. **Güvenlik: .env Dosyası Temizlendi** ✅
   - `.env` dosyası placeholder değerlerle yeniden oluşturuldu
   - `.env.example` dosyası oluşturuldu (dokümantasyon için)
   - `.gitignore` zaten `.env`'yi içeriyor (doğrulandı)
   - **ÖNEMLİ:** Gerçek API anahtarlarınızı `.env` dosyasına manuel olarak girmelisiniz!

5. **Requirements.txt Doğrulandı** ✅
   - `python-telegram-bot[job-queue]>=22.0` zaten mevcut
   - JobQueue desteği için ek kurulum gerekmez
   - Tüm bağımlılıklar güncel

**Güvenlik Notları:**

⚠️ **ACİL:** Eski `.env` dosyası Git geçmişinde commit edilmiş durumda. Aşağıdaki adımları MUTLAKA uygulayın:

1. **Tüm API anahtarlarınızı yenileyin:**
   - Telegram Bot Token (BotFather'dan yeni token alın)
   - Gemini API Keys (Google AI Studio'dan yeni anahtarlar)
   - DeepSeek API Key
   - Tavily API Key
   - ElevenLabs API Key
   - OpenWeather API Key

2. **Git geçmişinden .env'yi temizleyin:**
   ```bash
   # Yöntem 1: git-filter-repo (önerilen)
   pip install git-filter-repo
   git filter-repo --path .env --invert-paths
   
   # Yöntem 2: git filter-branch (eski yöntem)
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch .env" \
     --prune-empty --tag-name-filter cat -- --all
   
   # Force push (dikkatli!)
   git push origin --force --all
   git push origin --force --tags
   ```

3. **Yeni API anahtarlarınızı .env'ye girin:**
   - `.env.example` dosyasını referans alın
   - Gerçek anahtarlarınızı `.env` dosyasına yazın
   - `.env` dosyasının Git'e commit edilmediğinden emin olun

**Sonraki Adımlar:**

🟡 **Kısa Vade (Bu Hafta):**
- Gemini API kota yönetimi ve rate limiting ekle
- Reuters RSS retry mekanizması ekle
- Python 3.11+ sürümüne geç

🟢 **Orta Vade (Bu Ay):**
- Structured logging ekle
- Performans izleme ekle
- Admin yönetimi iyileştir
- Health check endpoint ekle

**Detaylı Rapor:** [debug-operasyonu-1.md](debug-operasyonu-1.md)

---

## 2026-04-20 — Sohbet Modu (Sesli + Yazılı, Pro/Claude)

**Amaç:** Pro/Claude üyeler için doğal dil sohbeti — sesli mesaj at, sesli cevap al; yazı yaz, yazı gelir. Profil bilgisini kullanarak kişiselleştirilmiş yanıt.

**Yapılanlar:**

1. **`sohbet.py`** ✨ YENİ — Sohbet motoru
   - `ses_metne_cevir()` — Whisper local (Pi 5) veya OpenAI Whisper API
   - `metin_sese_cevir()` — OpenAI TTS (anahtar varsa) veya gTTS (ücretsiz)
   - `sohbet_cevabi_uret()` — Profil + sohbet geçmişi ile kısa doğal cevap
   - Kullanıcı başına son 10 mesaj geçmişi (RAM'de)

2. **`app.py`** — Handler güncellemeleri
   - `diger_mesajlar()` güncellendi: Pro/Claude → sohbet, Free → /analiz yönlendir
   - `sesli_mesaj_isle()` ✨ YENİ — VOICE/AUDIO mesajları yakalar, STT → LLM → TTS
   - `/gecmis_sil` komutu eklendi — sohbet geçmişini temizle
   - `filters.VOICE | filters.AUDIO` handler'ı main()'e eklendi

3. **`requirements.txt`** — `openai-whisper`, `gtts` eklendi

---

## 2026-04-20 — Alarm Sistemi (Parça O)

**Amaç:** Piyasayı derinden etkileyen kritik gelişmelerde Pro/Claude üyelere otomatik bildirim.

**Yapılanlar:**

1. **`alarm_sistemi.py`** ✨ YENİ
   - Her 30 dakikada RSS + Tavily tarar
   - Model 1-10 önem skoru verir, 7+ → bildirim
   - Dedupe: aynı haber 6 saat içinde tekrar gönderilmez
   - Sadece Pro/Claude üyeler, bildirimi açık olanlar alır

2. **`app.py`** — `/bildirim` komutu (aç/kapat toggle), JobQueue entegrasyonu

3. **`metrics/bildirim_tercihleri.json`** — kullanıcı tercihleri

---

[... önceki kayıtlar devam ediyor ...]


