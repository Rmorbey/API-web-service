#!/usr/bin/env python3
"""
Test script to verify Deezer search logic for "A Kiss for the Whole World" by Enter Shikari
"""

import requests
import json

def test_deezer_search():
    """Test the Deezer search logic with the actual search implementation"""
    
    title = "A Kiss for the Whole World"
    artist = "Enter Shikari"
    music_type = "album"
    
    print(f"🎵 Testing Deezer search for: '{title}' by '{artist}' (type: {music_type})")
    print("=" * 60)
    
    # Clean and prepare search query
    clean_title = title.strip().replace('"', '').replace("'", "")
    clean_artist = artist.strip().replace('"', '').replace("'", "")
    
    # Try multiple search strategies
    search_queries = [
        f'"{clean_title}" "{clean_artist}"',  # Exact match with quotes
        f"{clean_title} {clean_artist}",      # Simple concatenation
        f"{clean_artist} {clean_title}",      # Artist first
        clean_title,                          # Title only
        clean_artist                          # Artist only
    ]
    
    search_endpoint = "https://api.deezer.com/search/album"
    
    # Try each search query
    for i, search_query in enumerate(search_queries, 1):
        print(f"\n🔍 Search Strategy {i}: '{search_query}'")
        print("-" * 40)
        
        try:
            encoded_query = search_query.replace(" ", "%20")
            search_url = f"{search_endpoint}?q={encoded_query}&limit=10"
            
            print(f"URL: {search_url}")
            
            # Make request to Deezer API
            response = requests.get(search_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                if data.get("data") and len(data["data"]) > 0:
                    print(f"Found {len(data['data'])} results:")
                    
                    # Look for exact matches first
                    exact_match_found = False
                    for j, result in enumerate(data["data"]):
                        result_title = result.get("title", "").lower()
                        result_artist = result.get("artist", {}).get("name", "").lower()
                        
                        print(f"  {j+1}. '{result.get('title')}' by '{result.get('artist', {}).get('name')}' (ID: {result['id']})")
                        
                        # Check for exact match
                        if (clean_title.lower() in result_title and clean_artist.lower() in result_artist) or \
                           (clean_artist.lower() in result_title and clean_title.lower() in result_artist):
                            print(f"     ✅ EXACT MATCH FOUND!")
                            print(f"     Deezer URL: https://www.deezer.com/album/{result['id']}")
                            print(f"     Widget URL: https://widget.deezer.com/widget/dark/album/{result['id']}")
                            exact_match_found = True
                            break
                    
                    if not exact_match_found:
                        print("     ⚠️  No exact match found in this search")
                        
                        # Try partial matching
                        for j, result in enumerate(data["data"]):
                            result_title = result.get("title", "").lower()
                            result_artist = result.get("artist", {}).get("name", "").lower()
                            
                            # Check for partial match (at least 80% of words match)
                            title_words = set(clean_title.lower().split())
                            artist_words = set(clean_artist.lower().split())
                            result_title_words = set(result_title.split())
                            result_artist_words = set(result_artist.split())
                            
                            title_match_ratio = len(title_words.intersection(result_title_words)) / len(title_words) if title_words else 0
                            artist_match_ratio = len(artist_words.intersection(result_artist_words)) / len(artist_words) if artist_words else 0
                            
                            if title_match_ratio >= 0.8 and artist_match_ratio >= 0.8:
                                print(f"     🎯 PARTIAL MATCH: {title_match_ratio:.1%} title, {artist_match_ratio:.1%} artist")
                                print(f"     Deezer URL: https://www.deezer.com/album/{result['id']}")
                                print(f"     Widget URL: https://widget.deezer.com/widget/dark/album/{result['id']}")
                                break
                        else:
                            print(f"     ❌ No partial match found either")
                else:
                    print("     No results found")
            else:
                print(f"     ❌ API Error: {response.status_code}")
                
        except Exception as e:
            print(f"     ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("🎵 Test completed!")

if __name__ == "__main__":
    test_deezer_search()
