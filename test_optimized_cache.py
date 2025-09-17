#!/usr/bin/env python3
"""
Test the optimized cache system
"""

import sys
import os
sys.path.append('projects/fundraising_tracking_app/strava_integration')

from smart_strava_cache_optimized import OptimizedSmartStravaCache
import json

def test_optimized_cache():
    """Test the optimized cache system"""
    
    print("🧪 TESTING OPTIMIZED CACHE SYSTEM")
    print("=" * 40)
    
    # Initialize optimized cache
    cache = OptimizedSmartStravaCache()
    
    try:
        # Get 2 activities with optimized data
        print("📡 Fetching 2 activities with optimized data...")
        activities = cache.get_activities_smart(limit=2)
        
        if not activities:
            print("❌ No activities returned")
            return
        
        print(f"✅ Retrieved {len(activities)} activities")
        
        # Analyze the data
        for i, activity in enumerate(activities):
            print(f"\n📊 ACTIVITY {i+1}: {activity.get('name', 'Unknown')}")
            print(f"  ID: {activity.get('id')}")
            print(f"  Type: {activity.get('type')}")
            print(f"  Distance: {activity.get('distance')}m")
            print(f"  Duration: {activity.get('moving_time')}s")
            print(f"  Description: {activity.get('description', '')[:50]}...")
            print(f"  Comment count: {activity.get('comment_count', 0)}")
            
            # Check map data
            map_data = activity.get('map', {})
            if 'polyline' in map_data:
                print(f"  Polyline: {len(map_data['polyline'])} chars")
            if 'gps_points' in map_data:
                print(f"  GPS points: {len(map_data['gps_points'])} points")
            else:
                print("  GPS points: None (optimized!)")
            
            # Check photos
            photos = activity.get('photos', {})
            if photos:
                print(f"  Photos: {photos.get('count', 0)} found")
            
            # Check music
            music = activity.get('music', {})
            if music:
                detected = music.get('detected', {})
                print(f"  Music: {detected.get('title', 'Unknown')} by {detected.get('artist', 'Unknown')}")
            
            # Check comments
            comments = activity.get('comments', [])
            print(f"  Comments: {len(comments)} found")
        
        # Calculate total size
        total_size = len(json.dumps(activities))
        print(f"\n📈 TOTAL DATA SIZE: {total_size:,} characters")
        
        # Save test data
        test_data = {
            'timestamp': cache._cache_data.get('timestamp'),
            'activities': activities
        }
        
        with open('test_optimized_cache.json', 'w') as f:
            json.dump(test_data, f, indent=2)
        
        print("💾 Saved test data to: test_optimized_cache.json")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_optimized_cache()
