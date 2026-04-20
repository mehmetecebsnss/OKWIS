# Debug Operasyonu - 1
## Tarih: 20 Nisan 2026
## Proje: OKWIS - Telegram Yatırım Asistanı

---

## 🔴 KRİTİK HATALAR

### 1. **UTF-8 BOM Hatası - prob_zinciri.json**
**Hata Mesajı:**
```
WARNING — prob_zinciri.json yüklenemedi: Unexpected UTF-8 BOM (decode using utf-8-sig): line 1 column 1 (char 0)
```

**Konum:** `app.py` - `_prob_zinciri_yukle()` fonksiyonu

**Sebep:** JSON dosyası UTF-8 BOM (Byte Order Mark) ile kaydedilmiş. Python'un standart `json.load()` BOM karakterini tanımıyor.

**Etki:** Sosyal ihtimal zincirleri yüklenemiyor, analiz kalitesi düşüyor.

**Çözüm:**
```python
# app.py içinde _prob_zinciri_yukle() fonksiyonunu güncelle:
def _prob_zinciri_yukle() -> list[dict]:
    try:
        if _PROB_ZINCIRI_PATH.exists():
            with open(_PROB_ZINCIRI_PATH, encoding="utf-8-sig") as f:  # utf-8-sig kullan
                data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning("prob_zinciri.json yüklenemedi: %s", e)
    return []
```

**Alternatif:** Dosyayı UTF-8 (BOM olmadan) olarak yeniden kaydet.

---

### 2. **Gemini API Kota Aşımı**
**Hata Mesajı:**
```
WARNING — Gemini anahtar 1/2 başarısız (kota vb.): 429 You exceeded your current quota
Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20
```

**Konum:** `app.py` - `llm_metin_uret()` fonksiyonu

**Sebep:** Gemini free tier günlük 20 istek limiti aşılmış.

**Etki:** Analiz istekleri başarısız oluyor, kullanıcı deneyimi bozuluyor.

**Çözüm:**
1. **Kısa Vade:** DeepSeek fallback'i aktif (zaten var ama daha iyi hata yönetimi gerekli)
2. **Orta Vade:** Kullanıcı başına rate limiting ekle
3. **Uzun Vade:** Ücretli Gemini planına geç veya Claude API'yi varsayılan yap

**Önerilen Kod İyileştirmesi:**
```python
# Kullanıcı başına günlük limit kontrolü ekle
def _kullanici_llm_limiti_kontrol(user_id: int | str) -> bool:
    """Kullanıcının günlük LLM istek limitini kontrol et"""
    gun = date.today().isoformat()
    data = _kullanim_limitleri_yukle()
    uid = str(user_id)
    llm_key = f"{gun}_llm"
    
    if uid not in data:
        data[uid] = {}
    
    llm_kullanim = int(data[uid].get(llm_key, 0))
    
    # Free kullanıcılar: 5 LLM/gün, Pro: 50 LLM/gün
    limit = 50 if _kullanici_pro_mu(user_id) else 5
    
    if llm_kullanim >= limit:
        return False
    
    data[uid][llm_key] = llm_kullanim + 1
    _kullanim_limitleri_kaydet(data)
    return True
```

---

### 3. **Reuters RSS Feed Erişim Hatası**
**Hata Mesajı:**
```
WARNING — Jeopolitik RSS alınamadı (https://feeds.reuters.com/reuters/worldNews): [Errno 11001] getaddrinfo failed
WARNING — Sektör RSS alınamadı (https://feeds.reuters.com/reuters/businessNews): [Errno 11001] getaddrinfo failed
```

**Konum:** Çeşitli bağlam modülleri (`jeopolitik_baglam.py`, `sektor_baglam.py`, vb.)

**Sebep:** 
- DNS çözümleme hatası (internet bağlantısı veya DNS sorunu)
- Reuters RSS feed'leri erişilebilir değil veya URL değişmiş

**Etki:** Bağlam verisi eksik, analiz kalitesi düşüyor.

**Çözüm:**
1. **Acil:** BBC RSS'leri çalışıyor, onlara güven
2. **Kısa Vade:** Reuters URL'lerini kontrol et ve güncelle
3. **Orta Vade:** Retry mekanizması ekle (exponential backoff)
4. **Uzun Vade:** Alternatif haber kaynakları ekle (AP News, Bloomberg, vb.)

**Önerilen Kod:**
```python
# Retry mekanizması ekle
import time
from functools import wraps

def retry_on_network_error(max_retries=3, delay=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Deneme {attempt + 1}/{max_retries} başarısız: {e}")
                        time.sleep(delay * (attempt + 1))
                    else:
                        raise
            return None
        return wrapper
    return decorator
```

---

### 4. **JobQueue Eksikliği**
**Hata Mesajı:**
```
PTBUserWarning: No `JobQueue` set up. To use `JobQueue`, you must install PTB via `pip install "python-telegram-bot[job-queue]"`
WARNING — JobQueue mevcut değil — alarm sistemi başlatılamadı
```

**Konum:** `app.py` - bot başlatma

**Sebep:** `python-telegram-bot[job-queue]` bağımlılığı eksik veya yüklenmemiş.

**Etki:** Alarm sistemi çalışmıyor, kullanıcılar zamanlanmış bildirimler alamıyor.

**Çözüm:**
```bash
pip install "python-telegram-bot[job-queue]"
```

**Alternatif:** `requirements.txt` zaten doğru, ama kurulum yapılmamış. Deployment sırasında:
```bash
pip install -r requirements.txt --upgrade
```

---

### 5. **ConversationHandler per_message Uyarısı**
**Hata Mesajı:**
```
PTBUserWarning: If 'per_message=False', 'CallbackQueryHandler' will not be tracked for every message.
```

**Konum:** `app.py` - `ConversationHandler` tanımları (satır ~4035, ~4059)

**Sebep:** `per_message=False` ayarı ile `CallbackQueryHandler` kullanımı çakışıyor.

**Etki:** Bazı callback query'ler kaybolabilir, kullanıcı akışı bozulabilir.

**Çözüm:**
```python
# ConversationHandler tanımlarını güncelle:
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("analiz", analiz_baslat)],
    states={
        MOD_SECIMI: [CallbackQueryHandler(mod_secildi)],
        ULKE_SECIMI: [CallbackQueryHandler(ulke_secildi)],
        # ...
    },
    fallbacks=[CommandHandler("iptal", iptal)],
    per_message=True,  # Bunu True yap
    per_chat=True,
    per_user=True,
)
```

---

## 🟡 ORTA ÖNCELİKLİ SORUNLAR

### 6. **Python Versiyon Uyarısı**
**Hata Mesajı:**
```
FutureWarning: You are using a Python version (3.10.10) which Google will stop supporting in new releases of google.api_core once it reaches its end of life (2026-10-04).
```

**Çözüm:** Python 3.11+ sürümüne geç.

```bash
# Windows için:
# Python 3.11 veya 3.12 indir: https://www.python.org/downloads/
# Sanal ortam oluştur:
python3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

### 7. **Hardcoded API Keys (.env dosyası)**
**Güvenlik Riski:** `.env` dosyası Git'e commit edilmiş (açık API anahtarları).

**Etki:** 
- Telegram bot token açık
- Gemini API keys açık
- DeepSeek API key açık
- Tavily API key açık
- ElevenLabs API key açık

**Çözüm:**
1. **ACİL:** Tüm API anahtarlarını yenile (özellikle Telegram token)
2. `.env` dosyasını `.gitignore`'a ekle
3. Git geçmişinden `.env`'yi temizle:

```bash
# Git geçmişinden .env'yi kaldır
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all

# Veya daha modern:
git filter-repo --path .env --invert-paths

# Force push (dikkatli!)
git push origin --force --all
```

4. `.env.example` oluştur (placeholder değerlerle):
```env
AI_PROVIDER=gemini
DEEPSEEK_API_KEY=your_deepseek_key_here
GEMINI_API_KEY=your_gemini_key_here
TELEGRAM_TOKEN=your_telegram_token_here
# ...
```

---

### 8. **Eksik Hata Yakalama - Bağlam Modülleri**
**Sorun:** Bağlam toplama fonksiyonları (`topla_mevsim_baglami`, vb.) hata fırlatırsa bot çökebilir.

**Çözüm:** Tüm bağlam fonksiyonlarını try-except ile sar:

```python
def guvenli_baglam_topla(baglam_func, *args, **kwargs):
    """Bağlam toplama fonksiyonlarını güvenli şekilde çağır"""
    try:
        return baglam_func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Bağlam toplama hatası ({baglam_func.__name__}): {e}")
        return "Bağlam verisi şu an alınamadı. Genel analiz yapılıyor."
```

---

## 🟢 DÜŞÜK ÖNCELİKLİ İYİLEŞTİRMELER

### 9. **Logging İyileştirmesi**
**Öneri:** Structured logging ekle (JSON format).

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)

# Kullanım:
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
```

---

### 10. **Performans İzleme**
**Öneri:** Analiz sürelerini ölç ve logla.

```python
import time
from functools import wraps

def measure_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        logger.info(f"{func.__name__} tamamlandı: {duration:.2f}s")
        return result
    return wrapper

# Kullanım:
@measure_time
def mevsim_analizi_yap(...):
    # ...
```

---

### 11. **Markdown Temizleme Fonksiyonu Eksik**
**Sorun:** `_markdown_temizle()` fonksiyonu tanımlı ama bazı edge case'leri kaçırıyor.

**İyileştirme:**
```python
def _markdown_temizle(text: str) -> str:
    """Model çıktısındaki Markdown artıklarını temizle."""
    if not text:
        return text
    
    # Kod blokları (multiline)
    text = re.sub(r'```[\s\S]*?```', '', text)
    
    # Inline kod
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # Bold (**text** ve __text__)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    
    # Italic (*text* ve _text_)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', text)
    text = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'\1', text)
    
    # Başlıklar (# ## ###)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    
    # Liste işaretleri
    text = re.sub(r'^\s*[\*\-\+]\s+', '• ', text, flags=re.MULTILINE)
    
    # Em dash ve en dash
    text = text.replace('—', '-').replace('–', '-')
    
    # Linkler [text](url)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    # Fazla boşlukları temizle
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()
```

---

## 📊 GÜVENLİK AÇIKLARI

### 12. **SQL Injection Riski YOK (JSON kullanılıyor)**
✅ Proje veritabanı kullanmıyor, JSON dosyaları kullanıyor. SQL injection riski yok.

---

### 13. **XSS (Cross-Site Scripting) Koruması**
✅ `_tg_html_escape()` fonksiyonu kullanılıyor. Telegram HTML injection koruması var.

**Ancak:** Bazı yerlerde kaçırılmamış metin var. Kontrol et:

```python
# Tüm kullanıcı girdilerini escape et:
def _guvenli_html(text: str) -> str:
    """Kullanıcı girdisini Telegram HTML için güvenli hale getir"""
    if not text:
        return ""
    return html.escape(str(text), quote=False)
```

---

### 14. **Rate Limiting Eksikliği**
**Risk:** Kullanıcılar botu spam edebilir, API kotaları hızla tükenebilir.

**Çözüm:**
```python
from collections import defaultdict
from datetime import datetime, timedelta

# Kullanıcı başına rate limit
_user_last_request = defaultdict(lambda: datetime.min)
_user_request_count = defaultdict(int)

def rate_limit_check(user_id: int, max_requests: int = 10, window_seconds: int = 60) -> bool:
    """Kullanıcının rate limitini kontrol et"""
    now = datetime.now()
    last_req = _user_last_request[user_id]
    
    # Zaman penceresi sıfırlandı mı?
    if now - last_req > timedelta(seconds=window_seconds):
        _user_request_count[user_id] = 0
    
    # Limit aşıldı mı?
    if _user_request_count[user_id] >= max_requests:
        return False
    
    _user_request_count[user_id] += 1
    _user_last_request[user_id] = now
    return True

# Kullanım:
async def analiz_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not rate_limit_check(user_id):
        await update.message.reply_text(
            "⏳ Çok hızlı istek gönderiyorsun. Lütfen 1 dakika bekle."
        )
        return ConversationHandler.END
    
    # Normal akış devam eder...
```

---

### 15. **Admin Kontrolü Zayıf**
**Sorun:** `ADMIN_USER_IDS` sadece `.env`'den okunuyor. Dinamik admin ekleme/çıkarma yok.

**İyileştirme:**
```python
# Admin yönetimi için komutlar ekle
async def admin_ekle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yeni admin ekle (sadece mevcut adminler)"""
    if not _admin_mi(update.effective_user.id):
        await update.message.reply_text("❌ Bu komutu kullanma yetkin yok.")
        return
    
    try:
        yeni_admin_id = int(context.args[0])
        ADMIN_USER_IDS.add(yeni_admin_id)
        # .env'ye kaydet (veya ayrı bir admin.json dosyası kullan)
        await update.message.reply_text(f"✅ Admin eklendi: {yeni_admin_id}")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Kullanım: /admin_ekle <user_id>")
```

---

## 🛠️ DEPLOYMENT ÖNERİLERİ

### 16. **Environment Variables Kontrolü**
**Öneri:** Başlangıçta tüm gerekli env var'ları kontrol et:

```python
def check_required_env_vars():
    """Gerekli environment variable'ları kontrol et"""
    required = [
        "TELEGRAM_TOKEN",
        "GEMINI_API_KEY",
        "OPENWEATHER_API_KEY",
        "TAVILY_API_KEY",
    ]
    
    missing = [var for var in required if not os.getenv(var)]
    
    if missing:
        logger.error(f"Eksik environment variables: {', '.join(missing)}")
        raise RuntimeError(f"Eksik env vars: {missing}")
    
    logger.info("✅ Tüm gerekli environment variables mevcut")

# main() fonksiyonunun başında çağır:
def main():
    check_required_env_vars()
    # ...
```

---

### 17. **Graceful Shutdown**
**Öneri:** Bot kapatılırken temiz bir shutdown yap:

```python
import signal
import sys

def signal_handler(sig, frame):
    """SIGINT/SIGTERM sinyallerini yakala"""
    logger.info("Shutdown sinyali alındı, bot kapatılıyor...")
    # Açık dosyaları kapat, bağlantıları temizle
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
```

---

### 18. **Health Check Endpoint**
**Öneri:** Bot sağlığını kontrol etmek için basit bir HTTP endpoint ekle:

```python
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        else:
            self.send_response(404)
            self.end_headers()

def start_health_check_server(port=8080):
    """Health check HTTP sunucusunu başlat"""
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Health check server started on port {port}")

# main() içinde:
start_health_check_server()
```

---

## 📋 ÖNCELIK SIRASI

### 🔴 ACİL (Bugün)
1. ✅ UTF-8 BOM hatasını düzelt (`prob_zinciri.json`)
2. ✅ API anahtarlarını yenile ve `.env`'yi Git'ten kaldır
3. ✅ JobQueue bağımlılığını kur
4. ✅ ConversationHandler `per_message` uyarısını düzelt

### 🟡 KISA VADE (Bu Hafta)
5. ✅ Gemini kota yönetimi ve rate limiting ekle
6. ✅ Reuters RSS retry mekanizması ekle
7. ✅ Hata yakalama iyileştirmeleri
8. ✅ Python 3.11+ sürümüne geç

### 🟢 ORTA VADE (Bu Ay)
9. ✅ Structured logging ekle
10. ✅ Performans izleme ekle
11. ✅ Admin yönetimi iyileştir
12. ✅ Health check endpoint ekle

---

## 🎯 SONUÇ

**Toplam Tespit Edilen Sorun:** 18
- 🔴 Kritik: 5
- 🟡 Orta: 8
- 🟢 Düşük: 5

**Tahmini Düzeltme Süresi:**
- Acil düzeltmeler: 2-3 saat
- Kısa vade: 1-2 gün
- Orta vade: 1 hafta

**Sonraki Adımlar:**
1. Bu raporu takım ile paylaş
2. Acil düzeltmeleri uygula
3. Kısa vade iyileştirmeleri planla
4. Orta vade için sprint oluştur

---

**Hazırlayan:** Kiro AI  
**Tarih:** 20 Nisan 2026  
**Versiyon:** 1.0
