"""
Test script for country-specific RSS feeds in magazin_baglam.py
"""

import logging
from magazin_baglam import _ulke_rss_yukle, _ulke_rss_al, topla_magazin_baglami

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def test_rss_yukle():
    """Test RSS data loading"""
    print("\n=== TEST 1: RSS Data Loading ===")
    data = _ulke_rss_yukle()
    
    if data:
        print(f"✓ RSS data loaded successfully")
        print(f"✓ Countries available: {len(data)} ({', '.join(list(data.keys())[:5])}...)")
    else:
        print("✗ Failed to load RSS data")
    
    return data

def test_ulke_rss_al():
    """Test country-specific RSS retrieval"""
    print("\n=== TEST 2: Country-Specific RSS Retrieval ===")
    
    test_cases = [
        ("Türkiye", "magazin"),
        ("Japonya", "magazin"),
        ("ABD", "magazin"),
        ("Çin", "magazin"),
        ("NonExistentCountry", "magazin"),  # Should fallback to DEFAULT
    ]
    
    for ulke, kategori in test_cases:
        feeds = _ulke_rss_al(ulke, kategori)
        print(f"\n{ulke} ({kategori}):")
        print(f"  ✓ Found {len(feeds)} RSS feeds")
        for i, feed in enumerate(feeds[:2], 1):  # Show first 2
            print(f"    {i}. {feed[:60]}...")

def test_topla_magazin_baglami():
    """Test full context gathering with country-specific feeds"""
    print("\n=== TEST 3: Full Context Gathering ===")
    
    test_countries = ["Türkiye", "Japonya", "ABD"]
    
    for ulke in test_countries:
        print(f"\n--- Testing {ulke} ---")
        try:
            context = topla_magazin_baglami(ulke)
            
            # Check if country is mentioned
            if ulke in context:
                print(f"  ✓ Country '{ulke}' mentioned in context")
            else:
                print(f"  ✗ Country '{ulke}' NOT mentioned in context")
            
            # Check context length
            print(f"  ✓ Context length: {len(context)} characters")
            
            # Check for key phrases
            if "magazin" in context.lower() or "viral" in context.lower():
                print(f"  ✓ Contains magazine/viral keywords")
            
            # Show first 200 chars
            print(f"  Preview: {context[:200]}...")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("MAGAZIN RSS COUNTRY-SPECIFIC TEST")
    print("=" * 60)
    
    # Run tests
    test_rss_yukle()
    test_ulke_rss_al()
    test_topla_magazin_baglami()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)
