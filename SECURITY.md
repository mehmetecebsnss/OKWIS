# Okwis AI - Güvenlik Politikası

**Son Güncelleme:** 30 Nisan 2026

---

## 🔒 API Key Güvenliği

### Genel Kurallar

1. **ASLA** API key'leri kod içine yazmayın (hardcode)
2. **ASLA** .env dosyasını GitHub'a commit etmeyin
3. **ASLA** API key'leri public olarak paylaşmayın
4. **HER ZAMAN** .env.example kullanın (template)
5. **DÜZENLI** olarak key'leri rotate edin (30 günde bir)

---

## 📁 Dosya Yapısı

```
okwis/
├── .env                 # GİZLİ - Gerçek API key'ler (GİT'E GİTMEZ)
├── .env.example         # PUBLIC - Template (GİT'E GİDER)
├── .gitignore           # .env burada olmalı
└── check_security.py    # Güvenlik kontrol scripti
```

---

## 🚀 Kurulum (Yeni Geliştirici)

### 1. Repo'yu Clone'la
```bash
git clone https://github.com/your-username/okwis.git
cd okwis
```

### 2. .env Dosyası Oluştur
```bash
# .env.example'ı kopyala
cp .env.example .env

# Gerçek API key'lerini gir
nano .env  # veya favori editörünüz
```

### 3. API Key'leri Al

#### Gemini (Ücretsiz)
1. https://aistudio.google.com/app/apikey
2. "Create API Key" tıkla
3. Key'i kopyala → .env'e yapıştır

#### DeepSeek (Ücretli)
1. https://platform.deepseek.com/
2. Sign up / Login
3. API Keys → Create new key
4. Key'i kopyala → .env'e yapıştır

#### Telegram Bot
1. Telegram'da @BotFather'ı aç
2. `/newbot` komutunu gönder
3. Bot adı ve username belirle
4. Token'ı kopyala → .env'e yapıştır

#### OpenWeatherMap (Ücretsiz)
1. https://openweathermap.org/api
2. Sign up / Login
3. API Keys → Create key
4. Key'i kopyala → .env'e yapıştır

#### Tavily (Ücretsiz/Ücretli)
1. https://tavily.com/
2. Sign up / Login
3. API Key → Copy
4. Key'i kopyala → .env'e yapıştır

### 4. Güvenlik Kontrolü Yap
```bash
python check_security.py
```

Tüm kontroller ✅ olmalı!

---

## 🔄 API Key Rotation (Yenileme)

### Ne Zaman?
- Her 30 günde bir (rutin)
- Key sızdırıldığında (acil)
- Ekip üyesi ayrıldığında (acil)
- Şüpheli aktivite tespit edildiğinde (acil)

### Nasıl?

#### 1. Yeni Key Al
```bash
# Örnek: Gemini
# 1. https://aistudio.google.com/app/apikey
# 2. Yeni key oluştur
# 3. .env'e ekle (GEMINI_API_KEY_9 gibi)
```

#### 2. Bot'u Test Et
```bash
# Yeni key ile test
python main.py
# Telegram'da /analiz dene
```

#### 3. Eski Key'i İptal Et
```bash
# Google AI Studio'da eski key'i sil
# Veya devre dışı bırak
```

#### 4. .env'den Eski Key'i Sil
```bash
# .env dosyasından eski key'i kaldır
nano .env
```

---

## 🚨 Key Sızdırıldıysa Ne Yapmalı?

### Acil Adımlar (5 dakika içinde)

1. **Key'i Hemen İptal Et**
   ```bash
   # Provider'ın dashboard'una git
   # Key'i devre dışı bırak veya sil
   ```

2. **Yeni Key Al**
   ```bash
   # Yeni key oluştur
   # .env'e ekle
   ```

3. **Bot'u Yeniden Başlat**
   ```bash
   # Eski bot'u durdur
   pkill -f "python main.py"
   
   # Yeni bot'u başlat
   python main.py
   ```

4. **GitHub'ı Temizle** (eğer commit edildiyse)
   ```bash
   # Git geçmişinden .env'i sil
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch .env" \
     --prune-empty --tag-name-filter cat -- --all
   
   # Force push (DİKKAT: Tehlikeli!)
   git push origin --force --all
   ```

5. **Ekibi Bilgilendir**
   ```bash
   # Slack/Discord/Email ile ekibe haber ver
   # Herkes yeni key'i alsın
   ```

---

## 🛡️ Production Güvenliği

### Environment Variables (Önerilen)

```bash
# Railway
railway variables set GEMINI_API_KEY="AIzaSy..."

# Heroku
heroku config:set GEMINI_API_KEY="AIzaSy..."

# Docker
docker run -e GEMINI_API_KEY="AIzaSy..." okwis

# Systemd
Environment="GEMINI_API_KEY=AIzaSy..."
```

### Secrets Manager (İdeal)

#### AWS Secrets Manager
```python
import boto3
from botocore.exceptions import ClientError

def get_secret(secret_name):
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name='us-east-1'
    )
    
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except ClientError as e:
        raise e

# Kullanım
gemini_key = get_secret('okwis/gemini-api-key')
```

#### Google Cloud Secret Manager
```python
from google.cloud import secretmanager

def get_secret(project_id, secret_id):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# Kullanım
gemini_key = get_secret('okwis-prod', 'gemini-api-key')
```

---

## 📊 Güvenlik Kontrol Listesi

### Geliştirme Öncesi
- [ ] .env dosyası oluşturuldu
- [ ] Tüm API key'ler girildi
- [ ] `python check_security.py` çalıştırıldı
- [ ] Tüm kontroller ✅

### Her Commit Öncesi
- [ ] .env commit edilmedi
- [ ] Hardcoded key yok
- [ ] Sensitive data yok

### Her 30 Günde
- [ ] API key'ler rotate edildi
- [ ] Eski key'ler iptal edildi
- [ ] Güvenlik kontrolü yapıldı

### Production Deploy Öncesi
- [ ] Environment variables ayarlandı
- [ ] .env production'da yok
- [ ] Secrets manager kullanılıyor (ideal)
- [ ] Monitoring aktif

---

## 🔍 Güvenlik Taraması

### Manuel Kontrol
```bash
# Güvenlik scripti
python check_security.py

# Git geçmişi kontrolü
git log --all --full-history -- .env

# Kod içinde key arama
grep -r "AIzaSy" --include="*.py" .
grep -r "sk-" --include="*.py" .
```

### Otomatik Kontrol (CI/CD)
```yaml
# .github/workflows/security.yml
name: Security Check

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Check for secrets
        run: |
          python check_security.py
          # Fail if .env is committed
          if git ls-files | grep -q "^.env$"; then
            echo "ERROR: .env file is committed!"
            exit 1
          fi
```

---

## 📞 Güvenlik Sorunu Bildirimi

Güvenlik açığı tespit ederseniz:

1. **ASLA** public issue açmayın
2. **HEMEN** admin'e email gönderin: security@okwis.ai
3. Detayları açıklayın (nasıl reproduce edilir)
4. 24 saat içinde yanıt alacaksınız

---

## 📚 Kaynaklar

- [OWASP API Security](https://owasp.org/www-project-api-security/)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/)
- [Google Cloud Secret Manager](https://cloud.google.com/secret-manager)

---

**Hazırlayan:** Okwis AI Team  
**Tarih:** 30 Nisan 2026  
**Versiyon:** 1.0
