#!/usr/bin/env python3
"""
Update the existing cache to use optimized data structure
"""

import json
import os

def update_cache_to_optimized():
    """Update the test cache to use optimized data structure"""
    
    print("🔧 UPDATING CACHE TO OPTIMIZED STRUCTURE")
    print("=" * 50)
    
    # Load current test cache
    cache_file = 'projects/fundraising_tracking_app/strava_integration/test_strava_cache.json'
    with open(cache_file, 'r') as f:
        cache_data = json.load(f)
    
    print(f"📊 Original cache size: {len(json.dumps(cache_data)):,} characters")
    
    # Create optimized activities
    optimized_activities = []
    
    for activity in cache_data.get('activities', []):
        print(f"🔧 Optimizing: {activity.get('name', 'Unknown')}")
        
        # Create optimized activity with only essential fields
        optimized_activity = {}
        
        # Copy essential basic fields
        essential_fields = ['id', 'name', 'type', 'distance', 'moving_time', 'start_date_local', 'description', 'comment_count']
        for field in essential_fields:
            if field in activity:
                optimized_activity[field] = activity[field]
        
        # Copy photos data (already optimized)
        if 'photos' in activity:
            optimized_activity['photos'] = activity['photos']
        
        # Copy music data (already optimized)
        if 'music' in activity:
            optimized_activity['music'] = activity['music']
        
        # Copy comments data (already optimized)
        if 'comments' in activity:
            optimized_activity['comments'] = activity['comments']
        
        # Optimize map data - use polyline instead of GPS points
        if 'map' in activity:
            map_data = activity['map']
            optimized_map = {}
            
            # Keep only essential map data
            if 'polyline' in map_data:
                optimized_map['polyline'] = map_data['polyline']
            if 'summary_polyline' in map_data:
                optimized_map['summary_polyline'] = map_data['summary_polyline']
            if 'bounds' in map_data:
                optimized_map['bounds'] = map_data['bounds']
            
            # Remove GPS points (huge space saver!)
            if 'gps_points' in map_data:
                gps_count = len(map_data['gps_points'])
                gps_size = len(json.dumps(map_data['gps_points']))
                print(f"  ❌ Removing {gps_count} GPS points (saving ~{gps_size:,} chars)")
            
            optimized_activity['map'] = optimized_map
        
        optimized_activities.append(optimized_activity)
    
    # Create optimized cache structure
    optimized_cache = {
        'timestamp': cache_data.get('timestamp'),
        'activities': optimized_activities
    }
    
    # Calculate size savings
    original_size = len(json.dumps(cache_data))
    optimized_size = len(json.dumps(optimized_cache))
    savings = original_size - optimized_size
    savings_percent = (savings / original_size) * 100
    
    print(f"\n📈 SIZE OPTIMIZATION RESULTS:")
    print(f"  Original size: {original_size:,} characters")
    print(f"  Optimized size: {optimized_size:,} characters")
    print(f"  Space saved: {savings:,} characters ({savings_percent:.1f}%)")
    
    # Save optimized cache (overwrite the original)
    with open(cache_file, 'w') as f:
        json.dump(optimized_cache, f, indent=2)
    
    print(f"💾 Updated cache file: {cache_file}")
    
    # Verify the optimized cache
    print(f"\n✅ VERIFICATION:")
    with open(cache_file, 'r') as f:
        verify_data = json.load(f)
    
    print(f"  Activities: {len(verify_data.get('activities', []))}")
    for i, activity in enumerate(verify_data.get('activities', [])):
        map_data = activity.get('map', {})
        has_polyline = 'polyline' in map_data
        has_gps_points = 'gps_points' in map_data
        print(f"  Activity {i+1}: {activity.get('name')}")
        print(f"    Polyline: {'✅' if has_polyline else '❌'}")
        print(f"    GPS points: {'❌' if not has_gps_points else '⚠️'}")
    
    return optimized_cache

if __name__ == "__main__":
    update_cache_to_optimized()
