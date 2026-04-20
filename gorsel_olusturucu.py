"""
Okwis AI — Premium Görsel Oluşturucu
Analiz sonuçları için profesyonel grafikler, infografikler ve PDF raporlar üretir.
"""

import io
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import matplotlib
    matplotlib.use('Agg')  # GUI olmadan çalışması için
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch
    MATPLOTLIB_VAR = True
except ImportError:
    MATPLOTLIB_VAR = False

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_VAR = True
except ImportError:
    REPORTLAB_VAR = False


def _turkce_karakter_temizle(metin: str) -> str:
    """
    Türkçe karakterleri ASCII karşılıklarına çevir.
    PDF'de karakter sorunu yaşanmaması için.
    """
    turkce_map = {
        'ı': 'i', 'İ': 'I',
        'ş': 's', 'Ş': 'S',
        'ğ': 'g', 'Ğ': 'G',
        'ü': 'u', 'Ü': 'U',
        'ö': 'o', 'Ö': 'O',
        'ç': 'c', 'Ç': 'C',
    }
    for tr, en in turkce_map.items():
        metin = metin.replace(tr, en)
    return metin


class GorselOlusturucu:
    """Premium görsel içerik oluşturucu"""
    
    def __init__(self):
        self.renk_paleti = {
            'baslik': '#1a1a2e',
            'vurgu': '#0f3460',
            'pozitif': '#16213e',
            'notr': '#533483',
            'negatif': '#e94560',
            'arka_plan': '#f8f9fa',
            'cerceve': '#e0e0e0',
        }
    
    def guven_skoru_grafigi(
        self,
        guven_skoru: int,
        veri_kalitesi: int,
        mod_basarisi: int,
        ulke: str,
        mod: str,
    ) -> Optional[io.BytesIO]:
        """
        Güven skoru için zarif, minimal bar chart oluştur.
        
        Returns:
            BytesIO buffer (PNG) veya None (matplotlib yoksa)
        """
        if not MATPLOTLIB_VAR:
            return None
        
        fig, ax = plt.subplots(figsize=(10, 6), facecolor='white')
        
        # Veriler
        kategoriler = ['Güven Skoru', 'Veri Kalitesi', 'Mod Başarısı']
        degerler = [guven_skoru, veri_kalitesi, mod_basarisi]
        renkler = ['#16213e', '#0f3460', '#533483']
        
        # Horizontal bar chart
        bars = ax.barh(kategoriler, degerler, color=renkler, height=0.6, alpha=0.85)
        
        # Değerleri bar'ların üzerine yaz
        for i, (bar, deger) in enumerate(zip(bars, degerler)):
            ax.text(
                deger + 2,
                bar.get_y() + bar.get_height() / 2,
                f'{deger}/100',
                va='center',
                fontsize=12,
                fontweight='bold',
                color='#1a1a2e'
            )
        
        # Stil ayarları
        ax.set_xlim(0, 110)
        ax.set_xlabel('Skor', fontsize=11, color='#1a1a2e', fontweight='600')
        ax.set_title(
            f'Analiz Kalite Metrikleri\n{ulke} · {mod.upper()}',
            fontsize=14,
            fontweight='bold',
            color='#1a1a2e',
            pad=20
        )
        
        # Grid ve çerçeve
        ax.grid(axis='x', alpha=0.3, linestyle='--', linewidth=0.5)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#e0e0e0')
        ax.spines['bottom'].set_color('#e0e0e0')
        
        # Y ekseni etiketleri
        ax.tick_params(axis='y', labelsize=11, colors='#1a1a2e')
        ax.tick_params(axis='x', labelsize=10, colors='#666666')
        
        plt.tight_layout()
        
        # BytesIO buffer'a kaydet
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        plt.close(fig)
        
        return buf
    
    def prob_zinciri_infografik(
        self,
        aktif_zincirler: list[dict],
        ulke: str,
        varlik: str,
    ) -> Optional[io.BytesIO]:
        """
        Aktif olasılık zincirleri için infografik oluştur.
        
        Args:
            aktif_zincirler: [{"baslik": "...", "olasilik": 0.75, "kategori": "mevsimsel"}, ...]
        
        Returns:
            BytesIO buffer (PNG) veya None
        """
        if not MATPLOTLIB_VAR or not aktif_zincirler:
            return None
        
        fig, ax = plt.subplots(figsize=(10, 8), facecolor='white')
        
        # En fazla 5 zincir göster
        zincirler = aktif_zincirler[:5]
        
        y_pozisyonlari = list(range(len(zincirler), 0, -1))
        
        for i, (zincir, y_pos) in enumerate(zip(zincirler, y_pozisyonlari)):
            baslik = zincir.get('baslik', 'Bilinmeyen')
            olasilik = zincir.get('olasilik', 0.5)
            kategori = zincir.get('kategori', 'genel')
            
            # Olasılık rengini belirle
            if olasilik >= 0.7:
                renk = '#16213e'
            elif olasilik >= 0.5:
                renk = '#0f3460'
            else:
                renk = '#533483'
            
            # Bar
            bar = ax.barh(y_pos, olasilik * 100, height=0.7, color=renk, alpha=0.85)
            
            # Başlık (sol tarafta)
            ax.text(
                -5,
                y_pos,
                baslik[:40] + ('...' if len(baslik) > 40 else ''),
                va='center',
                ha='right',
                fontsize=10,
                fontweight='600',
                color='#1a1a2e'
            )
            
            # Olasılık değeri (bar içinde)
            ax.text(
                olasilik * 100 - 3,
                y_pos,
                f'%{int(olasilik * 100)}',
                va='center',
                ha='right',
                fontsize=10,
                fontweight='bold',
                color='white'
            )
            
            # Kategori etiketi (sağ tarafta)
            ax.text(
                105,
                y_pos,
                kategori.upper(),
                va='center',
                ha='left',
                fontsize=8,
                color='#666666',
                style='italic'
            )
        
        # Stil
        ax.set_xlim(-50, 120)
        ax.set_ylim(0, len(zincirler) + 1)
        ax.set_xlabel('Olasılık (%)', fontsize=11, color='#1a1a2e', fontweight='600')
        
        varlik_str = f' · {varlik}' if varlik else ''
        ax.set_title(
            f'Aktif Olasılık Zincirleri\n{ulke}{varlik_str}',
            fontsize=14,
            fontweight='bold',
            color='#1a1a2e',
            pad=20
        )
        
        # Grid ve çerçeve
        ax.grid(axis='x', alpha=0.3, linestyle='--', linewidth=0.5)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['bottom'].set_color('#e0e0e0')
        ax.set_yticks([])
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        plt.close(fig)
        
        return buf
    
    def pdf_rapor_olustur(
        self,
        analiz_metni: str,
        ulke: str,
        mod: str,
        varlik: str,
        guven_skoru: int,
        tarih: Optional[datetime] = None,
    ) -> Optional[io.BytesIO]:
        """
        Analiz için profesyonel PDF rapor oluştur.
        
        Returns:
            BytesIO buffer (PDF) veya None (reportlab yoksa)
        """
        if not REPORTLAB_VAR:
            return None
        
        if tarih is None:
            tarih = datetime.now()
        
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )
        
        # Stil tanımları
        styles = getSampleStyleSheet()
        
        # Özel stiller - Times-Roman Türkçe karakterleri destekler
        baslik_stil = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a2e'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Times-Bold',
        )
        
        alt_baslik_stil = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#0f3460'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Times-Bold',
        )
        
        metin_stil = ParagraphStyle(
            'CustomBody',
            parent=styles['BodyText'],
            fontSize=11,
            textColor=colors.HexColor('#1a1a2e'),
            spaceAfter=12,
            alignment=TA_JUSTIFY,
            fontName='Times-Roman',
            leading=16,
        )
        
        # İçerik
        story = []
        
        # Türkçe karakterleri temizle
        ulke_temiz = _turkce_karakter_temizle(ulke)
        mod_temiz = _turkce_karakter_temizle(mod)
        varlik_temiz = _turkce_karakter_temizle(varlik) if varlik else "Genel"
        
        # Başlık
        story.append(Paragraph('OKWIS AI', baslik_stil))
        story.append(Paragraph('Yatirim Analiz Raporu', alt_baslik_stil))
        story.append(Spacer(1, 0.5*cm))
        
        # Bilgi tablosu
        bilgi_data = [
            ['Ulke:', ulke_temiz],
            ['Analiz Modu:', mod_temiz.upper()],
            ['Varlik:', varlik_temiz],
            ['Tarih:', tarih.strftime('%d.%m.%Y %H:%M')],
            ['Guven Skoru:', f'{guven_skoru}/100'],
        ]
        
        bilgi_tablo = Table(bilgi_data, colWidths=[4*cm, 10*cm])
        bilgi_tablo.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1a1a2e')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Times-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Times-Roman'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ]))
        
        story.append(bilgi_tablo)
        story.append(Spacer(1, 1*cm))
        
        # Analiz içeriği
        story.append(Paragraph('ANALIZ', alt_baslik_stil))
        
        # Metni temizle ve paragraflara böl
        analiz_temiz = _turkce_karakter_temizle(analiz_metni)
        paragraflar = analiz_temiz.split('\n\n')
        for para in paragraflar:
            if para.strip():
                # Satır sonlarını <br/> ile değiştir
                para_html = para.replace('\n', '<br/>')
                # & < > karakterlerini escape et
                para_html = para_html.replace('&', '&amp;')
                para_html = para_html.replace('<br/>', '<!BR!>')  # Geçici koruma
                para_html = para_html.replace('<', '&lt;').replace('>', '&gt;')
                para_html = para_html.replace('<!BR!>', '<br/>')  # Geri al
                story.append(Paragraph(para_html, metin_stil))
        
        story.append(Spacer(1, 1*cm))
        
        # Uyarı
        uyari_stil = ParagraphStyle(
            'Warning',
            parent=styles['BodyText'],
            fontSize=9,
            textColor=colors.HexColor('#666666'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Times-Italic',
        )
        
        story.append(Paragraph(
            'Bu rapor yatirim tavsiyesi degildir. Yatirim kararlarinizi kendi arastirmaniza dayanarak alin.',
            uyari_stil
        ))
        
        # PDF oluştur
        doc.build(story)
        buf.seek(0)
        
        return buf


# Singleton instance
_gorsel_olusturucu: Optional[GorselOlusturucu] = None


def gorsel_olusturucu_al() -> GorselOlusturucu:
    """Görsel oluşturucu singleton instance'ını döndür."""
    global _gorsel_olusturucu
    if _gorsel_olusturucu is None:
        _gorsel_olusturucu = GorselOlusturucu()
    return _gorsel_olusturucu
