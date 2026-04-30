"""
Test script for RSS fallback mechanism
"""

import logging
import sys
from rss_utils import fetch_rss_titles, get_fallback_urls

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def test_successful_rss():
    """Test with a working RSS feed"""
    print("\n=== TEST 1: Successful RSS Fetch ===")
    
    url = "https://feeds.bbci.co.uk/news/rss.xml"
    titles, used_url = fetch_rss_titles(url, limit=5)
    
    if titles:
        print(f"✓ Successfully fetched {len(titles)} titles from {used_url[:50]}")
        for i, title in enumerate(titles[:3], 1):
            print(f"  {i}. {title[:80]}")
    else:
        print(f"✗ Failed to fetch from {url}")

def test_failed_rss_with_fallback():
    """Test with a failing RSS feed and fallback"""
    print("\n=== TEST 2: Failed RSS with Fallback ===")
    
    # Use a non-existent URL to trigger fallback
    bad_url = "https://nonexistent-rss-feed-12345.com/rss.xml"
    fallback_urls = get_fallback_urls("world_news")
    
    print(f"Trying: {bad_url}")
    print(f"Fallback URLs: {len(fallback_urls)} available")
    
    titles, used_url = fetch_rss_titles(bad_url, limit=5, fallback_urls=fallback_urls)
    
    if titles:
        print(f"✓ Fallback successful! Used: {used_url[:50]}")
        print(f"✓ Fetched {len(titles)} titles")
        for i, title in enumerate(titles[:3], 1):
            print(f"  {i}. {title[:80]}")
    else:
        print(f"✗ All sources failed")

def test_fallback_categories():
    """Test fallback URL categories"""
    print("\n=== TEST 3: Fallback Categories ===")
    
    categories = ["world_news", "business", "technology", "entertainment"]
    
    for category in categories:
        urls = get_fallback_urls(category)
        print(f"\n{category}:")
        print(f"  ✓ {len(urls)} fallback URLs available")
        for i, url in enumerate(urls, 1):
            print(f"    {i}. {url[:60]}")

def test_reuters_fallback():
    """Test Reuters URL with fallback"""
    print("\n=== TEST 4: Reuters with Fallback ===")
    
    # Reuters URL from .env (may fail)
    reuters_url = "https://feeds.reuters.com/reuters/worldNews"
    fallback_urls = get_fallback_urls("world_news")
    
    print(f"Trying Reuters: {reuters_url}")
    
    titles, used_url = fetch_rss_titles(reuters_url, limit=5, fallback_urls=fallback_urls)
    
    if titles:
        if used_url == reuters_url:
            print(f"✓ Reuters working! Fetched {len(titles)} titles")
        else:
            print(f"⚠ Reuters failed, fallback used: {used_url[:50]}")
            print(f"✓ Fetched {len(titles)} titles from fallback")
        
        for i, title in enumerate(titles[:3], 1):
            print(f"  {i}. {title[:80]}")
    else:
        print(f"✗ All sources failed (Reuters + fallbacks)")

if __name__ == "__main__":
    print("=" * 60)
    print("RSS FALLBACK MECHANISM TEST")
    print("=" * 60)
    
    # Run tests
    test_successful_rss()
    test_failed_rss_with_fallback()
    test_fallback_categories()
    test_reuters_fallback()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)
