# Makro Lens — Mimari kurallar ve proje envanteri

Bu dosya kod yazmadan önce ortak dili tanımlar. Ürün vizyonu ve yol haritası: [makro_lens_proje_plani.md](makro_lens_proje_plani.md), [SURUM_VE_YOL_HARITASI.md](SURUM_VE_YOL_HARITASI.md).

---

## 1. Strateji kuralı (öncelik)

1. **Önce Mevsim derinliği** — Yeni mod (Hava, Jeopolitik, …) eklemeden önce Mevsim’de bağlam katmanları, prompt disiplini, bot footer ve hata/uzunluk davranışı oturmuş olmalı (Parça M).
2. **Tek analiz boru hattı** — Tüm modlar aynı deseni kullanır: `toplama_bağlam(mod, ülke) → modele_iste(prompt, bağlam) → formatla_mesaj(metin)`.
3. **Uyarı politikası** — Uzun yasal metin modelde üretilmez; kısa bilgilendirme satırı **her zaman** Telegram şablonuyla eklenir ([plan: Uyarı politikası](makro_lens_proje_plani.md)).

---

## 2. Depo yapısı (şu an)

| Dosya / klasör | Rol |
|----------------|-----|
| [app.py](app.py) | Ayarlar, Mevsim + Hava + Jeopolitik analizleri, Telegram handler’lar, `main()` |
| [mevsim_baglam.py](mevsim_baglam.py) | Mevsim modu: bağlam (JSON, RSS, isteğe bağlı hava özeti) |
| [hava_baglam.py](hava_baglam.py) | Hava modu: OpenWeather anlık + tahmin bağlamı; `HavaModuHatasi` |
| [jeopolitik_baglam.py](jeopolitik_baglam.py) | Jeopolitik modu: RSS başlıklarından bağlam üretimi |
| [data/ulke_mevsim.json](data/ulke_mevsim.json) | Ülke mevsim / başkent / dönem notları verisi |
| [MEVSIM_KALITE_SENARYOLARI.md](MEVSIM_KALITE_SENARYOLARI.md) | Mevsim modu manuel regresyon listesi |
| [main.py](main.py) | İnce giriş noktası: `python main.py` → `app.main()` |
| [requirements.txt](requirements.txt) | Python bağımlılıkları |
| [.env](.env) | Yerel gizli anahtarlar (**asla git’e eklenmez**) |
| [.env.example](.env.example) | Anahtar isimleri şablonu (değer yok; commit edilebilir) |
| [.gitignore](.gitignore) | `.env`, sanal ortam, önbellek |
| [kurulum.md](kurulum.md) | Sıfırdan kurulum |
| [makro_lens_proje_plani.md](makro_lens_proje_plani.md) | Ürün ve teknik plan |
| [SURUM_VE_YOL_HARITASI.md](SURUM_VE_YOL_HARITASI.md) | Sürüm notları ve parçalı iş listesi |
| [GUNCELLEME_GUNLUGU.md](GUNCELLEME_GUNLUGU.md) | Tarihli kod/davranış değişiklik özeti |
| [.cursor/rules/](.cursor/rules/) | Cursor: her oturumda otomatik yüklenen agent kuralları (`*.mdc`) |

**İleride (büyüyünce):** `src/makro_lens/` paketi (`handlers/`, `services/ai.py`, `context/`); şimdilik tek `app.py` ile devam; dosya 400–500 satırı aşmadan paketlemeye geçilmesi önerilir.

**Cursor:** “Her sohbette kuralları baştan anlatma” ihtiyacı için `.cursor/rules/makro-lens.mdc` (`alwaysApply: true`) kullanılır; günlük ve yol haritası disiplini orada özetlenir.

---

## 3. Gereksiz / silinmesi gereken dosya

**Şu an repoda silinmesi gereken dosya yok.** Tüm dosyaların bir rolü var.

- **`.env`:** Gereksiz değil; yerel çalışma için zorunlu. **Çift kopya** veya **repoya yanlışlıkla commit** edilmiş örnek oluşturma — tek kaynak yerel `.env`, şablon için istenirse `.env.example` (sadece anahtar isimleri, değer yok) eklenebilir.
- Gizli anahtarları **asla** `app.py` veya dokümana gömme.

---

## 4. Teknik kurallar

| Konu | Kural |
|------|--------|
| Python | 3.11+ (kurulum dokümanında 3.12 de uygun) |
| Telegram | `python-telegram-bot` v20+, async handler’lar; analiz ve komut metinlerinde `ParseMode.HTML`, kullanıcı/model metni `html.escape` |
| Async | Handler’lar `async`; bloklayan ağ çağrıları mümkünse thread veya async HTTP ile |
| Dil | Kullanıcıya Türkçe; yabancı ülke analizinde sembol/isim tutarlılığı prompt’ta tanımlanır |
| Hata | Kullanıcıya kısa Türkçe mesaj; log’da tam istisna |
| Mesaj uzunluğu | Telegram ~4096 karakter; uzun model çıktısı bölünür veya kısaltma talimatı verilir |
| Bağımlılık | Yeni paket eklemeden önce `requirements.txt` güncelle; sabit sürüm tercih et |

---

## 5. Plan ↔ kod gerçeği

- **Plan:** Claude + `httpx` + harici veri. **Kod:** şu an **Google Gemini** veya `.env` ile **DeepSeek** (`AI_PROVIDER`); `httpx` ile RSS (mevsim) ve OpenWeather (hava + isteğe bağlı mevsim özeti).
- Motor (Claude) kararı netleştikçe bu dosya ve `makro_lens_proje_plani.md` güncellenir.

---

## 6. Sıradaki kod adımları

Parça B, M, **G**, **C** (Hava) ve **D** (Jeopolitik) tamam ([GUNCELLEME_GUNLUGU.md](GUNCELLEME_GUNLUGU.md)). Önerilen sıra ([SURUM_VE_YOL_HARITASI.md](SURUM_VE_YOL_HARITASI.md)):

1. **Parça E** — Tek AI motoru stratejisini netleştir (Claude geçişi mi, Gemini+DeepSeek mi).
2. **Parça F** — Web arama kalitesini artır (mevsim/jeopolitik bağlamında daha güvenilir kaynak).
3. **Parça K/L/N/O** — Güven skoru, mod karnesi, simülasyon/backtest, portföy+alarm (ticari fark).

Yeni mod veya yeni harici API eklemeden önce [MEVSIM_KALITE_SENARYOLARI.md](MEVSIM_KALITE_SENARYOLARI.md) ile bir regresyon turu önerilir.
