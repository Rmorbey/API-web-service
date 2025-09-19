#!/usr/bin/env python3
"""
Process remaining activities (21-48) to complete the full dataset
"""
import json
import sys
import os
import time
from datetime import datetime

# Add the parent directory to the sys.path to allow importing modules from it
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from projects.fundraising_tracking_app.strava_integration.smart_strava_cache import SmartStravaCache

def process_remaining_activities():
    cache = SmartStravaCache()
    
    print('🔄 Processing remaining activities (21-48) to complete full dataset...')
    print(f'📊 This will make 84 API calls (28 activities × 3 calls each)')
    print(f'⏰ Started at: {datetime.now().strftime("%H:%M:%S")}')
    
    # Load current cache
    with open('projects/fundraising_tracking_app/strava_integration/strava_cache.json', 'r') as f:
        cache_data = json.load(f)
    
    all_activities = cache_data.get("activities", [])
    print(f'📁 Cache has {len(all_activities)} activities')
    
    if len(all_activities) < 48:
        print(f'❌ Not enough activities in cache. Expected 48, found {len(all_activities)}')
        return
    
    # Process activities 21-48 (0-based indices 20-47)
    activities_to_process = all_activities[20:48]
    print(f'🎯 Processing activities 21-48 ({len(activities_to_process)} activities)')
    
    processed_count = 0
    api_calls_made = 0
    
    for i, activity in enumerate(activities_to_process):
        activity_id = activity.get("id")
        activity_name = activity.get("name", "Unknown Activity")
        activity_index = i + 21  # 1-based index for display
        
        print(f'\n📝 Processing {activity_index}/48: {activity_name} (ID: {activity_id})')
        
        try:
            # Fetch complete data for the activity
            complete_data = cache._fetch_complete_activity_data(activity_id)
            api_calls_made += 3  # 3 API calls per activity (details, photos, comments)
            
            # Update the activity in the cache with the complete data
            all_activities[20 + i] = complete_data
            processed_count += 1
            print(f'✅ Processed {activity_name} - {api_calls_made} API calls made')
            
            # Add a small delay to respect rate limits
            time.sleep(0.5)
            
        except Exception as e:
            print(f'❌ Error processing activity {activity_id}: {e}')
    
    # Save updated cache
    with open('projects/fundraising_tracking_app/strava_integration/strava_cache.json', 'w') as f:
        json.dump(cache_data, f, indent=2)
    
    print(f'\n🎉 REMAINING ACTIVITIES COMPLETE!')
    print(f'✅ Processed {processed_count} activities')
    print(f'📊 Made {api_calls_made} API calls')
    print(f'⏰ Completed at: {datetime.now().strftime("%H:%M:%S")}')
    print(f'📁 Cache updated with complete data for all 48 activities')

if __name__ == "__main__":
    process_remaining_activities()

