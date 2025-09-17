#!/usr/bin/env python3
"""
Test script to collect 1 single activity from Strava API v3 with token refresh
"""

import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Add the project path to import our modules
import sys
sys.path.append('projects/fundraising_tracking_app')

from strava_integration.strava_token_manager import StravaTokenManager
from strava_integration.smart_strava_cache import SmartStravaCache

# Load environment variables
load_dotenv()

async def test_single_strava_with_refresh():
    """Collect 1 single activity from Strava API v3 with token refresh"""
    
    print("🚀 Testing single Strava API v3 call with token refresh...")
    print(f"📅 Timestamp: {datetime.now().isoformat()}")
    print()
    
    try:
        # Initialize token manager and cache
        token_manager = StravaTokenManager()
        cache = SmartStravaCache()
        
        print("🔄 Getting valid Strava token...")
        access_token = token_manager.get_valid_access_token()
        
        if access_token:
            print("✅ Valid token obtained!")
            
            # Now try to get activities using the smart cache
            print("📡 Fetching 1 activity using smart cache...")
            
            # Get activities with limit of 1
            activities = await cache.get_activities_smart(limit=1)
            
            if activities and len(activities) > 0:
                activity = activities[0]
                print(f"✅ Success! Retrieved {len(activities)} activity(ies)")
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
                        "processed_activity": activity,
                        "source": "smart_cache"
                    }
                }
                
                with open('single_strava_activity_test.json', 'w') as f:
                    json.dump(test_data, f, indent=2)
                
                print()
                print("💾 Saved processed activity to: single_strava_activity_test.json")
                print("🔍 Next: We'll compare this with our test cache structure")
                
            else:
                print("⚠️ No activities returned from smart cache")
                
        else:
            print("❌ Failed to refresh token")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_single_strava_with_refresh())
