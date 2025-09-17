#!/usr/bin/env python3
"""
Test script to collect 1 single activity from Strava API v3
This will help us compare real data structure with our test cache
"""

import os
import json
import httpx
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_single_strava_api():
    """Collect 1 single activity from Strava API v3"""
    
    # Get credentials from environment
    access_token = os.getenv('STRAVA_ACCESS_TOKEN')
    if not access_token:
        print("❌ No STRAVA_ACCESS_TOKEN found in .env file")
        return
    
    print("🚀 Testing single Strava API v3 call...")
    print(f"📅 Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Strava API endpoint for activities
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    
    # Parameters - get only 1 activity
    params = {
        "per_page": 1,
        "page": 1
    }
    
    try:
        print("📡 Making API call to Strava...")
        with httpx.Client() as client:
            response = client.get(url, headers=headers, params=params, timeout=30.0)
        
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            activities = response.json()
            print(f"✅ Success! Retrieved {len(activities)} activity(ies)")
            
            if activities:
                activity = activities[0]
                print(f"🏃 Activity: {activity.get('name', 'Unknown')}")
                print(f"🆔 ID: {activity.get('id')}")
                print(f"📅 Date: {activity.get('start_date_local', 'Unknown')}")
                print(f"🏃 Type: {activity.get('type', 'Unknown')}")
                print(f"📏 Distance: {activity.get('distance', 0)} meters")
                print(f"⏱️ Duration: {activity.get('moving_time', 0)} seconds")
                
                # Check if it has a description (for music detection)
                description = activity.get('description', '')
                if description:
                    print(f"📝 Description: {description[:100]}{'...' if len(description) > 100 else ''}")
                else:
                    print("📝 Description: None")
                
                # Save to a test file for comparison
                test_data = {
                    "single_activity_test": {
                        "timestamp": datetime.now().isoformat(),
                        "api_response": activity,
                        "raw_response": response.text
                    }
                }
                
                with open('single_strava_activity_test.json', 'w') as f:
                    json.dump(test_data, f, indent=2)
                
                print()
                print("💾 Saved raw API response to: single_strava_activity_test.json")
                print("🔍 Next: We'll process this data and compare with our test cache structure")
                
            else:
                print("⚠️ No activities returned from API")
                
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except httpx.TimeoutException:
        print("❌ Request timed out")
    except httpx.RequestError as e:
        print(f"❌ Request error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_single_strava_api()
