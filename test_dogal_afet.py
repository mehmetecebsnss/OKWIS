"""
Test script for natural disaster context with alternative analysis
"""

import logging
from dogal_afet_baglam import topla_dogal_afet_baglami, _ulke_afet_profili, _son_depremler

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def test_ulke_afet_profili():
    """Test country disaster profiles"""
    print("\n=== TEST 1: Country Disaster Profiles ===")
    
    test_countries = ["Türkiye", "Japonya", "ABD", "Çin", "NonExistent"]
    
    for ulke in test_countries:
        print(f"\n--- {ulke} ---")
        profil = _ulke_afet_profili(ulke)
        print(profil[:200] + "..." if len(profil) > 200 else profil)

def test_son_depremler():
    """Test earthquake data retrieval"""
    print("\n=== TEST 2: Recent Earthquakes (M5.0+) ===")
    
    depremler = _son_depremler(min_magnitude=5.0, limit=5)
    
    if depremler:
        print(f"✓ Found {len(depremler)} earthquakes:")
        for deprem in depremler:
            print(f"  {deprem}")
    else:
        print("✓ No M5.0+ earthquakes in last 7 days (this will trigger alternative analysis)")

def test_topla_dogal_afet_baglami():
    """Test full context gathering with alternative analysis"""
    print("\n=== TEST 3: Full Context Gathering ===")
    
    test_countries = ["Türkiye", "Japonya", "Çin"]
    
    for ulke in test_countries:
        print(f"\n--- Testing {ulke} ---")
        try:
            context = topla_dogal_afet_baglami(ulke)
            
            # Check if country is mentioned
            if ulke in context:
                print(f"  ✓ Country '{ulke}' mentioned in context")
            
            # Check context length
            print(f"  ✓ Context length: {len(context)} characters")
            
            # Check for alternative analysis keywords
            if "Risk Profili" in context or "HAZIRLıK EKONOMİSİ" in context:
                print(f"  ✓ Contains alternative analysis (no earthquakes)")
            elif "depremler (USGS)" in context:
                print(f"  ✓ Contains earthquake data")
            
            # Check for key sections
            if "Analiz Rehberi" in context:
                print(f"  ✓ Contains analysis guide")
            
            # Show preview
            lines = context.split('\n')
            print(f"  Preview (first 10 lines):")
            for line in lines[:10]:
                print(f"    {line[:80]}")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("=" * 60)
    print("NATURAL DISASTER ALTERNATIVE ANALYSIS TEST")
    print("=" * 60)
    
    # Run tests
    test_ulke_afet_profili()
    test_son_depremler()
    test_topla_dogal_afet_baglami()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)
