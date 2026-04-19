#!/usr/bin/env python3
"""Update app.py prompts to add market direction prediction (PİYASA_YÖNÜ)"""
import re

# Read the file
with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

print("Starting updates...")

# 1. Update mevsim özet: "sekiz satır" -> "dokuz satır" and add PİYASA_YÖNÜ line
content = content.replace(
    "aşağıdaki sekiz satır olarak ver; her satır tam olarak `ETİKET: içerik`",
    "aşağıdaki dokuz satır olarak ver; her satır tam olarak `ETİKET: içerik`",
    1
)
print("✓ Updated 'aşağıdaki sekiz satır' -> 'dokuz satır' in mevsim özet")

# Add PİYASA_YÖNÜ line before GÜVEN in mevsim özet
content = content.replace(
    "RİSK: (tek cümle risk)\nGÜVEN: ({guven['toplam']}/100 — {guven['etiket']};",
    "RİSK: (tek cümle risk)\nPİYASA_YÖNÜ: (bullish/nötr/bearish + kısa neden: \"Mevsimsel talep artışı bullish\" gibi)\nGÜVEN: ({guven['toplam']}/100 — {guven['etiket']};",
    1
)
print("✓ Added PİYASA_YÖNÜ line to mevsim özet")

# Update satır count in mevsim özet kurallar
content = content.replace(
    "sadece bu sekiz satır\n- Düz metin; *, _, #, madde işareti kullanma\n- {dil_notu}\n- Uydurma veri kullanma",
    "sadece bu dokuz satır\n- Düz metin; *, _, #, madde işareti kullanma\n- {dil_notu}\n- Uydurma veri kullanma",
    1
)
print("✓ Updated 'sadece bu sekiz satır' -> 'dokuz satır' in mevsim özet kurallar")

# 2. Update mevsim uzun anlatım - add PİYASA TAHMINI as step 8
old_pattern = "7. **Girişim fırsatları:**"
# Find and replace the section with step 8 and 9 renumbered
old_mevsim_detay = """7. **Girişim fırsatları:** Aynı mevsim ve ülke bağlamında **girişim / yenilik / yan proje** açısından 1–2 cümle ekle: hangi problem alanlarında fırsat oluşur, hangi B2B veya tüketici ihtiyaçları artar, erken aşama hangi tema gündemde olabilir (somut "şunu kur" talimatı değil, tema düzeyinde).
8. Ayrı bir cümlede **GÜVEN** satırı ver: "GÜVEN: {guven['toplam']}/100 ({guven['etiket']}) ..." (kullanıcı dili; teknik kısaltma yok).
9. Ayrı bir cümlede **TERS_SENARYO** ver: "Bu tezi bozabilecek ana koşul ..."."""

new_mevsim_detay = """7. **Girişim fırsatları:** Aynı mevsim ve ülke bağlamında **girişim / yenilik / yan proje** açısından 1–2 cümle ekle: hangi problem alanlarında fırsat oluşur, hangi B2B veya tüketici ihtiyaçları artar, erken aşama hangi tema gündemde olabilir (somut "şunu kur" talimatı değil, tema düzeyinde).
8. **PİYASA TAHMINI:** Bullish/Nötr/Bearish + kısa neden ("Mevsimsel talep artışı bullish"). Ardından "Eğer bu koşullar devam ederse ..." senaryosu (bir cümle).
9. Ayrı bir cümlede **GÜVEN** satırı ver: "GÜVEN: {guven['toplam']}/100 ({guven['etiket']}) ..." (kullanıcı dili; teknik kısaltma yok).
10. Ayrı bir cümlede **TERS_SENARYO** ver: "Bu tezi bozabilecek ana koşul ..."."""

if old_mevsim_detay in content:
    content = content.replace(old_mevsim_detay, new_mevsim_detay)
    print("✓ Updated mevsim uzun anlatım steps (Added step 8 PİYASA TAHMINI)")
else:
    print("⚠ Could not find mevsim uzun anlatım section to update")

# 3. Update hava özet similarly
content = content.replace(
    "Çıktıyı **yalnızca** sekiz satır olarak ver; her satır `ETİKET: içerik` (ETİKET büyük harf, Türkçe).",
    "Çıktıyı **yalnızca** dokuz satır olarak ver; her satır `ETİKET: içerik` (ETİKET büyük harf, Türkçe).",
    1
)
print("✓ Updated hava özet satır count")

# Add PİYASA_YÖNÜ to hava özet output spec
content = content.replace(
    "TERS_SENARYO: tek cümle ters senaryo\n\n### Kurallar (özet — hava)",
    "PİYASA_YÖNÜ: (bullish/nötr/bearish + kısa neden)\nTERS_SENARYO: tek cümle ters senaryo\n\n### Kurallar (özet — hava)",
    1
)
print("✓ Added PİYASA_YÖNÜ output to hava özet")

# 4. Update hava uzun anlatım
old_hava_detay = """7. Son cümle: tek cümle **risk** (hava modeli belirsizliği, politik/regülasyon müdahalesi vb.).
8. Ayrı bir cümlede **GÜVEN** satırı ver: "GÜVEN: {guven['toplam']}/100 ({guven['etiket']}) ..." (kullanıcı dili; teknik kısaltma yok).
9. Ayrı bir cümlede **TERS_SENARYO** ver: "Bu tezi bozabilecek ana koşul ..."""

new_hava_detay = """7. Son cümle: tek cümle **risk** (hava modeli belirsizliği, politik/regülasyon müdahalesi vb.).
8. **PİYASA TAHMINI:** Bullish/Nötr/Bearish + kısa neden. Ardından "Eğer bu hava koşulları devam ederse ..." senaryosu (bir cümle).
9. Ayrı bir cümlede **GÜVEN** satırı ver: "GÜVEN: {guven['toplam']}/100 ({guven['etiket']}) ..." (kullanıcı dili; teknik kısaltma yok).
10. Ayrı bir cümlede **TERS_SENARYO** ver: "Bu tezi bozabilecek ana koşul ..."""

if old_hava_detay in content:
    content = content.replace(old_hava_detay, new_hava_detay)
    print("✓ Updated hava uzun anlatım steps (Added step 8 PİYASA TAHMINI)")
else:
    print("⚠ Could not find hava uzun anlatım section to update")

# 5. Update jeopolitik özet similarly
content = content.replace(
    "Çıktıyı yalnızca aşağıdaki sekiz satır olarak ver; her satır tam olarak `ETİKET: içerik` biçiminde olsun (ETİKET büyük harf ve Türkçe).",
    "Çıktıyı yalnızca aşağıdaki dokuz satır olarak ver; her satır tam olarak `ETİKET: içerik` biçiminde olsun (ETİKET büyük harf ve Türkçe).",
    1
)
print("✓ Updated jeopolitik özet satır count")

# 6. Update jeopolitik uzun anlatım
old_jeo_detay = """8. Ayrı bir cümlede **GÜVEN** satırı ver: "GÜVEN: {guven['toplam']}/100 ({guven['etiket']}) ..." (kullanıcı dili; teknik kısaltma yok).
9. Ayrı bir cümlede **TERS_SENARYO** ver: "Bu tezi bozabilecek ana koşul ..."."""

new_jeo_detay = """8. **PİYASA TAHMINI:** Bullish/Nötr/Bearish + kısa neden ("Bu jeopolitik gelişmeler bearish baskı oluşturuyor" gibi). Ardından "Eğer bu durumlar...değişmezse" senaryosu.
9. Ayrı bir cümlede **GÜVEN** satırı ver: "GÜVEN: {guven['toplam']}/100 ({guven['etiket']}) ..." (kullanıcı dili; teknik kısaltma yok).
10. Ayrı bir cümlede **TERS_SENARYO** ver: "Bu tezi bozabilecek ana koşul ..."."""

if old_jeo_detay in content:
    content = content.replace(old_jeo_detay, new_jeo_detay)
    print("✓ Updated jeopolitik uzun anlatım steps (Added step 8 PİYASA TAHMINI)")
else:
    print("⚠ Could not find jeopolitik uzun anlatım section to update")

# Write back
with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("\n✓ All updates completed successfully!")
