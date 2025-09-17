#!/usr/bin/env python3
"""
Analyze the test cache to identify redundant data that can be removed.
"""

import json
import sys
from collections import defaultdict

def analyze_cache_data():
    """Analyze what data we're storing vs what we actually need."""
    
    # Load the test cache
    with open('projects/fundraising_tracking_app/strava_integration/test_strava_cache.json', 'r') as f:
        cache_data = json.load(f)
    
    print("🔍 ANALYZING CACHE DATA USAGE")
    print("=" * 50)
    
    # Fields actually used by frontend (from our analysis)
    frontend_fields = {
        'id': 'Activity ID',
        'name': 'Activity name/title',
        'type': 'Activity type (Run, Ride, etc.)',
        'distance': 'Distance in meters (converted to km)',
        'moving_time': 'Duration in seconds (converted to minutes)',
        'start_date_local': 'Start date (formatted)',
        'description': 'Activity description',
        'comment_count': 'Number of comments',
        'photos': 'Photo data for display',
        'music': 'Music detection and Deezer widgets',
        'comments': 'Actual comment text',
        'map': 'GPS data for route display'
    }
    
    # Get first activity to analyze structure
    if cache_data.get('activities'):
        activity = cache_data['activities'][0]
        
        print(f"📊 ACTIVITY: {activity.get('name', 'Unknown')}")
        print(f"🆔 ID: {activity.get('id', 'Unknown')}")
        print()
        
        # Analyze all fields in the activity
        all_fields = set(activity.keys())
        frontend_field_set = set(frontend_fields.keys())
        
        print("✅ FIELDS USED BY FRONTEND:")
        used_fields = all_fields.intersection(frontend_field_set)
        for field in sorted(used_fields):
            print(f"  ✓ {field}: {frontend_fields[field]}")
        
        print()
        print("❌ REDUNDANT FIELDS (NOT USED BY FRONTEND):")
        redundant_fields = all_fields - frontend_field_set
        for field in sorted(redundant_fields):
            value = activity.get(field)
            if isinstance(value, (dict, list)):
                print(f"  ✗ {field}: {type(value).__name__} ({len(value) if hasattr(value, '__len__') else 'N/A'} items)")
            else:
                print(f"  ✗ {field}: {value}")
        
        print()
        print("📈 DATA SIZE ANALYSIS:")
        
        # Calculate approximate sizes
        total_size = len(json.dumps(activity))
        used_size = len(json.dumps({k: v for k, v in activity.items() if k in frontend_field_set}))
        redundant_size = total_size - used_size
        
        print(f"  Total activity size: ~{total_size:,} characters")
        print(f"  Used fields size: ~{used_size:,} characters")
        print(f"  Redundant fields size: ~{redundant_size:,} characters")
        print(f"  Redundancy: {(redundant_size/total_size)*100:.1f}%")
        
        # Analyze specific large fields
        print()
        print("🔍 LARGE FIELD ANALYSIS:")
        large_fields = []
        for field, value in activity.items():
            if isinstance(value, (dict, list)):
                size = len(json.dumps(value))
                if size > 1000:  # Fields larger than 1KB
                    large_fields.append((field, size, type(value).__name__))
        
        for field, size, field_type in sorted(large_fields, key=lambda x: x[1], reverse=True):
            print(f"  📦 {field}: {size:,} chars ({field_type})")
        
        # Check if we have GPS points vs polyline
        print()
        print("🗺️ MAP DATA ANALYSIS:")
        if 'map' in activity:
            map_data = activity['map']
            if 'gps_points' in map_data:
                gps_count = len(map_data['gps_points'])
                print(f"  GPS Points: {gps_count:,} points")
                if gps_count > 0:
                    gps_size = len(json.dumps(map_data['gps_points']))
                    print(f"  GPS Data Size: {gps_size:,} characters")
            
            if 'polyline' in map_data:
                polyline_size = len(map_data['polyline'])
                print(f"  Polyline: {polyline_size} characters")
                print(f"  Polyline Size: {polyline_size:,} characters")
        
        # Check photos data
        print()
        print("📸 PHOTOS DATA ANALYSIS:")
        if 'photos' in activity:
            photos = activity['photos']
            if isinstance(photos, dict):
                for key, value in photos.items():
                    if isinstance(value, dict):
                        print(f"  {key}: {len(value)} fields")
                        for subkey, subvalue in value.items():
                            if isinstance(subvalue, str) and len(subvalue) > 100:
                                print(f"    {subkey}: {len(subvalue)} chars")
                    else:
                        print(f"  {key}: {type(value).__name__}")

if __name__ == "__main__":
    analyze_cache_data()
