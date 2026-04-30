"""
Okwis AI — Mesaj Utility Fonksiyonları
Telegram mesaj gönderme, HTML escape, formatting
"""

import html
import logging
from typing import Optional
from telegram import Update, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import BadRequest

logger = logging.getLogger(__name__)


def tg_html_escape(text: str) -> str:
    """
    Telegram HTML için güvenli escape.
    Dinamik değerleri HTML'e eklerken kullan.
    """
    return html.escape(str(text))


def analiz_html_temizle(html_text: str) -> str:
    """
    Analiz çıktısındaki HTML'i temizle ve güvenli hale getir.
    
    Args:
        html_text: Ham HTML metni
    
    Returns:
        Temizlenmiş HTML metni
    """
    # Desteklenmeyen tag'leri temizle
    import re
    
    # İzin verilen tag'ler: b, i, code, pre, a
    # Diğer tüm tag'leri kaldır
    allowed_tags = ['b', 'i', 'code', 'pre', 'a']
    
    # Tüm tag'leri bul
    def replace_tag(match):
        tag = match.group(1).lower()
        if tag.startswith('/'):
            tag = tag[1:]
        if tag.split()[0] in allowed_tags:
            return match.group(0)
        return ''
    
    # Tag'leri temizle
    cleaned = re.sub(r'<(/?\w+)[^>]*>', replace_tag, html_text)
    
    # Boş satırları temizle (3'ten fazla ardışık \n)
    cleaned = re.sub(r'\n{4,}', '\n\n\n', cleaned)
    
    return cleaned.strip()


async def gonder_mesaj_guvenli(
    update: Update,
    text: str,
    parse_mode: str = ParseMode.HTML,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    max_length: int = 4096,
) -> bool:
    """
    Telegram mesajı güvenli şekilde gönder.
    Hata durumunda fallback'ler dene.
    
    Args:
        update: Telegram Update objesi
        text: Gönderilecek mesaj
        parse_mode: Parse modu (HTML, Markdown, None)
        reply_markup: Inline keyboard
        max_length: Maksimum mesaj uzunluğu
    
    Returns:
        Başarılı mı?
    """
    if not update.effective_chat:
        return False
    
    # Mesaj çok uzunsa böl
    if len(text) > max_length:
        chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
        for i, chunk in enumerate(chunks):
            try:
                # Son chunk'ta reply_markup ekle
                markup = reply_markup if i == len(chunks) - 1 else None
                await update.effective_chat.send_message(
                    text=chunk,
                    parse_mode=parse_mode,
                    reply_markup=markup,
                )
            except Exception as e:
                logger.warning("Mesaj chunk gönderilemedi: %s", e)
                return False
        return True
    
    # Normal mesaj gönder
    try:
        await update.effective_chat.send_message(
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
        return True
    except BadRequest as e:
        # HTML parse hatası - fallback: plain text
        if "can't parse" in str(e).lower():
            logger.warning("HTML parse hatası, plain text deneniyor: %s", e)
            try:
                await update.effective_chat.send_message(
                    text=text,
                    parse_mode=None,
                    reply_markup=reply_markup,
                )
                return True
            except Exception as e2:
                logger.error("Plain text de başarısız: %s", e2)
                return False
        else:
            logger.error("Mesaj gönderilemedi: %s", e)
            return False
    except Exception as e:
        logger.error("Beklenmeyen hata: %s", e)
        return False


async def gonder_foto_guvenli(
    update: Update,
    photo_buffer,
    caption: Optional[str] = None,
    parse_mode: str = ParseMode.HTML,
) -> bool:
    """
    Fotoğraf güvenli şekilde gönder.
    
    Args:
        update: Telegram Update objesi
        photo_buffer: BytesIO buffer veya file path
        caption: Fotoğraf açıklaması
        parse_mode: Parse modu
    
    Returns:
        Başarılı mı?
    """
    if not update.effective_chat:
        return False
    
    try:
        await update.effective_chat.send_photo(
            photo=photo_buffer,
            caption=caption,
            parse_mode=parse_mode,
        )
        return True
    except BadRequest as e:
        # Caption parse hatası - fallback: plain text
        if "can't parse" in str(e).lower() and caption:
            logger.warning("Caption parse hatası, plain text deneniyor")
            try:
                await update.effective_chat.send_photo(
                    photo=photo_buffer,
                    caption=caption,
                    parse_mode=None,
                )
                return True
            except Exception as e2:
                logger.error("Plain text caption de başarısız: %s", e2)
                return False
        else:
            logger.error("Fotoğraf gönderilemedi: %s", e)
            return False
    except Exception as e:
        logger.error("Beklenmeyen hata: %s", e)
        return False


def format_tarih(dt: Optional[object] = None) -> str:
    """
    Tarihi Türkçe formatla
    
    Args:
        dt: datetime objesi (None ise şimdi)
    
    Returns:
        "30 Nisan 2026 15:30" formatında string
    """
    from datetime import datetime
    
    if dt is None:
        dt = datetime.now()
    
    aylar = (
        "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
        "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
    )
    
    return f"{dt.day} {aylar[dt.month - 1]} {dt.year} {dt.hour:02d}:{dt.minute:02d}"


def format_sayi(sayi: float, ondalik: int = 2) -> str:
    """
    Sayıyı formatla (binlik ayırıcı ile)
    
    Args:
        sayi: Formatlanacak sayı
        ondalik: Ondalık basamak sayısı
    
    Returns:
        "1,234.56" formatında string
    """
    return f"{sayi:,.{ondalik}f}"


def kisalt_metin(metin: str, max_uzunluk: int = 100, son_ek: str = "...") -> str:
    """
    Metni kısalt
    
    Args:
        metin: Kısaltılacak metin
        max_uzunluk: Maksimum uzunluk
        son_ek: Kısaltma eki
    
    Returns:
        Kısaltılmış metin
    """
    if len(metin) <= max_uzunluk:
        return metin
    
    return metin[:max_uzunluk - len(son_ek)] + son_ek


def emoji_durum(basarili: bool) -> str:
    """Başarı durumuna göre emoji döndür"""
    return "✅" if basarili else "❌"


def emoji_seviye(seviye: int, max_seviye: int = 10) -> str:
    """
    Seviyeye göre emoji döndür
    
    Args:
        seviye: Mevcut seviye (0-max_seviye)
        max_seviye: Maksimum seviye
    
    Returns:
        Emoji string
    """
    oran = seviye / max_seviye
    
    if oran >= 0.8:
        return "🟢"  # Yüksek
    elif oran >= 0.5:
        return "🟡"  # Orta
    else:
        return "🔴"  # Düşük
