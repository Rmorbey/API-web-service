#!/usr/bin/env python3
"""
GPX Data Importer
Reads activity data from Google Sheets (GPX imports) and processes it into activity format
"""

import os
import logging
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from datetime import datetime
import polyline

logger = logging.getLogger(__name__)

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False
    logger.warning("Google Sheets API not available - install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")

try:
    import gpxpy
    GPXPY_AVAILABLE = True
except ImportError:
    GPXPY_AVAILABLE = False
    logger.warning("gpxpy not available - install with: pip install gpxpy")


class GPXImporter:
    """Import and process GPX files from Google Sheets"""
    
    def __init__(self):
        self.sheets_service = None
        self.drive_service = None
        self.credentials = None
        self._setup_google_sheets()
    
    def _setup_google_sheets(self):
        """Setup Google Sheets API connection"""
        if not GOOGLE_SHEETS_AVAILABLE:
            logger.warning("Google Sheets API not available")
            return
        
        try:
            creds = None
            token_file = os.getenv("GOOGLE_SHEETS_TOKEN_FILE", "token.json")
            creds_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "credentials.json")
            
            # Load existing token
            if os.path.exists(token_file):
                creds = Credentials.from_authorized_user_file(token_file)
            
            # If no valid credentials, authorize
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(creds_file):
                        logger.error(f"Google Sheets credentials file not found: {creds_file}")
                        return
                    flow = InstalledAppFlow.from_client_secrets_file(
                        creds_file,
                        [
                            'https://www.googleapis.com/auth/spreadsheets',
                            'https://www.googleapis.com/auth/drive.readonly'
                        ]
                    )
                    creds = flow.run_local_server(port=0)
                
                # Save token for future use
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())
            
            self.credentials = creds
            self.sheets_service = build('sheets', 'v4', credentials=creds)
            self.drive_service = build('drive', 'v3', credentials=creds)
            logger.info("✅ Google Sheets and Drive API connected")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup Google Sheets: {e}")
            self.sheets_service = None
    
    def read_activities_from_sheets(self, spreadsheet_id: str, range_name: str = "Activities!A:Z") -> List[Dict[str, Any]]:
        """Read activity data from Google Sheets"""
        if not self.sheets_service:
            logger.error("Google Sheets service not available")
            return []
        
        try:
            # Read data from sheet
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                logger.warning("No data found in Google Sheets")
                return []
            
            # First row is headers
            headers = values[0]
            activities = []
            
            # Minimum required fields for an activity (name, type, gpx_drive_id)
            min_required_fields = 3
            
            # Process each row
            for row in values[1:]:
                # Skip completely empty rows
                if not row:
                    continue
                
                # Only require minimum fields (not all headers)
                if len(row) < min_required_fields:
                    logger.debug(f"Skipping row with insufficient fields: {row}")
                    continue
                
                activity = {}
                for i, header in enumerate(headers):
                    if i < len(row):
                        activity[header.lower().replace(' ', '_')] = row[i]
                    else:
                        # Fill missing columns with empty string
                        activity[header.lower().replace(' ', '_')] = ''
                
                activities.append(activity)
            
            logger.info(f"📊 Read {len(activities)} activities from Google Sheets")
            return activities
            
        except Exception as e:
            logger.error(f"❌ Failed to read from Google Sheets: {e}")
            return []
    
    def parse_gpx_file(self, gpx_content: str) -> Dict[str, Any]:
        """Parse GPX file content and extract activity data"""
        if not GPXPY_AVAILABLE:
            logger.error("gpxpy not available for GPX parsing")
            return {}
        
        try:
            gpx = gpxpy.parse(gpx_content)
            
            if not gpx.tracks:
                logger.warning("No tracks found in GPX file")
                return {}
            
            # Get the first track (main activity)
            track = gpx.tracks[0]
            
            # Extract all points
            points = []
            total_distance = 0
            total_elevation_gain = 0
            prev_point = None
            
            for segment in track.segments:
                for point in segment.points:
                    points.append({
                        'lat': point.latitude,
                        'lng': point.longitude,
                        'elevation': point.elevation,
                        'time': point.time
                    })
                    
                    # Calculate distance
                    if prev_point:
                        from math import radians, sin, cos, sqrt, atan2
                        lat1, lon1 = radians(prev_point['lat']), radians(prev_point['lng'])
                        lat2, lon2 = radians(point.latitude), radians(point.longitude)
                        
                        dlat = lat2 - lat1
                        dlon = lon2 - lon1
                        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                        c = 2 * atan2(sqrt(a), sqrt(1-a))
                        distance = 6371000 * c  # Earth radius in meters
                        total_distance += distance
                        
                        # Calculate elevation gain
                        if point.elevation and prev_point['elevation']:
                            elevation_diff = point.elevation - prev_point['elevation']
                            if elevation_diff > 0:
                                total_elevation_gain += elevation_diff
                    
                    prev_point = {'lat': point.latitude, 'lng': point.longitude, 'elevation': point.elevation}
            
            # Calculate duration
            start_time = points[0]['time'] if points else None
            end_time = points[-1]['time'] if points else None
            duration = (end_time - start_time).total_seconds() if start_time and end_time else 0
            
            # Create polyline
            if points:
                polyline_points = [(p['lat'], p['lng']) for p in points]
                encoded_polyline = polyline.encode(polyline_points)
            else:
                encoded_polyline = None
            
            # Calculate bounds
            if points:
                lats = [p['lat'] for p in points]
                lngs = [p['lng'] for p in points]
                bounds = {
                    'north': max(lats),
                    'south': min(lats),
                    'east': max(lngs),
                    'west': min(lngs)
                }
            else:
                bounds = None
            
            return {
                'distance': total_distance,
                'duration': int(duration),
                'moving_time': int(duration),
                'elapsed_time': int(duration),
                'total_elevation_gain': total_elevation_gain,
                'polyline': encoded_polyline,
                'bounds': bounds,
                'start_time': start_time.isoformat() if start_time else None,
                'point_count': len(points)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to parse GPX file: {e}")
            return {}
    
    def process_gpx_activity(self, sheet_activity: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single activity from Google Sheets with GPX data"""
        try:
            gpx_content = ''
            
            # Try multiple ways to get GPX data:
            # 1. Direct content in cell (if small enough)
            gpx_content = sheet_activity.get('gpx_content', '')
            
            # 2. Local file path
            if not gpx_content:
                gpx_file_path = sheet_activity.get('gpx_file_path', '') or sheet_activity.get('gpx_file', '')
                if gpx_file_path and os.path.exists(gpx_file_path):
                    try:
                        with open(gpx_file_path, 'r') as f:
                            gpx_content = f.read()
                        logger.info(f"✅ Read GPX from file: {gpx_file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to read GPX file {gpx_file_path}: {e}")
            
            # 3. Google Drive file ID
            if not gpx_content:
                drive_file_id = sheet_activity.get('gpx_drive_id', '') or sheet_activity.get('drive_file_id', '')
                if drive_file_id:
                    gpx_content = self._download_from_google_drive(drive_file_id)
            
            # 4. URL (HTTP/HTTPS)
            if not gpx_content:
                gpx_url = sheet_activity.get('gpx_url', '') or sheet_activity.get('url', '')
                if gpx_url and (gpx_url.startswith('http://') or gpx_url.startswith('https://')):
                    gpx_content = self._download_from_url(gpx_url)
            
            if not gpx_content:
                logger.warning("No GPX content found in activity - need gpx_content, gpx_file_path, gpx_drive_id, or gpx_url")
                return {}
            
            # Parse GPX
            gpx_data = self.parse_gpx_file(gpx_content)
            
            if not gpx_data:
                logger.warning("Failed to parse GPX data")
                return {}
            
            # Process photos (can be URLs or Google Drive links, comma-separated)
            photos = []
            photo_urls_str = sheet_activity.get('photos', '') or sheet_activity.get('photo_urls', '')
            if photo_urls_str:
                # Split comma-separated URLs (handle line breaks too)
                import re
                photo_urls = re.split(r'[,\n]+', photo_urls_str)
                for url in photo_urls:
                    url = url.strip()
                    if not url:
                        continue
                    
                    # If it's a Google Drive link, convert to direct image URL or keep as is
                    # Drive links: https://drive.google.com/file/d/FILE_ID/view
                    # Extract file ID if it's a Drive link
                    drive_match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
                    if drive_match:
                        file_id = drive_match.group(1)
                        # Convert to direct image preview URL
                        url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w1200"
                    
                    photos.append({
                        'urls': {
                            '300': url,
                            '600': url,
                            '1200': url
                        }
                    })
            
            # Build activity object
            activity = {
                'id': int(sheet_activity.get('id', 0)) if sheet_activity.get('id') else None,
                'name': sheet_activity.get('name', 'Activity').replace('_', ' '),
                'type': sheet_activity.get('type', 'Run'),
                'distance': gpx_data.get('distance', 0),
                'moving_time': gpx_data.get('moving_time', 0),
                'elapsed_time': gpx_data.get('elapsed_time', 0),
                'total_elevation_gain': gpx_data.get('total_elevation_gain', 0),
                'start_date': gpx_data.get('start_time') or sheet_activity.get('start_date', datetime.now().isoformat()),
                'start_date_local': gpx_data.get('start_time') or sheet_activity.get('start_date_local', datetime.now().isoformat()),
                'description': sheet_activity.get('description', ''),
                'polyline': gpx_data.get('polyline'),
                'bounds': gpx_data.get('bounds'),
                'photos': photos,
                'comments': [],
                'source': 'gpx_import'
            }
            
            logger.info(f"✅ Processed GPX activity: {activity.get('name')}")
            return activity
            
        except Exception as e:
            logger.error(f"❌ Failed to process GPX activity: {e}")
            return {}
    
    def _download_from_google_drive(self, file_id: str) -> str:
        """Download GPX file from Google Drive by file ID"""
        try:
            if not self.drive_service:
                logger.error("Google Drive service not available")
                return ''
            
            # Use Google Drive API
            try:
                request = self.drive_service.files().get_media(fileId=file_id)
                import io
                from googleapiclient.http import MediaIoBaseDownload
                
                file = io.BytesIO()
                downloader = MediaIoBaseDownload(file, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                
                gpx_content = file.getvalue().decode('utf-8')
                logger.info(f"✅ Downloaded GPX from Google Drive: {file_id}")
                return gpx_content
            except Exception as e:
                logger.warning(f"Could not use Drive API, trying direct download: {e}")
                # Fallback: Direct download URL
                download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
                return self._download_from_url(download_url)
                
        except Exception as e:
            logger.error(f"❌ Failed to download from Google Drive: {e}")
            return ''
    
    def _download_from_url(self, url: str) -> str:
        """Download GPX file from URL (handles redirects)"""
        try:
            import httpx
            # Follow redirects automatically
            response = httpx.get(url, timeout=30, follow_redirects=True)
            response.raise_for_status()
            gpx_content = response.text
            logger.info(f"✅ Downloaded GPX from URL: {url}")
            return gpx_content
        except Exception as e:
            logger.error(f"❌ Failed to download from URL {url}: {e}")
            return ''

