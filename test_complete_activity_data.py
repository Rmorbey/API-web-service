#!/usr/bin/env python3
"""
Test script to get complete activity data including comments
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

def test_complete_activity_data():
    """Get complete activity data including comments"""
    
    print("🚀 Testing complete activity data collection...")
    print(f"📅 Timestamp: {datetime.now().isoformat()}")
    print()
    
    try:
        # Initialize smart cache
        cache = SmartStravaCache()
        
        # Get the activity ID from our previous test
        activity_id = 15806551007  # From the real data we collected
        
        print(f"📡 Fetching complete data for activity {activity_id}...")
        print("   (This will collect comments, photos, and detailed map data)")
        
        # Get complete activity data
        complete_activity = cache.get_complete_activity_data(activity_id)
        
        if complete_activity:
            print(f"✅ Success! Retrieved complete data for activity {activity_id}")
            print(f"🏃 Activity: {complete_activity.get('name', 'Unknown')}")
            print(f"🆔 ID: {complete_activity.get('id')}")
            
            # Check comments
            comments = complete_activity.get('comments', [])
            print(f"💬 Comments: {len(comments)} found")
            for i, comment in enumerate(comments, 1):
                print(f"   {i}. {comment.get('text', 'No text')} - {comment.get('athlete', {}).get('firstname', 'Unknown')} {comment.get('athlete', {}).get('lastname', '')}")
            
            # Check photos
            photos = complete_activity.get('photos', {})
            print(f"📸 Photos: {photos.get('count', 0)} found")
            if photos.get('primary'):
                print(f"   Primary photo: {photos['primary'].get('urls', {}).get('600', 'No URL')}")
            
            # Check music
            music = complete_activity.get('music', {})
            print(f"🎵 Music: {'Detected' if music else 'None'}")
            if music:
                print(f"   Music data: {music}")
            
            # Check map data
            map_data = complete_activity.get('map', {})
            print(f"🗺️ Map: {'Present' if map_data else 'None'}")
            if map_data:
                gps_points = map_data.get('gps_points', [])
                print(f"   GPS Points: {len(gps_points)}")
                polyline = map_data.get('summary_polyline', '')
                print(f"   Polyline: {len(polyline)} characters")
            
            # Save complete data
            test_data = {
                "complete_activity_test": {
                    "timestamp": datetime.now().isoformat(),
                    "activity_id": activity_id,
                    "complete_activity": complete_activity,
                    "source": "smart_cache_complete"
                }
            }
            
            with open('complete_strava_activity_test.json', 'w') as f:
                json.dump(test_data, f, indent=2)
            
            print()
            print("💾 Saved complete activity data to: complete_strava_activity_test.json")
            
        else:
            print("⚠️ No complete activity data returned")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_complete_activity_data()
