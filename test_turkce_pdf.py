"""
Türkçe karakter testi için basit PDF
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors

# Test metni - Türkçe karakterler
test_metni = """
Türkiye ekonomisi için önemli gelişmeler:

• Enflasyon düşüş trendinde
• Merkez Bankası faiz politikası değişiyor
• Döviz kurları istikrarlı seyrediyor
• Yatırımcılar için fırsatlar oluşuyor

Özel karakterler: ı ş ğ ü ö ç İ Ş Ğ Ü Ö Ç

Umarım bu analiz, senin için somut adımlar atmana yardımcı olur.
Portföyünü düzenli olarak gözden geçirmeyi unutma.
Bu rapor yatırım tavsiyesi değildir.
Yatırım kararı için kendi araştırmanı yap.
"""

buf = open("test_turkce.pdf", "wb")
doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

styles = getSampleStyleSheet()

# Times-Roman ile test
times_stil = ParagraphStyle(
    'TimesTest',
    parent=styles['BodyText'],
    fontSize=11,
    fontName='Times-Roman',
    leading=16,
)

story = []
story.append(Paragraph("TÜRKÇE KARAKTER TESTİ", styles['Title']))
story.append(Spacer(1, 1*cm))
story.append(Paragraph("Times-Roman Font:", styles['Heading2']))
story.append(Paragraph(test_metni.replace('\n', '<br/>'), times_stil))

doc.build(story)
buf.close()

print("✅ test_turkce.pdf oluşturuldu")
print("PDF'i açıp Türkçe karakterlerin doğru göründüğünü kontrol edin.")
