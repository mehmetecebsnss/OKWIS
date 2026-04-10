"""
Hava modu: OpenWeatherMap ile başkent anlık hava + kısa tahmin özeti (model bağlamı).
Ülke → şehir eşlemesi: data/ulke_mevsim.json içindeki capital_query.
"""

from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_DATA_PATH = Path(__file__).resolve().parent / "data" / "ulke_mevsim.json"
_TIMEOUT = 12.0
# OpenWeather 2.5 forecast: en fazla 40 adım × 3 saat ≈ 5 takvim günü
_FORECAST_CNT = 40
_ILK_24_SAAT_ADIM = 8


class HavaModuHatasi(Exception):
    """Kullanıcıya gösterilecek kısa Türkçe mesaj (HTML kaçışı handler’da)."""


def _yukle_ulke_tablosu() -> dict[str, Any]:
    with open(_DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def _gunluk_ozet_satirlari(tahmin_listesi: list[dict[str, Any]]) -> list[str]:
    """3 saatlik dilimleri takvim gününe göre grupla; min/max sıcaklık + tipik açıklama."""
    gunluk: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"temps": [], "descs": []}
    )
    for it in tahmin_listesi:
        dt_txt = it.get("dt_txt") or ""
        gun = (dt_txt[:10] if len(dt_txt) >= 10 else None) or "?"
        main = it.get("main") or {}
        t = main.get("temp")
        if t is not None:
            gunluk[gun]["temps"].append(float(t))
        tw = (it.get("weather") or [{}])[0]
        d = tw.get("description", "").strip()
        if d:
            gunluk[gun]["descs"].append(d)

    satirlar: list[str] = []
    for gun in sorted(gunluk.keys()):
        g = gunluk[gun]
        temps = g["temps"]
        if not temps:
            continue
        t_min, t_max = min(temps), max(temps)
        descs = g["descs"]
        # en sık geçen açıklama (kısa özet)
        if descs:
            en_sik = max(set(descs), key=descs.count)
        else:
            en_sik = "—"
        satirlar.append(
            f"- {gun}: min {t_min:.0f}°C, max {t_max:.0f}°C; gün içi koşullar çoğunlukla: {en_sik}"
        )
    return satirlar


def topla_hava_baglami(ulke: str) -> str:
    """
    OpenWeatherMap: anlık hava + 5 güne kadar tahmin (3 saatlik dilimler),
    günlük min/max özet + ilk 24 saat detayı. Gemini’ye tek metin bloğu.
    OPENWEATHER_API_KEY zorunlu.
    """
    api_key = (os.getenv("OPENWEATHER_API_KEY") or "").strip()
    if not api_key:
        raise HavaModuHatasi(
            "Hava modu için OpenWeatherMap anahtarı gerekli. "
            ".env dosyana OPENWEATHER_API_KEY=... ekle; "
            "https://openweathermap.org/api adresinden ücretsiz anahtar alabilirsin."
        )

    tablo = _yukle_ulke_tablosu()
    meta = tablo.get(ulke) or tablo.get("Diğer", {})
    city_q = meta.get("capital_query")
    if not city_q:
        raise HavaModuHatasi(
            "Bu seçenek için tanımlı şehir yok. Hava analizi için listeden belirli bir ülke seç "
            "(“Diğer” şu an başkent eşleşmesi içermiyor)."
        )

    base = "https://api.openweathermap.org/data/2.5"
    params_common = {"q": city_q, "appid": api_key, "units": "metric", "lang": "tr"}

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r_cur = client.get(f"{base}/weather", params=params_common)
            r_cur.raise_for_status()
            cur = r_cur.json()

            r_fc = client.get(
                f"{base}/forecast",
                params={**params_common, "cnt": _FORECAST_CNT},
            )
            r_fc.raise_for_status()
            fc = r_fc.json()
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        logger.warning("OpenWeather HTTP %s (%s): %s", code, city_q, e)
        if code == 401:
            raise HavaModuHatasi(
                "OpenWeatherMap anahtarı geçersiz veya süresi dolmuş görünüyor. .env içindeki OPENWEATHER_API_KEY değerini kontrol et."
            ) from e
        if code == 404:
            raise HavaModuHatasi(
                "Seçilen ülke için şehir bulunamadı. Farklı bir ülke dene veya yöneticiye bildir."
            ) from e
        raise HavaModuHatasi(
            "Hava servisi şu an beklenmeyen bir kod döndü. Biraz sonra tekrar dene."
        ) from e
    except httpx.RequestError as e:
        logger.warning("OpenWeather ağ hatası (%s): %s", city_q, e)
        raise HavaModuHatasi(
            "Hava verisine bağlanılamadı. İnternetini kontrol edip biraz sonra tekrar dene."
        ) from e
    except Exception as e:
        logger.exception("OpenWeather işlenemedi (%s)", city_q)
        raise HavaModuHatasi(
            "Hava verisi işlenirken bir sorun oluştu. /analiz ile tekrar dene."
        ) from e

    try:
        w0 = cur["weather"][0]
        main = cur["main"]
        wind = cur.get("wind", {})
        sehir = cur.get("name", city_q)
        ulke_kod = cur.get("sys", {}).get("country", "")

        anlik_satir = (
            f"Anlık ({sehir}{', ' + ulke_kod if ulke_kod else ''}): "
            f"{w0.get('description', '—')}, "
            f"{main.get('temp', 0):.0f}°C (hissedilen {main.get('feels_like', main.get('temp', 0)):.0f}°C), "
            f"nem %{main.get('humidity', '—')}, "
            f"rüzgar ~{wind.get('speed', '—')} m/s."
        )

        tum = fc.get("list") or []
        gunluk_satirlar = _gunluk_ozet_satirlari(tum)

        tahmin_satirlari: list[str] = []
        for i, it in enumerate(tum[:_ILK_24_SAAT_ADIM]):
            t_main = it.get("main", {})
            tw = (it.get("weather") or [{}])[0]
            dt = it.get("dt_txt", f"+{i}")
            tahmin_satirlari.append(
                f"- {dt}: {tw.get('description', '—')}, "
                f"{t_main.get('temp', 0):.0f}°C, nem %{t_main.get('humidity', '—')}"
            )
    except (KeyError, IndexError, TypeError) as e:
        logger.exception("OpenWeather JSON beklenen yapıda değil: %s", e)
        raise HavaModuHatasi("Hava yanıtı okunamadı. Servis formatı değişmiş olabilir; sonra dene.") from e

    parcalar = [
        "### Verilen bağlam — hava (yalnızca bu verilere dayan; uydurma ekleme)",
        f"Hedef ülke (kullanıcı seçimi): {ulke}. Ölçüm şehri (başkent temsili): {sehir}.",
        "Tahmin horizonu: OpenWeather 5 günlük / 3 saatlik API; aşağıda günlük min–max ve ilk 24 saat dilimleri var.",
        anlik_satir,
        "### Günlük özet (takvim günü bazında, önümüzdeki ~5 güne kadar)",
        "\n".join(gunluk_satirlar) if gunluk_satirlar else "(Günlük özet oluşturulamadı.)",
        "### İlk 24 saat (3 saatlik dilimler)",
        "\n".join(tahmin_satirlari) if tahmin_satirlari else "(Tahmin listesi boş.)",
        "### Not",
        "Bu veriler bilgilendirme amaçlıdır; yatırım tavsiyesi değildir.",
    ]
    return "\n".join(parcalar)
