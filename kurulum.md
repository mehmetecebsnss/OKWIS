# Makro Lens — Kurulum Kılavuzu (Sıfırdan)

Hiç Python bilmesen bile bu adımları takip edersen bot çalışır.

---

## Adım 1 — Python Kur

1. https://python.org/downloads adresine git
2. "Download Python 3.12" butonuna tıkla
3. İndir ve kur
4. Kurulum sırasında **"Add Python to PATH"** kutusunu işaretle (önemli!)

Kuruldu mu kontrol et: Terminal/Komut İstemi aç, şunu yaz:
```
python --version
```
`Python 3.12.x` yazıyorsa tamam.

---

## Adım 2 — Telegram Bot Token Al

1. Telegram'da **@BotFather**'ı aç
2. `/newbot` yaz
3. Bot ismi gir: `Makro Lens`
4. Bot kullanıcı adı gir: `makrolens_bot` (sonu _bot bitmeli, benzersiz olmalı)
5. BotFather sana şöyle bir token verecek:
   ```
   1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
   ```
6. Bu tokeni bir yere kaydet.

---

## Adım 3 — Gemini API Key Al

1. https://aistudio.google.com/app/apikey adresine git
2. Google hesabınla giriş yap
3. "Create API Key" butonuna tıkla
4. Çıkan uzun metni kopyala ve bir yere kaydet

---

## Adım 4 — Proje Klasörünü Hazırla

Bu repoyu klonladıysan veya `Makro-Lens` klasörünü kullanıyorsan proje kökünde şunlar olmalı:
- `app.py` — bot mantığı
- `main.py` — isteğe bağlı giriş (`python main.py` → `app.main()`)
- `requirements.txt`
- `.env` (aşağıda anlatıyorum; repoda yok, sen oluşturursun)

Mimari ve sıradaki işler: [MIMARI.md](MIMARI.md), [SURUM_VE_YOL_HARITASI.md](SURUM_VE_YOL_HARITASI.md).

### .env dosyası oluştur

Repoda [`.env.example`](.env.example) şablonu var; kopyalayıp `.env` yapabilirsin.

Notepad aç, şunu yaz (kendi tokenlarını yaz):
```
TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
GEMINI_API_KEY=AIzaSy...seninkeyburada

# İsteğe bağlı — DeepSeek API (kullanım başına ücretlendirme; ücretsiz deneme kredisi platforma göre değişir)
# AI_PROVIDER=deepseek
# DEEPSEEK_API_KEY=sk-...
# DeepSeek bakiye/kota hatasında otomatik Gemini: AI_FALLBACK_GEMINI=true ve GEMINI_API_KEY dolu olmalı
# Ücret ödemek istemezsen: AI_PROVIDER=gemini veya anahtarı kaldır

# Hava modu: OPENWEATHER_API_KEY (openweathermap.org). Diğer isteğe bağlı anahtarlar: .env.example
```

"Farklı Kaydet" ile proje köküne (ör. `Makro-Lens`) `.env` adıyla kaydet.
(Uzantı seçerken "Tüm Dosyalar" seç, dosya adını `.env` yaz)

---

## Adım 5 — Kütüphaneleri Kur

Terminal aç (Windows: Başlat → "cmd" yaz → Enter).

Proje klasörüne git (yolunu kendi kurulumuna göre düzenle):
```
cd Desktop\Unsar\Makro-Lens
```

Kütüphaneleri kur:
```
pip install -r requirements.txt
```

Birkaç dakika bekle, indirme tamamlanacak.

---

## Adım 6 — Botu Çalıştır

Aynı terminalde (ikisi de aynı botu başlatır):
```
python main.py
```
veya
```
python app.py
```

`Bot başlatıldı...` yazısını görürsen başarılı!

---

## Adım 7 — Test Et

1. Telegram'ı aç
2. Kendi botunu bul (@makrolens_bot gibi)
3. `/start` yaz
4. `/analiz` yaz
5. Mevsimler → Türkiye seç
6. 10-15 saniye bekle, analiz gelecek

---

## Sık Karşılaşılan Sorunlar

**"python bulunamadı" hatası:**
Python kurulumunda PATH seçeneğini işaretlemedin. Python'u kaldırıp tekrar kur.

**"ModuleNotFoundError" hatası:**
`pip install -r requirements.txt` komutunu doğru klasörde çalıştır.

**Bot cevap vermiyor:**
`.env` dosyasındaki tokenları kontrol et. Boşluk veya tırnak işareti olmamalı.

**"Invalid token" hatası:**
BotFather'dan aldığın tokenı tam kopyaladığından emin ol.

---

## Bot Durdurma

Terminalde `Ctrl + C` tuşuna bas.

---

## Sonraki Adımlar

Öncelik sırası [SURUM_VE_YOL_HARITASI.md](SURUM_VE_YOL_HARITASI.md) ve [MIMARI.md](MIMARI.md) ile uyumlu:
- Önce Mevsim modunu derinleştir (bağlam, footer, prompt)
- Sonra Hava / Jeopolitik ve diğer modlar
- Kullanıcı limiti ve deploy