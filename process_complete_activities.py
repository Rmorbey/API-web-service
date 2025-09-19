#!/usr/bin/env python3
"""
Process 20 activities with complete data (descriptions, comments, photos, music)
This will make 60 API calls (3 per activity) to stay within rate limits
"""

import json
import sys
import os
import time
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from projects.fundraising_tracking_app.strava_integration.smart_strava_cache import SmartStravaCache

def process_complete_activities(batch_size=20, start_index=0):
    """Process activities with complete data"""
    print(f"🔄 Processing {batch_size} activities with complete data...")
    print(f"📊 This will make {batch_size * 3} API calls")
    print(f"⏰ Started at: {datetime.now().strftime('%H:%M:%S')}")
    
    # Load current cache
    cache_file = "projects/fundraising_tracking_app/strava_integration/strava_cache.json"
    
    with open(cache_file, 'r') as f:
        cache_data = json.load(f)
    
    activities = cache_data.get("activities", [])
    print(f"📁 Cache has {len(activities)} activities")
    
    # Process the specified batch
    end_index = min(start_index + batch_size, len(activities))
    batch_activities = activities[start_index:end_index]
    
    print(f"🎯 Processing activities {start_index+1} to {end_index}")
    
    # Create cache instance for API calls
    cache = SmartStravaCache()
    
    processed_activities = []
    api_call_count = 0
    
    for i, activity in enumerate(batch_activities):
        activity_id = activity.get("id")
        activity_name = activity.get("name", "Unknown")
        
        print(f"\n📝 Processing {i+1}/{len(batch_activities)}: {activity_name} (ID: {activity_id})")
        
        try:
            # Fetch complete activity data (3 API calls per activity)
            complete_activity = cache._fetch_complete_activity_data(activity_id)
            api_call_count += 3
            
            # Clean up the activity data - keep only essential fields
            cleaned_activity = {
                "id": complete_activity.get("id"),
                "name": complete_activity.get("name", ""),
                "type": complete_activity.get("type", ""),
                "distance": complete_activity.get("distance", 0),
                "moving_time": complete_activity.get("moving_time", 0),
                "elapsed_time": complete_activity.get("elapsed_time", 0),
                "total_elevation_gain": complete_activity.get("total_elevation_gain", 0),
                "start_date": complete_activity.get("start_date", ""),
                "start_date_local": complete_activity.get("start_date_local", ""),
                "timezone": complete_activity.get("timezone", ""),
                "description": complete_activity.get("description", ""),
                "start_latlng": complete_activity.get("start_latlng"),
                "end_latlng": complete_activity.get("end_latlng"),
                "map": complete_activity.get("map", {}),
                "photos": complete_activity.get("photos", {}),
                "comments": complete_activity.get("comments", []),
                "music": complete_activity.get("music", {})
            }
            
            processed_activities.append(cleaned_activity)
            print(f"✅ Processed {activity_name} - {api_call_count} API calls made")
            
            # Small delay to be respectful to the API
            time.sleep(0.5)
            
        except Exception as e:
            print(f"❌ Error processing {activity_name}: {e}")
            # Keep the original activity if processing fails
            processed_activities.append(activity)
    
    # Update the cache with processed activities
    activities[start_index:end_index] = processed_activities
    
    # Save updated cache
    cache_data["activities"] = activities
    cache_data["timestamp"] = datetime.now().isoformat()
    cache_data["last_processed"] = {
        "batch_size": batch_size,
        "start_index": start_index,
        "end_index": end_index,
        "api_calls_made": api_call_count,
        "processed_at": datetime.now().isoformat()
    }
    
    with open(cache_file, 'w') as f:
        json.dump(cache_data, f, indent=2)
    
    print(f"\n🎉 BATCH COMPLETE!")
    print(f"✅ Processed {len(processed_activities)} activities")
    print(f"📊 Made {api_call_count} API calls")
    print(f"⏰ Completed at: {datetime.now().strftime('%H:%M:%S')}")
    print(f"📁 Cache updated with complete data")
    
    return processed_activities

if __name__ == "__main__":
    # Process first 20 activities
    process_complete_activities(batch_size=20, start_index=0)

