#!/usr/bin/env python3
"""
Collect the last 2 activities from Strava API v3 and store in cache
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Add the project path to import our modules
import sys
sys.path.append('projects/fundraising_tracking_app')

from strava_integration.smart_strava_cache import SmartStravaCache

# Load environment variables
load_dotenv()

def collect_last_2_activities():
    """Collect the last 2 activities from Strava API v3"""
    
    print("🚀 Collecting last 2 activities from Strava API v3...")
    print(f"📅 Timestamp: {datetime.now().isoformat()}")
    print()
    
    try:
        # Initialize smart cache
        cache = SmartStravaCache()
        
        print("📡 Fetching 2 activities using smart cache...")
        print("   (This will collect complete data including comments, photos, and music)")
        
        # Get 2 activities with complete data by using the complete data collection method
        activities = []
        basic_activities = cache.get_activities_smart(limit=2)
        
        # For each activity, collect complete data
        for activity in basic_activities:
            try:
                complete_activity = cache.get_complete_activity_data(activity["id"])
                activities.append(complete_activity)
            except Exception as e:
                print(f"⚠️ Failed to get complete data for activity {activity.get('id', 'unknown')}: {e}")
                # Use basic activity as fallback
                activities.append(activity)
        
        if activities and len(activities) > 0:
            print(f"✅ Success! Retrieved {len(activities)} activity(ies)")
            print()
            
            for i, activity in enumerate(activities, 1):
                print(f"=== ACTIVITY {i} ===")
                print(f"🏃 Name: {activity.get('name', 'Unknown')}")
                print(f"🆔 ID: {activity.get('id')}")
                print(f"📅 Date: {activity.get('start_date_local', 'Unknown')}")
                print(f"🏃 Type: {activity.get('type', 'Unknown')}")
                print(f"📏 Distance: {activity.get('distance', 0)} meters")
                print(f"⏱️ Duration: {activity.get('moving_time', 0)} seconds")
                
                # Check description
                description = activity.get('description', '')
                if description:
                    print(f"📝 Description: {description[:100]}{'...' if len(description) > 100 else ''}")
                else:
                    print("📝 Description: None")
                
                # Check comments
                comments = activity.get('comments', [])
                print(f"💬 Comments: {len(comments)} found")
                for j, comment in enumerate(comments[:2], 1):  # Show first 2 comments
                    print(f"   {j}. {comment.get('text', 'No text')} - {comment.get('athlete', {}).get('firstname', 'Unknown')}")
                
                # Check photos
                photos = activity.get('photos', {})
                print(f"📸 Photos: {photos.get('count', 0)} found")
                if photos.get('primary'):
                    primary = photos['primary']
                    print(f"   Status: {primary.get('status', 'Unknown')}")
                    urls = primary.get('urls', {})
                    if urls.get('600'):
                        print(f"   URL: {urls['600'][:80]}...")
                
                # Check music
                music = activity.get('music', {})
                if music:
                    print(f"🎵 Music: {music}")
                else:
                    print("🎵 Music: None")
                
                print()
            
            # Save the activities to the test cache
            test_cache_data = {
                "timestamp": datetime.now().isoformat(),
                "activities": activities,
                "source": "smart_cache_real_data"
            }
            
            test_cache_path = 'projects/fundraising_tracking_app/strava_integration/test_strava_cache.json'
            with open(test_cache_path, 'w') as f:
                json.dump(test_cache_data, f, indent=2)
            
            print(f"💾 Saved activities to: {test_cache_path}")
            print("🔍 Next: We'll test the frontend with this complete data")
            
        else:
            print("⚠️ No activities returned from smart cache")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    collect_last_2_activities()
