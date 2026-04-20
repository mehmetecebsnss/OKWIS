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
    import whisper  # pip install openai-whisper

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp.write(ses_verisi)
        tmp_path = tmp.name

    try:
        model = whisper.load_model("small")  # tiny/small/medium — Pi 5'te small yeterli
        sonuc = model.transcribe(tmp_path, language="tr")
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

def metin_sese_cevir(metin: str) -> bytes | None:
    """
    Metni sese çevir.
    Önce OpenAI TTS dener, yoksa gTTS'e düşer.
    Başarısız olursa None döner (yazılı cevap gönderilir).
    """
    # OpenAI TTS dene
    try:
        return _openai_tts(metin)
    except ImportError:
        pass
    except Exception as e:
        logger.warning("OpenAI TTS başarısız: %s", e)

    # gTTS dene
    try:
        return _gtts(metin)
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
