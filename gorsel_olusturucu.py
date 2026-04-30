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


# ═══════════════════════════════════════════════════════════════════════════════
# YENİ: GELİŞMİŞ GÖRSEL ÖZELLİKLERİ
# ═══════════════════════════════════════════════════════════════════════════════

class GelismisGorselOlusturucu(GorselOlusturucu):
    """Gelişmiş görsel özellikleri ile genişletilmiş sınıf"""
    
    def __init__(self):
        super().__init__()
        # Yeni renk paletleri
        self.renk_paletleri = {
            "varsayilan": {
                'baslik': '#1a1a2e',
                'vurgu': '#0f3460',
                'pozitif': '#16213e',
                'notr': '#533483',
                'negatif': '#e94560',
            },
            "profesyonel": {
                'baslik': '#2c3e50',
                'vurgu': '#3498db',
                'pozitif': '#27ae60',
                'notr': '#95a5a6',
                'negatif': '#e74c3c',
            },
            "modern": {
                'baslik': '#1e272e',
                'vurgu': '#0984e3',
                'pozitif': '#00b894',
                'notr': '#636e72',
                'negatif': '#d63031',
            },
        }
    
    def heatmap_grafigi(
        self,
        data: dict[str, dict[str, float]],
        baslik: str,
        x_etiket: str = "Kategori",
        y_etiket: str = "Metrik",
    ) -> Optional[io.BytesIO]:
        """
        Heatmap (ısı haritası) grafiği oluştur
        
        Args:
            data: {satir_adi: {sutun_adi: deger}}
            baslik: Grafik başlığı
        
        Returns:
            BytesIO buffer (PNG) veya None
        """
        if not MATPLOTLIB_VAR:
            return None
        
        if not data:
            return None
        
        # Verileri matrise çevir
        satirlar = list(data.keys())
        sutunlar = list(next(iter(data.values())).keys())
        
        matris = []
        for satir in satirlar:
            satir_data = []
            for sutun in sutunlar:
                satir_data.append(data[satir].get(sutun, 0))
            matris.append(satir_data)
        
        # Grafik oluştur
        fig, ax = plt.subplots(figsize=(10, 8), facecolor='white')
        
        im = ax.imshow(matris, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)
        
        # Eksen etiketleri
        ax.set_xticks(range(len(sutunlar)))
        ax.set_yticks(range(len(satirlar)))
        ax.set_xticklabels(sutunlar, rotation=45, ha='right')
        ax.set_yticklabels(satirlar)
        
        # Değerleri hücrelere yaz
        for i in range(len(satirlar)):
            for j in range(len(sutunlar)):
                text = ax.text(j, i, f'{matris[i][j]:.0f}',
                             ha="center", va="center", color="black", fontsize=10, fontweight='600')
        
        # Colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Değer', rotation=270, labelpad=20, fontsize=10, fontweight='600')
        
        # Başlık
        ax.set_title(baslik, fontsize=14, fontweight='bold', color='#1a1a2e', pad=20)
        ax.set_xlabel(x_etiket, fontsize=11, fontweight='600')
        ax.set_ylabel(y_etiket, fontsize=11, fontweight='600')
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        plt.close(fig)
        
        return buf
    
    def radar_chart(
        self,
        kategoriler: list[str],
        degerler: list[float],
        baslik: str,
        max_deger: float = 100,
    ) -> Optional[io.BytesIO]:
        """
        Radar (örümcek ağı) grafiği oluştur
        
        Args:
            kategoriler: Kategori isimleri
            degerler: Her kategori için değer (0-max_deger)
            baslik: Grafik başlığı
            max_deger: Maksimum değer
        
        Returns:
            BytesIO buffer (PNG) veya None
        """
        if not MATPLOTLIB_VAR:
            return None
        
        if not kategoriler or not degerler:
            return None
        
        # Açıları hesapla
        N = len(kategoriler)
        angles = [n / float(N) * 2 * 3.14159 for n in range(N)]
        degerler += degerler[:1]  # Döngüyü kapat
        angles += angles[:1]
        
        # Grafik oluştur
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'), facecolor='white')
        
        # Çizgi ve alan
        ax.plot(angles, degerler, 'o-', linewidth=2, color='#16213e', label='Skor')
        ax.fill(angles, degerler, alpha=0.25, color='#16213e')
        
        # Kategori etiketleri
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(kategoriler, fontsize=10)
        
        # Y ekseni
        ax.set_ylim(0, max_deger)
        ax.set_yticks([max_deger * 0.25, max_deger * 0.5, max_deger * 0.75, max_deger])
        ax.set_yticklabels([f'{int(max_deger * 0.25)}', f'{int(max_deger * 0.5)}',
                           f'{int(max_deger * 0.75)}', f'{int(max_deger)}'], fontsize=8, color='#666666')
        
        # Grid
        ax.grid(True, linestyle='--', alpha=0.3)
        
        # Başlık
        plt.title(baslik, size=14, fontweight='bold', color='#1a1a2e', pad=20)
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        plt.close(fig)
        
        return buf
    
    def watermark_ekle(
        self,
        gorsel_buffer: io.BytesIO,
        watermark_text: str = "OKWIS AI",
    ) -> io.BytesIO:
        """
        Görsele watermark ekle
        
        Args:
            gorsel_buffer: Orijinal görsel
            watermark_text: Watermark metni
        
        Returns:
            Watermark eklenmiş görsel
        """
        if not MATPLOTLIB_VAR:
            return gorsel_buffer
        
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Görseli aç
            gorsel_buffer.seek(0)
            img = Image.open(gorsel_buffer)
            
            # Watermark ekle
            draw = ImageDraw.Draw(img)
            
            # Font (varsayılan)
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except Exception:
                font = ImageFont.load_default()
            
            # Watermark pozisyonu (sağ alt köşe)
            width, height = img.size
            text_bbox = draw.textbbox((0, 0), watermark_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            x = width - text_width - 20
            y = height - text_height - 20
            
            # Watermark çiz (yarı saydam)
            draw.text((x, y), watermark_text, fill=(26, 26, 46, 128), font=font)
            
            # Yeni buffer'a kaydet
            output = io.BytesIO()
            img.save(output, format='PNG')
            output.seek(0)
            
            return output
        except Exception:
            # Hata durumunda orijinal görseli döndür
            return gorsel_buffer
    
    def karsilastirma_grafigi(
        self,
        veri1: dict,
        veri2: dict,
        etiket1: str,
        etiket2: str,
        baslik: str,
    ) -> Optional[io.BytesIO]:
        """
        İki veri setini karşılaştırmalı grafik
        
        Args:
            veri1: {kategori: deger}
            veri2: {kategori: deger}
            etiket1: İlk veri seti etiketi
            etiket2: İkinci veri seti etiketi
            baslik: Grafik başlığı
        
        Returns:
            BytesIO buffer (PNG) veya None
        """
        if not MATPLOTLIB_VAR:
            return None
        
        if not veri1 or not veri2:
            return None
        
        kategoriler = list(veri1.keys())
        degerler1 = list(veri1.values())
        degerler2 = list(veri2.values())
        
        x = range(len(kategoriler))
        width = 0.35
        
        fig, ax = plt.subplots(figsize=(10, 6), facecolor='white')
        
        bars1 = ax.bar([i - width/2 for i in x], degerler1, width, label=etiket1,
                       color='#16213e', alpha=0.85)
        bars2 = ax.bar([i + width/2 for i in x], degerler2, width, label=etiket2,
                       color='#0f3460', alpha=0.85)
        
        # Değerleri bar'ların üzerine yaz
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}',
                       ha='center', va='bottom', fontsize=9, fontweight='600')
        
        ax.set_xlabel('Kategori', fontsize=11, fontweight='600')
        ax.set_ylabel('Değer', fontsize=11, fontweight='600')
        ax.set_title(baslik, fontsize=14, fontweight='bold', color='#1a1a2e', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(kategoriler, rotation=45, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        plt.close(fig)
        
        return buf


# Gelişmiş singleton instance
_gelismis_gorsel_olusturucu: Optional[GelismisGorselOlusturucu] = None


def gelismis_gorsel_olusturucu_al() -> GelismisGorselOlusturucu:
    """Gelişmiş görsel oluşturucu singleton instance'ını döndür."""
    global _gelismis_gorsel_olusturucu
    if _gelismis_gorsel_olusturucu is None:
        _gelismis_gorsel_olusturucu = GelismisGorselOlusturucu()
    return _gelismis_gorsel_olusturucu
