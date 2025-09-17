#!/usr/bin/env python3
"""
Update existing cache with proper map coordinates and bounds
"""

import json
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from projects.fundraising_tracking_app.strava_integration.smart_strava_cache import SmartStravaCache

def update_cache_map_data():
    """Update existing cache with proper map coordinates"""
    print("🔄 Updating cache with proper map coordinates...")
    
    # Load the cache
    cache_file = "projects/fundraising_tracking_app/strava_integration/strava_cache.json"
    
    with open(cache_file, 'r') as f:
        cache_data = json.load(f)
    
    # Create cache instance to use the new map processing
    cache = SmartStravaCache()
    
    updated_activities = []
    
    for activity in cache_data.get("activities", []):
        print(f"Processing activity: {activity.get('name', 'Unknown')}")
        
        # Get the original activity data from the map field
        original_map = activity.get("map", {})
        
        # Process the map data with the new enhanced method
        enhanced_map = cache._process_map_data({"map": original_map})
        
        # Update the activity with enhanced map data
        activity["map"] = enhanced_map
        activity["start_latlng"] = enhanced_map.get("start_latlng")
        activity["end_latlng"] = enhanced_map.get("end_latlng")
        
        updated_activities.append(activity)
    
    # Update cache data
    cache_data["activities"] = updated_activities
    
    # Save updated cache
    with open(cache_file, 'w') as f:
        json.dump(cache_data, f, indent=2)
    
    print(f"✅ Updated {len(updated_activities)} activities with enhanced map data")
    
    # Test the first activity
    if updated_activities:
        first_activity = updated_activities[0]
        map_data = first_activity.get("map", {})
        print(f"\n🎯 Sample activity: {first_activity.get('name')}")
        print(f"  - Coordinates: {len(map_data.get('coordinates', []))} points")
        print(f"  - Bounds: {map_data.get('bounds', {})}")
        print(f"  - Start: {map_data.get('start_latlng')}")
        print(f"  - End: {map_data.get('end_latlng')}")

if __name__ == "__main__":
    update_cache_map_data()
