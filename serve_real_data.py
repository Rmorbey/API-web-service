#!/usr/bin/env python3
"""
Temporarily serve real Strava data through the test-feed endpoint
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

def serve_real_data():
    """Get real activities and serve them through test-feed endpoint"""
    
    print("🚀 Getting real Strava data for frontend...")
    print(f"📅 Timestamp: {datetime.now().isoformat()}")
    print()
    
    try:
        # Initialize smart cache
        cache = SmartStravaCache()
        
        print("📡 Fetching real activities using smart cache...")
        
        # Get real activities
        activities = cache.get_activities_smart(limit=2)
        
        if activities and len(activities) > 0:
            print(f"✅ Success! Retrieved {len(activities)} real activities")
            
            # Create a temporary test cache file with real data
            test_data = {
                "timestamp": datetime.now().isoformat(),
                "activities": activities
            }
            
            # Save to the test cache file (this will be served by test-feed endpoint)
            test_cache_file = "projects/fundraising_tracking_app/strava_integration/test_strava_cache.json"
            
            # Backup the original test data
            backup_file = "projects/fundraising_tracking_app/strava_integration/test_strava_cache_backup.json"
            if os.path.exists(test_cache_file):
                os.rename(test_cache_file, backup_file)
                print(f"💾 Backed up original test data to: {backup_file}")
            
            # Write real data to test cache file
            with open(test_cache_file, 'w') as f:
                json.dump(test_data, f, indent=2)
            
            print(f"💾 Saved real data to: {test_cache_file}")
            print("🌐 Frontend will now display real Strava activities!")
            print()
            
            # Show what we're serving
            for i, activity in enumerate(activities, 1):
                print(f"{i}. {activity.get('name')} (ID: {activity.get('id')})")
                print(f"   Type: {activity.get('type')} | Distance: {activity.get('distance', 0)}m")
                print(f"   Description: {activity.get('description', 'None')[:50]}...")
                print(f"   Comments: {len(activity.get('comments', []))} | Photos: {activity.get('photos', {}).get('count', 0)}")
                print()
            
        else:
            print("⚠️ No activities returned from smart cache")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    serve_real_data()
