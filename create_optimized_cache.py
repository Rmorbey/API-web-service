#!/usr/bin/env python3
"""
Create an optimized version of the test cache with only essential data.
"""

import json
import sys
import os

def create_optimized_cache():
    """Create an optimized cache with only essential data for frontend."""
    
    # Load the current test cache
    with open('projects/fundraising_tracking_app/strava_integration/test_strava_cache.json', 'r') as f:
        cache_data = json.load(f)
    
    print("🔧 CREATING OPTIMIZED CACHE")
    print("=" * 40)
    
    # Fields we actually need for the frontend
    essential_fields = {
        'id': 'Activity ID',
        'name': 'Activity name/title', 
        'type': 'Activity type (Run, Ride, etc.)',
        'distance': 'Distance in meters',
        'moving_time': 'Duration in seconds',
        'start_date_local': 'Start date',
        'description': 'Activity description',
        'comment_count': 'Number of comments',
        'photos': 'Photo data',
        'music': 'Music detection and widgets',
        'comments': 'Comment text',
        'map': 'Map data (polyline only)'
    }
    
    # Create optimized activities
    optimized_activities = []
    
    for activity in cache_data.get('activities', []):
        print(f"📊 Optimizing: {activity.get('name', 'Unknown')}")
        
        # Create optimized activity with only essential fields
        optimized_activity = {}
        
        # Copy essential basic fields
        for field in ['id', 'name', 'type', 'distance', 'moving_time', 'start_date_local', 'description', 'comment_count']:
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
                print(f"  ❌ Removing {len(map_data['gps_points'])} GPS points (saving ~{len(json.dumps(map_data['gps_points'])):,} chars)")
            
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
    
    # Save optimized cache
    optimized_file = 'projects/fundraising_tracking_app/strava_integration/test_strava_cache_optimized.json'
    with open(optimized_file, 'w') as f:
        json.dump(optimized_cache, f, indent=2)
    
    print(f"💾 Saved optimized cache to: {optimized_file}")
    
    # Show what we removed
    print(f"\n🗑️ REMOVED REDUNDANT FIELDS:")
    sample_activity = cache_data['activities'][0]
    optimized_sample = optimized_activities[0]
    
    removed_fields = set(sample_activity.keys()) - set(optimized_sample.keys())
    for field in sorted(removed_fields):
        value = sample_activity[field]
        if isinstance(value, (dict, list)):
            print(f"  ✗ {field}: {type(value).__name__} ({len(value) if hasattr(value, '__len__') else 'N/A'} items)")
        else:
            print(f"  ✗ {field}: {value}")
    
    return optimized_file

if __name__ == "__main__":
    create_optimized_cache()
