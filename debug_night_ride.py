#!/usr/bin/env python3
"""
Debug Night Ride complete data collection
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

def debug_night_ride():
    """Debug Night Ride complete data collection"""
    
    print("🔍 Debugging Night Ride complete data collection...")
    print(f"📅 Timestamp: {datetime.now().isoformat()}")
    print()
    
    try:
        # Initialize smart cache
        cache = SmartStravaCache()
        
        # Get Night Ride activity ID
        night_ride_id = 15723207147
        
        print(f"📡 Getting complete data for Night Ride (ID: {night_ride_id})...")
        
        # Force complete data collection
        complete_data = cache.get_complete_activity_data(night_ride_id)
        
        if complete_data:
            print(f"✅ Success! Retrieved complete data for Night Ride")
            print(f"🏃 Name: {complete_data.get('name', 'Unknown')}")
            print(f"📝 Description: {complete_data.get('description', 'None')}")
            print(f"💬 Comments: {len(complete_data.get('comments', []))}")
            for i, comment in enumerate(complete_data.get('comments', []), 1):
                print(f"   {i}. {comment.get('text', 'No text')} - {comment.get('athlete', {}).get('firstname', 'Unknown')}")
            print(f"📸 Photos: {complete_data.get('photos', {}).get('count', 0)}")
            if complete_data.get('photos', {}).get('primary'):
                primary = complete_data['photos']['primary']
                print(f"   Primary photo: {primary.get('urls', {})}")
            print(f"🎵 Music: {complete_data.get('music', {})}")
            print(f"🗺️ Map: {complete_data.get('map', {}).get('point_count', 0)} GPS points")
            
            # Save complete data
            with open('night_ride_complete_debug.json', 'w') as f:
                json.dump(complete_data, f, indent=2)
            
            print()
            print("💾 Saved complete Night Ride data to: night_ride_complete_debug.json")
            
        else:
            print("⚠️ No complete data returned for Night Ride")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_night_ride()
