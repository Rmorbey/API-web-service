#!/usr/bin/env python3
"""
Test map data processing
"""

import json
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from projects.fundraising_tracking_app.strava_integration.smart_strava_cache import SmartStravaCache

def test_map_data():
    """Test map data processing"""
    print("🔍 Testing map data processing...")
    
    # Load cache
    cache = SmartStravaCache()
    activities = cache.get_activities_smart(1)
    
    if activities:
        activity = activities[0]
        print(f"Activity: {activity.get('name', 'Unknown')}")
        print(f"Activity keys: {list(activity.keys())}")
        
        map_data = activity.get("map", {})
        print(f"Map keys: {list(map_data.keys())}")
        print(f"Bounds: {map_data.get('bounds', {})}")
        print(f"Polyline length: {len(map_data.get('polyline', ''))}")
        
        # Test the API processing
        print("\n🔍 Testing API processing...")
        detailed_activity = activity
        map_data = detailed_activity.get("map", {})
        optimized_map = {
            "polyline": map_data.get("polyline"),
            "bounds": map_data.get("bounds", {})
        }
        print(f"Optimized bounds: {optimized_map.get('bounds', {})}")

if __name__ == "__main__":
    test_map_data()
