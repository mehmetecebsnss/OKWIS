"""
Okwis AI — Sohbet Modülü
Pro/Claude üyeler için doğal dil sohbeti.
Sesli mesaj → Whisper (local) → metin → LLM → cevap
Yazılı mesaj → LLM → cevap
Sesli giriş → sesli çıkış, yazılı giriş → yazılı çıkış.
"""

from __future__ import annotations

import io
import logging
import os
import tempfile
from collections import deque
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Kullanıcı başına sohbet geçmişi (son 10 mesaj)
_SOHBET_GECMISI: dict[str, deque] = {}
_GECMIS_LIMIT = 10


# ── Sohbet Geçmişi ────────────────────────────────────────────────────────────

def gecmis_ekle(user_id: int | str, rol: str, icerik: str) -> None:
    """Sohbet geçmişine mesaj ekle. rol: 'user' veya 'assistant'"""
    uid = str(user_id)
    if uid not in _SOHBET_GECMISI:
        _SOHBET_GECMISI[uid] = deque(maxlen=_GECMIS_LIMIT)
    _SOHBET_GECMISI[uid].append({"rol": rol, "icerik": icerik.strip()})


def gecmis_al(user_id: int | str) -> list[dict]:
    uid = str(user_id)
    return list(_SOHBET_GECMISI.get(uid, []))


def gecmis_temizle(user_id: int | str) -> None:
    uid = str(user_id)
    if uid in _SOHBET_GECMISI:
        _SOHBET_GECMISI[uid].clear()


# ── Speech-to-Text (Whisper local) ────────────────────────────────────────────

def ses_metne_cevir(ses_verisi: bytes, dosya_adi: str = "ses.ogg") -> str:
    """
    Ses verisini metne çevir.
    Önce local Whisper dener, yoksa OpenAI Whisper API'ye düşer.
    """
    # Local Whisper dene
    try:
        return _whisper_local(ses_verisi, dosya_adi)
    except ImportError:
        logger.info("Local Whisper yok, OpenAI API deneniyor")
    except Exception as e:
        logger.warning("Local Whisper başarısız: %s", e)

    # OpenAI Whisper API
    try:
        return _whisper_api(ses_verisi, dosya_adi)
    except Exception as e:
        logger.warning("OpenAI Whisper API başarısız: %s", e)

    return ""


def _whisper_local(ses_verisi: bytes, dosya_adi: str) -> str:
    """Local Whisper ile ses → metin."""
    import whisper

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp.write(ses_verisi)
        tmp_path = tmp.name

    try:
        model = whisper.load_model(
            (os.getenv("WHISPER_MODEL") or "small").strip()
        )
        # initial_prompt: Whisper'a bağlam ver — özel kelimeler, Türkçe olduğunu söyle
        # Bu sayede "Okwis", "bitcoin", "altın" gibi kelimeler doğru tanınır
        ozel_kelimeler = (os.getenv("WHISPER_PROMPT") or "").strip()
        initial_prompt = (
            "Okwis, bitcoin, ethereum, altın, dolar, borsa, analiz, "
            "portföy, yatırım, Türkiye, ABD, jeopolitik, piyasa. "
            "Türkçe konuşma."
        )
        if ozel_kelimeler:
            initial_prompt = ozel_kelimeler + " " + initial_prompt
        sonuc = model.transcribe(
            tmp_path,
            language="tr",
            initial_prompt=initial_prompt,
            temperature=0.0,       # deterministik — daha tutarlı
            best_of=1,
            beam_size=5,           # daha iyi arama
        )
        return sonuc.get("text", "").strip()
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def _whisper_api(ses_verisi: bytes, dosya_adi: str) -> str:
    """OpenAI Whisper API ile ses → metin."""
    from openai import OpenAI
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY tanımlı değil")

    client = OpenAI(api_key=api_key)
    ses_dosya = io.BytesIO(ses_verisi)
    ses_dosya.name = dosya_adi

    transkript = client.audio.transcriptions.create(
        model="whisper-1",
        file=ses_dosya,
        language="tr",
    )
    return transkript.text.strip()


# ── Text-to-Speech ────────────────────────────────────────────────────────────

def _edge_tts(metin: str) -> bytes:
    """Microsoft Edge TTS — ücretsiz, doğal Türkçe ses."""
    import asyncio as _asyncio
    import tempfile as _tempfile

    async def _calistir():
        import edge_tts
        # tr-TR-EmelNeural: doğal kadın sesi
        # tr-TR-AhmetNeural: erkek sesi
        ses_adi = (os.getenv("EDGE_TTS_VOICE") or "tr-TR-EmelNeural").strip()
        iletisim = edge_tts.Communicate(metin[:3000], ses_adi)
        with _tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name
        await iletisim.save(tmp_path)
        with open(tmp_path, "rb") as f:
            veri = f.read()
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        return veri

    # Mevcut event loop varsa kullan, yoksa yeni oluştur
    try:
        loop = _asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(_asyncio.run, _calistir())
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(_calistir())
    except RuntimeError:
        return _asyncio.run(_calistir())


def _elevenlabs_tts(metin: str) -> bytes:
    """ElevenLabs TTS ile metin → ses. Ücretsiz tier: 10.000 karakter/ay."""
    import httpx as _httpx
    api_key = (os.getenv("ELEVENLABS_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY tanımlı değil")

    # Varsayılan ses: "Rachel" — doğal kadın sesi, Türkçe iyi
    # Değiştirmek için ELEVENLABS_VOICE_ID env değişkeni kullan
    voice_id = (os.getenv("ELEVENLABS_VOICE_ID") or "21m00Tcm4TlvDq8ikWAM").strip()

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": metin[:2500],
        "model_id": "eleven_multilingual_v2",  # Türkçe dahil çok dilli
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.3,
            "use_speaker_boost": True,
        },
    }

    with _httpx.Client(timeout=30.0) as client:
        r = client.post(url, json=payload, headers=headers)
        r.raise_for_status()
        return r.content


def metin_sese_cevir(metin: str) -> bytes | None:
    """
    Metni sese çevir. Öncelik sırası:
    1. Edge TTS (Microsoft, ücretsiz, doğal Türkçe) — varsayılan
    2. ElevenLabs (ELEVENLABS_API_KEY varsa)
    3. OpenAI TTS (OPENAI_API_KEY varsa)
    4. gTTS (ücretsiz fallback)
    """
    # Edge TTS — varsayılan, ücretsiz, doğal
    try:
        sonuc = _edge_tts(metin)
        logger.info("Edge TTS başarılı, %d byte", len(sonuc))
        return sonuc
    except ImportError:
        logger.warning("edge-tts yok. pip install edge-tts")
    except Exception as e:
        logger.warning("Edge TTS başarısız, sonraki deneniyor: %s", e)

    # ElevenLabs
    if (os.getenv("ELEVENLABS_API_KEY") or "").strip():
        try:
            sonuc = _elevenlabs_tts(metin)
            logger.info("ElevenLabs TTS başarılı, %d byte", len(sonuc))
            return sonuc
        except Exception as e:
            logger.warning("ElevenLabs TTS başarısız: %s", e)

    # OpenAI TTS
    if (os.getenv("OPENAI_API_KEY") or "").strip():
        try:
            return _openai_tts(metin)
        except Exception as e:
            logger.warning("OpenAI TTS başarısız: %s", e)

    # gTTS — son çare
    try:
        sonuc = _gtts(metin)
        logger.info("gTTS başarılı, %d byte", len(sonuc))
        return sonuc
    except ImportError:
        logger.warning("gTTS yok. pip install gtts")
    except Exception as e:
        logger.warning("gTTS başarısız: %s", e)

    return None


def _openai_tts(metin: str) -> bytes:
    """OpenAI TTS ile metin → ses."""
    from openai import OpenAI
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY tanımlı değil")

    client = OpenAI(api_key=api_key)
    yanit = client.audio.speech.create(
        model="tts-1",
        voice="onyx",   # onyx: derin erkek sesi — alloy/echo/fable/nova/shimmer
        input=metin[:4096],
    )
    return yanit.content


def _gtts(metin: str) -> bytes:
    """gTTS ile metin → ses (ücretsiz)."""
    from gtts import gTTS
    tts = gTTS(text=metin[:500], lang="tr", slow=False)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf.read()


# ── LLM Sohbet ────────────────────────────────────────────────────────────────

def sohbet_cevabi_uret(
    kullanici_mesaji: str,
    user_id: int | str,
    profil: dict | None = None,
) -> str:
    """
    Kullanıcı mesajına doğal, kısa cevap üret.
    Sohbet geçmişini ve profil bilgisini kullanır.
    """
    now = datetime.now()
    aylar = ("Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
             "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık")
    tarih_str = f"{now.day} {aylar[now.month-1]} {now.year}"

    # Profil bloğu
    profil_metni = ""
    if profil:
        p = (profil.get("profil") or "").strip()
        if p:
            profil_metni = f"\nKullanıcı hakkında bildiğin şeyler:\n{p}\n"

    # Sohbet geçmişi
    gecmis = gecmis_al(user_id)
    gecmis_metni = ""
    if gecmis:
        satirlar = []
        for m in gecmis[-6:]:  # son 6 mesaj
            rol = "Sen" if m["rol"] == "user" else "Okwis"
            satirlar.append(f"{rol}: {m['icerik']}")
        gecmis_metni = "\nÖnceki konuşma:\n" + "\n".join(satirlar) + "\n"

    sistem = f"""Sen Okwis AI'sın — kıdemli makro yatırım analisti ve kullanıcının yakın danışmanı.
Bugün: {tarih_str}
{profil_metni}{gecmis_metni}
Kurallar:
- Kısa ve doğal konuş. Arkadaş gibi, resmi değil.
- Profil bilgisi varsa "senin portföyün", "elindeki X" diye sahiplen.
- Finans sorusu değilse de yardımcı ol ama kısa tut.
- Markdown kullanma. Düz metin yaz.
- Türkçe yaz."""

    prompt = f"{sistem}\n\nKullanıcı: {kullanici_mesaji}\nOkwis:"

    try:
        from app import llm_metin_uret
        cevap = llm_metin_uret(prompt, user_id=user_id)
        return cevap.strip()
    except Exception as e:
        logger.exception("Sohbet LLM hatası: %s", e)
        return "Şu an cevap üretemiyorum, biraz sonra tekrar dene."


# ── Niyet Tespiti ─────────────────────────────────────────────────────────────

ULKELER = ["Türkiye", "ABD", "Almanya", "İngiltere", "Japonya", "Çin", "Diğer"]

def niyet_tespit(mesaj: str) -> dict:
    """
    Kullanıcı mesajından niyet çıkar.
    Dönüş: {"tip": "analiz"|"sohbet", "ulke": str|None, "varlik": str|None, "mod": str}
    """
    mesaj_lower = mesaj.lower().strip()

    # Analiz anahtar kelimeleri
    analiz_kelimeler = [
        "analiz", "analizi", "analiz et", "analiz yap",
        "okwis", "tara", "tarama", "incele", "değerlendir",
        "ne düşünüyorsun", "ne yapmalıyım", "al mı", "sat mı",
        "yükselir mi", "düşer mi", "fırsat var mı",
    ]

    analiz_mi = any(k in mesaj_lower for k in analiz_kelimeler)

    if not analiz_mi:
        return {"tip": "sohbet", "ulke": None, "varlik": None, "mod": "okwis"}

    # Ülke tespiti
    ulke_esleme = {
        "türkiye": "Türkiye", "turkey": "Türkiye",
        "abd": "ABD", "amerika": "ABD", "usa": "ABD", "us ": "ABD",
        "almanya": "Almanya", "germany": "Almanya",
        "ingiltere": "İngiltere", "uk": "İngiltere",
        "japonya": "Japonya", "japan": "Japonya",
        "çin": "Çin", "china": "Çin",
    }
    ulke = "Türkiye"  # varsayılan
    for anahtar, deger in ulke_esleme.items():
        if anahtar in mesaj_lower:
            ulke = deger
            break

    # Varlık tespiti
    varlik_kelimeler = [
        "bitcoin", "btc", "ethereum", "eth", "kripto", "crypto",
        "altın", "gold", "petrol", "oil", "dolar", "euro",
        "hisse", "borsa", "bist", "nasdaq", "sp500",
        "gümüş", "silver", "doğalgaz",
    ]
    varlik = ""
    for k in varlik_kelimeler:
        if k in mesaj_lower:
            varlik = k
            break

    return {"tip": "analiz", "ulke": ulke, "varlik": varlik, "mod": "okwis"}
