#!/usr/bin/env python3
"""
Test what Strava API actually returns for map data
"""

import os
import sys
import json
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_strava_map_data():
    """Test what Strava API returns for map data"""
    
    # Get access token
    access_token = os.getenv('STRAVA_ACCESS_TOKEN')
    if not access_token:
        print("❌ No STRAVA_ACCESS_TOKEN found in .env")
        return
    
    headers = {'Authorization': f'Bearer {access_token}'}
    
    # Get a recent activity
    with httpx.Client() as client:
        # First get activities list
        response = client.get('https://www.strava.com/api/v3/athlete/activities?per_page=1', headers=headers)
        if response.status_code != 200:
            print(f"❌ Failed to get activities: {response.status_code}")
            return
        
        activities = response.json()
        if not activities:
            print("❌ No activities found")
            return
        
        activity_id = activities[0]['id']
        print(f"🔍 Testing activity ID: {activity_id}")
        
        # Get detailed activity data
        response = client.get(f'https://www.strava.com/api/v3/activities/{activity_id}', headers=headers)
        if response.status_code != 200:
            print(f"❌ Failed to get activity details: {response.status_code}")
            return
        
        activity = response.json()
        
        print("\n📊 RAW STRAVA API MAP DATA:")
        print("=" * 40)
        
        map_data = activity.get('map', {})
        for key, value in map_data.items():
            if isinstance(value, str):
                if len(value) > 100:
                    print(f"  {key}: {value[:100]}... ({len(value)} chars)")
                else:
                    print(f"  {key}: {value}")
            elif isinstance(value, dict):
                print(f"  {key}: {value}")
            elif isinstance(value, list):
                print(f"  {key}: list with {len(value)} items")
            else:
                print(f"  {key}: {value} ({type(value).__name__})")
        
        # Check if we have polyline data
        if 'polyline' in map_data:
            polyline = map_data['polyline']
            print(f"\n✅ POLYLINE FOUND: {len(polyline)} characters")
            print(f"   Preview: {polyline[:50]}...")
        else:
            print("\n❌ NO POLYLINE DATA FOUND")
        
        # Check summary polyline
        if 'summary_polyline' in map_data:
            summary_polyline = map_data['summary_polyline']
            print(f"\n✅ SUMMARY POLYLINE FOUND: {len(summary_polyline)} characters")
            print(f"   Preview: {summary_polyline[:50]}...")
        else:
            print("\n❌ NO SUMMARY POLYLINE DATA FOUND")

if __name__ == "__main__":
    test_strava_map_data()
