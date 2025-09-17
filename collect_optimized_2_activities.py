#!/usr/bin/env python3
"""
Collect 2 activities with optimized data structure (polyline instead of GPS points)
"""

import sys
import os
sys.path.append('projects/fundraising_tracking_app/strava_integration')

from smart_strava_cache import SmartStravaCache
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

def collect_optimized_activities():
    """Collect 2 activities with optimized data structure"""
    
    print("🚀 Collecting 2 activities with OPTIMIZED data structure...")
    print("📅 Timestamp:", datetime.now().isoformat())
    print()
    
    # Initialize cache
    cache = SmartStravaCache()
    
    try:
        # Get access token
        access_token = cache.token_manager.get_valid_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Get 2 basic activities
        print("📡 Fetching 2 basic activities...")
        with httpx.Client() as client:
            response = client.get('https://www.strava.com/api/v3/athlete/activities?per_page=2', headers=headers)
            if response.status_code != 200:
                print(f"❌ Failed to get activities: {response.status_code}")
                return
            
            activities = response.json()
            print(f"✅ Retrieved {len(activities)} basic activities")
        
        # Process each activity to get optimized data
        optimized_activities = []
        
        for i, activity in enumerate(activities):
            print(f"\n🔧 Processing activity {i+1}: {activity.get('name', 'Unknown')}")
            
            # Create optimized activity with only essential fields
            optimized_activity = {
                'id': activity.get('id'),
                'name': activity.get('name'),
                'type': activity.get('type'),
                'distance': activity.get('distance'),
                'moving_time': activity.get('moving_time'),
                'start_date_local': activity.get('start_date_local'),
                'description': activity.get('description', ''),
                'comment_count': activity.get('comment_count', 0)
            }
            
            # Get complete activity data for description, photos, comments, music
            activity_id = activity['id']
            print(f"  📡 Fetching complete data for {activity_id}...")
            
            try:
                # Get detailed activity data
                with httpx.Client() as client:
                    detail_response = client.get(f'https://www.strava.com/api/v3/activities/{activity_id}', headers=headers)
                    if detail_response.status_code == 200:
                        detail_data = detail_response.json()
                        optimized_activity['description'] = detail_data.get('description', '')
                        
                        # Get map data with polyline (not GPS points)
                        map_data = detail_data.get('map', {})
                        optimized_map = {}
                        if 'polyline' in map_data:
                            optimized_map['polyline'] = map_data['polyline']
                        if 'summary_polyline' in map_data:
                            optimized_map['summary_polyline'] = map_data['summary_polyline']
                        if 'bounds' in map_data:
                            optimized_map['bounds'] = map_data['bounds']
                        
                        optimized_activity['map'] = optimized_map
                        print(f"    ✅ Map data: polyline={len(map_data.get('polyline', ''))} chars")
                
                # Get photos
                with httpx.Client() as client:
                    photos_response = client.get(f'https://www.strava.com/api/v3/activities/{activity_id}/photos?size=5000', headers=headers)
                    if photos_response.status_code == 200:
                        photos_data = photos_response.json()
                        if photos_data:
                            primary_photo = photos_data[0]
                            optimized_activity['photos'] = {
                                'primary': {
                                    'unique_id': primary_photo.get('unique_id'),
                                    'type': primary_photo.get('type'),
                                    'urls': {
                                        '600': primary_photo.get('urls', {}).get('1800', ''),
                                        '1000': primary_photo.get('urls', {}).get('5000', '')
                                    },
                                    'status': primary_photo.get('status'),
                                    'placeholder_image': primary_photo.get('placeholder_image', False)
                                },
                                'count': len(photos_data)
                            }
                            print(f"    ✅ Photos: {len(photos_data)} found")
                
                # Get comments
                with httpx.Client() as client:
                    comments_response = client.get(f'https://www.strava.com/api/v3/activities/{activity_id}/comments', headers=headers)
                    if comments_response.status_code == 200:
                        comments_data = comments_response.json()
                        optimized_activity['comments'] = comments_data
                        print(f"    ✅ Comments: {len(comments_data)} found")
                
                # Get music data
                description = optimized_activity.get('description', '')
                if description:
                    try:
                        music_data = cache.music_integration.get_music_widget(description)
                        if music_data:
                            optimized_activity['music'] = music_data
                            detected = music_data.get('detected', {})
                            print(f"    ✅ Music: {detected.get('title', 'Unknown')} by {detected.get('artist', 'Unknown')}")
                        else:
                            optimized_activity['music'] = {}
                    except Exception as e:
                        print(f"    ⚠️ Music detection failed: {e}")
                        optimized_activity['music'] = {}
                
            except Exception as e:
                print(f"    ❌ Error processing activity {activity_id}: {e}")
            
            optimized_activities.append(optimized_activity)
        
        # Create optimized cache
        optimized_cache = {
            'timestamp': datetime.now().isoformat(),
            'activities': optimized_activities
        }
        
        # Calculate size
        total_size = len(json.dumps(optimized_cache))
        print(f"\n📈 OPTIMIZED CACHE SIZE: {total_size:,} characters")
        
        # Save to test cache
        test_cache_path = 'projects/fundraising_tracking_app/strava_integration/test_strava_cache.json'
        with open(test_cache_path, 'w') as f:
            json.dump(optimized_cache, f, indent=2)
        
        print(f"💾 Saved optimized cache to: {test_cache_path}")
        
        # Verify the data
        print(f"\n✅ VERIFICATION:")
        for i, activity in enumerate(optimized_activities):
            map_data = activity.get('map', {})
            has_polyline = 'polyline' in map_data
            has_gps_points = 'gps_points' in map_data
            print(f"  Activity {i+1}: {activity.get('name')}")
            print(f"    Polyline: {'✅' if has_polyline else '❌'}")
            print(f"    GPS points: {'❌' if not has_gps_points else '⚠️'}")
            print(f"    Description: {'✅' if activity.get('description') else '❌'}")
            print(f"    Photos: {'✅' if activity.get('photos') else '❌'}")
            print(f"    Comments: {'✅' if activity.get('comments') else '❌'}")
            print(f"    Music: {'✅' if activity.get('music') else '❌'}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    from datetime import datetime
    collect_optimized_activities()
