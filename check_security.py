#!/usr/bin/env python3
"""
Okwis AI - Güvenlik Kontrol Scripti
.env dosyasındaki API key'lerin güvenliğini kontrol eder
"""

import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Renkli çıktı için
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def check_env_file_exists():
    """Check if .env file exists"""
    env_path = Path(".env")
    if not env_path.exists():
        print(f"{Colors.RED}❌ .env dosyası bulunamadı!{Colors.END}")
        print(f"{Colors.YELLOW}💡 .env.example'ı kopyalayın: cp .env.example .env{Colors.END}")
        return False
    print(f"{Colors.GREEN}✅ .env dosyası mevcut{Colors.END}")
    return True

def check_gitignore():
    """Check if .env is in .gitignore"""
    gitignore_path = Path(".gitignore")
    if not gitignore_path.exists():
        print(f"{Colors.RED}❌ .gitignore dosyası bulunamadı!{Colors.END}")
        return False
    
    with open(gitignore_path, 'r') as f:
        content = f.read()
    
    if '.env' in content:
        print(f"{Colors.GREEN}✅ .env .gitignore'da{Colors.END}")
        return True
    else:
        print(f"{Colors.RED}❌ .env .gitignore'da DEĞİL!{Colors.END}")
        print(f"{Colors.YELLOW}💡 .gitignore'a ekleyin: echo '.env' >> .gitignore{Colors.END}")
        return False

def check_git_history():
    """Check if .env was ever committed"""
    import subprocess
    try:
        result = subprocess.run(
            ['git', 'log', '--all', '--full-history', '--', '.env'],
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            print(f"{Colors.RED}❌ .env GIT GEÇMİŞİNDE VAR!{Colors.END}")
            print(f"{Colors.YELLOW}💡 Acilen temizleyin ve key'leri rotate edin!{Colors.END}")
            return False
        else:
            print(f"{Colors.GREEN}✅ .env git geçmişinde yok{Colors.END}")
            return True
    except Exception as e:
        print(f"{Colors.YELLOW}⚠️  Git kontrolü yapılamadı: {e}{Colors.END}")
        return True

def check_api_keys():
    """Check if API keys are set and valid format"""
    load_dotenv()
    
    issues = []
    warnings = []
    
    # Gemini keys
    gemini_keys = []
    for i in range(1, 11):
        suffix = "" if i == 1 else f"_{i}"
        key = os.getenv(f"GEMINI_API_KEY{suffix}", "").strip()
        if key:
            gemini_keys.append(key)
            
            # Check if it's a placeholder
            if "your_" in key.lower() or "here" in key.lower():
                issues.append(f"GEMINI_API_KEY{suffix} placeholder değer içeriyor")
            
            # Check format (should start with AIzaSy)
            elif not key.startswith("AIzaSy"):
                warnings.append(f"GEMINI_API_KEY{suffix} geçersiz format (AIzaSy ile başlamalı)")
    
    if gemini_keys:
        print(f"{Colors.GREEN}✅ {len(gemini_keys)} Gemini API key bulundu{Colors.END}")
    else:
        issues.append("Hiç Gemini API key yok!")
    
    # DeepSeek key
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if deepseek_key:
        if "your_" in deepseek_key.lower() or "here" in deepseek_key.lower():
            issues.append("DEEPSEEK_API_KEY placeholder değer içeriyor")
        elif not deepseek_key.startswith("sk-"):
            warnings.append("DEEPSEEK_API_KEY geçersiz format (sk- ile başlamalı)")
        else:
            print(f"{Colors.GREEN}✅ DeepSeek API key bulundu{Colors.END}")
    else:
        warnings.append("DeepSeek API key yok (opsiyonel)")
    
    # Claude key
    claude_key = os.getenv("CLAUDE_API_KEY", "").strip()
    if claude_key:
        if "your_" in claude_key.lower() or "here" in claude_key.lower():
            issues.append("CLAUDE_API_KEY placeholder değer içeriyor")
        elif not claude_key.startswith("sk-ant-"):
            warnings.append("CLAUDE_API_KEY geçersiz format (sk-ant- ile başlamalı)")
        else:
            print(f"{Colors.GREEN}✅ Claude API key bulundu{Colors.END}")
    else:
        warnings.append("Claude API key yok (opsiyonel)")
    
    # Telegram token
    telegram_token = os.getenv("TELEGRAM_TOKEN", "").strip()
    if telegram_token:
        if "your_" in telegram_token.lower() or "here" in telegram_token.lower():
            issues.append("TELEGRAM_TOKEN placeholder değer içeriyor")
        elif not re.match(r'^\d+:[A-Za-z0-9_-]+$', telegram_token):
            warnings.append("TELEGRAM_TOKEN geçersiz format")
        else:
            print(f"{Colors.GREEN}✅ Telegram token bulundu{Colors.END}")
    else:
        issues.append("TELEGRAM_TOKEN yok!")
    
    # Other APIs
    openweather = os.getenv("OPENWEATHER_API_KEY", "").strip()
    if openweather and "your_" not in openweather.lower():
        print(f"{Colors.GREEN}✅ OpenWeather API key bulundu{Colors.END}")
    else:
        warnings.append("OpenWeather API key yok veya placeholder")
    
    tavily = os.getenv("TAVILY_API_KEY", "").strip()
    if tavily and "your_" not in tavily.lower():
        print(f"{Colors.GREEN}✅ Tavily API key bulundu{Colors.END}")
    else:
        warnings.append("Tavily API key yok veya placeholder")
    
    return issues, warnings

def check_key_exposure():
    """Check if keys might be exposed in code"""
    print(f"\n{Colors.BLUE}🔍 Kod içinde hardcoded key kontrolü...{Colors.END}")
    
    exposed = []
    
    # Check Python files
    for py_file in Path(".").rglob("*.py"):
        if "venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
        
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for potential API keys
            if re.search(r'AIzaSy[A-Za-z0-9_-]{33}', content):
                exposed.append(f"{py_file}: Gemini key bulundu!")
            if re.search(r'sk-[A-Za-z0-9]{48}', content):
                exposed.append(f"{py_file}: DeepSeek/OpenAI key bulundu!")
            if re.search(r'\d{10}:[A-Za-z0-9_-]{35}', content):
                exposed.append(f"{py_file}: Telegram token bulundu!")
        except Exception:
            pass
    
    if exposed:
        print(f"{Colors.RED}❌ Kod içinde hardcoded key'ler bulundu:{Colors.END}")
        for exp in exposed:
            print(f"   {Colors.RED}• {exp}{Colors.END}")
        return False
    else:
        print(f"{Colors.GREEN}✅ Kod içinde hardcoded key yok{Colors.END}")
        return True

def main():
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}🔒 Okwis AI - Güvenlik Kontrolü{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
    
    all_good = True
    
    # 1. .env file exists
    if not check_env_file_exists():
        all_good = False
    
    # 2. .gitignore check
    if not check_gitignore():
        all_good = False
    
    # 3. Git history check
    if not check_git_history():
        all_good = False
    
    # 4. API keys check
    print(f"\n{Colors.BLUE}🔑 API Key Kontrolü...{Colors.END}")
    issues, warnings = check_api_keys()
    
    if issues:
        print(f"\n{Colors.RED}❌ KRİTİK SORUNLAR:{Colors.END}")
        for issue in issues:
            print(f"   {Colors.RED}• {issue}{Colors.END}")
        all_good = False
    
    if warnings:
        print(f"\n{Colors.YELLOW}⚠️  UYARILAR:{Colors.END}")
        for warning in warnings:
            print(f"   {Colors.YELLOW}• {warning}{Colors.END}")
    
    # 5. Code exposure check
    if not check_key_exposure():
        all_good = False
    
    # Final verdict
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    if all_good and not issues:
        print(f"{Colors.GREEN}{Colors.BOLD}✅ GÜVENLİK KONTROLÜ BAŞARILI!{Colors.END}")
        print(f"{Colors.GREEN}Tüm API key'ler güvenli görünüyor.{Colors.END}")
    else:
        print(f"{Colors.RED}{Colors.BOLD}❌ GÜVENLİK SORUNLARI BULUNDU!{Colors.END}")
        print(f"{Colors.RED}Lütfen yukarıdaki sorunları düzeltin.{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
    
    # Recommendations
    print(f"{Colors.BLUE}💡 ÖNERİLER:{Colors.END}")
    print(f"   1. API key'leri düzenli rotate edin (30 günde bir)")
    print(f"   2. Production'da environment variables kullanın")
    print(f"   3. Secrets manager kullanmayı düşünün (AWS, GCP, Azure)")
    print(f"   4. .env dosyasını asla paylaşmayın")
    print(f"   5. Sızdırılmış key'leri hemen iptal edin\n")

if __name__ == "__main__":
    main()
