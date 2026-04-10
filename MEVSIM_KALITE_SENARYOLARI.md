# Mevsim modu — manuel kalite / regresyon senaryoları

Parça M kapsamında iç kontrol listesi. Yeni prompt veya bağlam değişikliğinden sonra en az bir tur çalıştır.

**Nasıl:** Her satır için `/analiz` → Mevsimler → ülke; çıktıyı hızlıca şu kriterlere göre işaretle.

| # | Ülke | Odak | Kontrol |
|---|------|------|---------|
| 1 | Türkiye | Sektör + 3 şirket + girişim teması | 1–2 sektör teması; üç gerçekçi şirket (tek cümlede); girişim fırsatı 1–2 cümle; uydurma yok |
| 2 | ABD | Üç ABD şirketi + girişim teması | Türkçe gövde; şirket adları doğrulanabilir; tema düzeyinde girişim |
| 3 | Almanya | Avrupa/enerji çerçevesi | Bağlamdaki ülke notlarıyla çelişmemeli |
| 4 | Japonya | Golden Week / mali yıl ipuçları | Uydurma tarih yok; emin değilse kısa itiraf |
| 5 | Çin | İç talep / üretim dengesi | Abartılı kesinlik yok |
| 6 | İngiltere | Enerji / perakende mevsimselliği | Risk cümlesi var |
| 7 | Diğer | Genelleme disiplini | “Diğer” notları: varsayımı söyleme |
| 8 | Türkiye | RSS başlıkları geldiğinde | Haber başlıkları analize hafif dokunuyor mu (zorla bağlama yok) |
| 9 | ABD | RSS yok / hata mesajı | Model yine tutarlı analiz üretiyor mu |
|10 | (İsteğe bağlı) | `OPENWEATHER_API_KEY` açıkken | Başkent hava satırı analizde abartısız kullanılıyor mu |

**Geç / kal** kolonunu kendin işaretle; sürüm notlarına tarih ekle ([GUNCELLEME_GUNLUGU.md](GUNCELLEME_GUNLUGU.md)).
