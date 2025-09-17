#!/usr/bin/env python3
"""
Optimize the existing cache by removing redundant data
"""

import json
import os

def optimize_cache():
    """Optimize the test cache by removing redundant fields"""
    
    # Load current cache
    cache_path = 'projects/fundraising_tracking_app/strava_integration/test_strava_cache.json'
    
    if not os.path.exists(cache_path):
        print(f"❌ Cache file not found: {cache_path}")
        return
    
    with open(cache_path, 'r') as f:
        cache_data = json.load(f)
    
    print(f"📊 Original cache size: {len(json.dumps(cache_data))} bytes")
    
    # Optimize each activity
    optimized_activities = []
    
    for activity in cache_data.get('activities', []):
        print(f"\\n🔧 Optimizing activity: {activity.get('name')}")
        
        # Create optimized activity
        optimized_activity = {
            "id": activity["id"],
            "name": activity["name"],
            "type": activity["type"],
            "distance": activity["distance"],
            "moving_time": activity["moving_time"],
            "start_date_local": activity["start_date_local"],
            "description": activity.get("description", ""),
            "comment_count": activity.get("comment_count", 0),
        }
        
        # Optimize map data - remove summary_polyline
        if "map" in activity:
            map_data = activity["map"]
            optimized_activity["map"] = {
                "polyline": map_data.get("polyline"),
                "bounds": map_data.get("bounds", {})
            }
            print(f"  🗺️ Map: Removed summary_polyline ({len(map_data.get('summary_polyline', ''))} chars)")
        
        # Optimize photos - keep only 600px URL
        if "photos" in activity and activity["photos"]:
            photos_data = activity["photos"]
            if "primary" in photos_data:
                primary = photos_data["primary"]
                optimized_activity["photos"] = {
                    "primary": {
                        "unique_id": primary.get("unique_id"),
                        "type": primary.get("type"),
                        "url": primary.get("urls", {}).get("600", ""),  # Only keep 600px
                        "status": primary.get("status")
                    },
                    "count": photos_data.get("count", 0)
                }
                print(f"  📸 Photos: Simplified to single URL ({len(primary.get('urls', {}).get('600', ''))} chars)")
        
        # Keep comments and music as-is
        if "comments" in activity:
            optimized_activity["comments"] = activity["comments"]
            print(f"  💬 Comments: {len(activity['comments'])} comments")
        
        if "music" in activity:
            optimized_activity["music"] = activity["music"]
            print(f"  🎵 Music: {'✅' if activity['music'] else '❌'}")
        
        optimized_activities.append(optimized_activity)
    
    # Create optimized cache
    optimized_cache = {
        "timestamp": cache_data.get("timestamp"),
        "activities": optimized_activities
    }
    
    # Save optimized cache
    with open(cache_path, 'w') as f:
        json.dump(optimized_cache, f, indent=2)
    
    print(f"\\n🎉 OPTIMIZATION COMPLETE!")
    print(f"📊 Optimized cache size: {len(json.dumps(optimized_cache))} bytes")
    
    # Calculate savings
    original_size = len(json.dumps(cache_data))
    optimized_size = len(json.dumps(optimized_cache))
    savings = original_size - optimized_size
    savings_percent = (savings / original_size) * 100
    
    print(f"💾 Size reduction: {savings:,} bytes ({savings_percent:.1f}%)")
    print(f"📁 Cache saved to: {cache_path}")

if __name__ == "__main__":
    optimize_cache()
