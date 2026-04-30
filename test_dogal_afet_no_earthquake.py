"""
Test script for natural disaster alternative analysis when NO earthquakes
"""

import logging
import sys
from unittest.mock import patch
from dogal_afet_baglam import topla_dogal_afet_baglami, _ulke_afet_profili

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def test_no_earthquake_scenario():
    """Test alternative analysis when no earthquakes are found"""
    print("\n=== TEST: No Earthquake Scenario (Alternative Analysis) ===")
    
    test_countries = ["Türkiye", "Japonya", "Çin", "ABD"]
    
    # Mock _son_depremler to return empty list (no earthquakes)
    with patch('dogal_afet_baglam._son_depremler', return_value=[]):
        for ulke in test_countries:
            print(f"\n{'='*60}")
            print(f"Testing: {ulke} (NO EARTHQUAKES)")
            print('='*60)
            
            try:
                context = topla_dogal_afet_baglami(ulke)
                
                # Check for alternative analysis markers
                has_alternative = False
                if "Risk Profili" in context:
                    print(f"✓ Contains disaster risk profile")
                    has_alternative = True
                
                if "HAZIRLıK EKONOMİSİ" in context or "HAZIRLIK EKONOMİSİ" in context:
                    print(f"✓ Contains preparedness economy analysis")
                    has_alternative = True
                
                if "Alternatif Analiz" in context:
                    print(f"✓ Contains alternative analysis marker")
                    has_alternative = True
                
                if "M5.0+ deprem kaydı yok" in context:
                    print(f"✓ Correctly states no earthquakes")
                
                if has_alternative:
                    print(f"✅ Alternative analysis ACTIVE")
                else:
                    print(f"❌ Alternative analysis NOT FOUND")
                
                # Show key sections
                print(f"\nContext length: {len(context)} characters")
                print(f"\nKey sections:")
                
                # Extract and show analysis guide
                if "### Analiz Rehberi" in context:
                    start = context.find("### Analiz Rehberi")
                    end = context.find("###", start + 1)
                    if end == -1:
                        end = len(context)
                    analiz_section = context[start:end].strip()
                    
                    print("\n" + "-"*60)
                    print(analiz_section[:500])
                    if len(analiz_section) > 500:
                        print("...")
                    print("-"*60)
                
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()

def test_country_profiles():
    """Show all country disaster profiles"""
    print("\n=== Country Disaster Profiles ===")
    
    countries = ["Türkiye", "Japonya", "ABD", "Çin", "Endonezya", "İtalya", "Meksika", "Şili"]
    
    for ulke in countries:
        print(f"\n{ulke}:")
        profil = _ulke_afet_profili(ulke)
        print(profil)

if __name__ == "__main__":
    print("=" * 60)
    print("NATURAL DISASTER - NO EARTHQUAKE SCENARIO TEST")
    print("=" * 60)
    
    # Run tests
    test_no_earthquake_scenario()
    test_country_profiles()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)
