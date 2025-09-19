#!/usr/bin/env python3
"""
Clean up redundant data from strava_cache.json
Removes coordinates, summary_polyline, duplicate coords, and unused fields
"""

import json
import os

def cleanup_cache():
    """Clean up redundant data from cache"""
    print("🧹 CLEANING UP REDUNDANT DATA...")
    
    cache_file = "projects/fundraising_tracking_app/strava_integration/strava_cache.json"
    
    # Load current cache
    with open(cache_file, 'r') as f:
        cache = json.load(f)
    
    original_size = len(json.dumps(cache))
    print(f"📊 Original file size: {original_size:,} characters")
    
    activities = cache.get("activities", [])
    print(f"📊 Processing {len(activities)} activities")
    
    cleaned_activities = []
    
    for i, activity in enumerate(activities):
        print(f"🧹 Cleaning activity {i+1}/{len(activities)}: {activity.get('name', 'Unknown')}")
        
        # Keep only essential fields (including timing for frontend)
        cleaned_activity = {
            "id": activity.get("id"),
            "name": activity.get("name", ""),
            "type": activity.get("type", ""),
            "distance": activity.get("distance", 0),
            "moving_time": activity.get("moving_time", 0),  # Required for duration calculations
            "elapsed_time": activity.get("elapsed_time", 0),  # May be useful for comparison
            "start_date": activity.get("start_date", ""),
            "start_date_local": activity.get("start_date_local", ""),
            "timezone": activity.get("timezone", ""),
            "description": activity.get("description", ""),
            "start_latlng": activity.get("start_latlng"),
            "end_latlng": activity.get("end_latlng"),
            "map": {
                "polyline": activity.get("map", {}).get("polyline"),
                "bounds": activity.get("map", {}).get("bounds", {})
            },
            "photos": activity.get("photos", {}),
            "comments": activity.get("comments", []),
            "music": activity.get("music", {})
        }
        
        cleaned_activities.append(cleaned_activity)
    
    # Update cache with cleaned data
    cache["activities"] = cleaned_activities
    cache["cleaned_at"] = "2025-09-18T01:21:00.000000"
    
    # Save cleaned cache
    with open(cache_file, 'w') as f:
        json.dump(cache, f, indent=2)
    
    new_size = len(json.dumps(cache))
    savings = original_size - new_size
    savings_percent = (savings / original_size) * 100
    
    print(f"\n🎉 CLEANUP COMPLETE!")
    print(f"📊 Original size: {original_size:,} characters")
    print(f"📊 New size: {new_size:,} characters")
    print(f"💰 Savings: {savings:,} characters ({savings_percent:.1f}%)")
    print(f"✅ Removed redundant data from {len(cleaned_activities)} activities")

if __name__ == "__main__":
    cleanup_cache()
