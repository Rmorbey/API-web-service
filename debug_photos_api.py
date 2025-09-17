#!/usr/bin/env python3
"""
Debug script to check photos API call directly
"""

import os
import json
import httpx
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def debug_photos_api():
    """Debug the photos API call directly"""
    
    print("🔍 Debugging Strava Photos API call...")
    print(f"📅 Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Get credentials
    access_token = os.getenv('STRAVA_ACCESS_TOKEN')
    if not access_token:
        print("❌ No STRAVA_ACCESS_TOKEN found")
        return
    
    activity_id = 15806551007  # The activity we're testing
    
    try:
        async with httpx.AsyncClient() as client:
            # Make direct photos API call
            photos_url = f"https://www.strava.com/api/v3/activities/{activity_id}/photos"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
            
            print(f"📡 Making photos API call to: {photos_url}")
            response = await client.get(photos_url, headers=headers, timeout=30.0)
            
            print(f"📊 Response status: {response.status_code}")
            print(f"📊 Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                photos_data = response.json()
                print(f"✅ Success! Retrieved photos data")
                print(f"📸 Raw photos data: {json.dumps(photos_data, indent=2)}")
                
                # Save raw photos data
                with open('raw_photos_data.json', 'w') as f:
                    json.dump(photos_data, f, indent=2)
                
                print()
                print("💾 Saved raw photos data to: raw_photos_data.json")
                
            else:
                print(f"❌ API Error: {response.status_code}")
                print(f"Response: {response.text}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(debug_photos_api())
