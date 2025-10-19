#!/usr/bin/env python3
"""
Async Processing Module
Handles heavy operations concurrently to improve API performance
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class AsyncProcessor:
    """
    Handles async processing of heavy operations
    Uses thread pools for CPU-bound tasks and asyncio for I/O-bound tasks
    """
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        logger.info(f"AsyncProcessor initialized with {max_workers} workers")
    
    async def process_activities_parallel(self, activities: List[Dict[str, Any]], 
                                        operations: List[str] = None) -> List[Dict[str, Any]]:
        """
        Process multiple activities in parallel
        
        Args:
            activities: List of activity dictionaries
            operations: List of operations to perform ['photo_processing', 'formatting'] (music_detection is now done during batch processing)
        
        Returns:
            List of processed activities
        """
        if not activities:
            return []
        
        if operations is None:
            operations = ['photo_processing', 'formatting']
        
        # Create tasks for parallel processing
        tasks = []
        for activity in activities:
            task = self._process_single_activity(activity, operations)
            tasks.append(task)
        
        # Process all activities concurrently
        try:
            processed_activities = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out any exceptions and log them
            valid_activities = []
            for i, result in enumerate(processed_activities):
                if isinstance(result, Exception):
                    logger.warning(f"Failed to process activity {i}: {result}")
                else:
                    valid_activities.append(result)
            
            logger.debug(f"Processed {len(valid_activities)}/{len(activities)} activities successfully")
            return valid_activities
            
        except Exception as e:
            logger.error(f"Error in parallel activity processing: {e}")
            # Fallback to sequential processing
            return await self._process_activities_sequential(activities, operations)
    
    async def _process_single_activity(self, activity: Dict[str, Any], 
                                     operations: List[str]) -> Dict[str, Any]:
        """Process a single activity with specified operations"""
        processed_activity = activity.copy()
        
        # Ensure comments are preserved (don't let them get lost in processing)
        original_comments = activity.get('comments', [])
        
        # Run CPU-bound operations in thread pool
        loop = asyncio.get_event_loop()
        
        if 'music_detection' in operations:
            description = activity.get('description', '')
            if description:
                music_data = await loop.run_in_executor(
                    self.executor, 
                    self._detect_music_sync, 
                    description
                )
                processed_activity['music'] = music_data
        
        if 'photo_processing' in operations:
            photos = activity.get('photos', {})
            if photos:
                processed_photos = await loop.run_in_executor(
                    self.executor,
                    self._process_photos_sync,
                    photos
                )
                processed_activity['photos'] = processed_photos
        
        if 'formatting' in operations:
            formatted_activity = await loop.run_in_executor(
                self.executor,
                self._format_activity_sync,
                processed_activity
            )
            processed_activity = formatted_activity
        
        # Ensure comments are still present after all processing
        if 'comments' not in processed_activity or not processed_activity['comments']:
            processed_activity['comments'] = original_comments
        
        return processed_activity
    
    async def _process_activities_sequential(self, activities: List[Dict[str, Any]], 
                                           operations: List[str]) -> List[Dict[str, Any]]:
        """Fallback sequential processing"""
        processed_activities = []
        for activity in activities:
            try:
                processed = await self._process_single_activity(activity, operations)
                processed_activities.append(processed)
            except Exception as e:
                logger.warning(f"Failed to process activity sequentially: {e}")
                processed_activities.append(activity)  # Return original if processing fails
        
        return processed_activities
    
    def _detect_music_sync(self, description: str) -> Dict[str, Any]:
        """Synchronous music detection (CPU-bound) - returns original format"""
        if not description:
            return {}
        
        # Music detection patterns - optimized for performance
        album_pattern = r"Album:\s*([^,\n]+?)\s+by\s+([^,\n]+)"
        russell_radio_pattern = r"Russell Radio:\s*([^,\n]+?)\s+by\s+([^,\n]+)"
        track_pattern = r"Track:\s*([^,\n]+?)\s+by\s+([^,\n]+)"
        playlist_pattern = r"Playlist:\s*([^,\n]+)"
        
        music_data = {}
        detected = {}
        
        # Check for album
        album_match = re.search(album_pattern, description, re.IGNORECASE)
        if album_match:
            detected = {
                "type": "album",
                "title": album_match.group(1).strip(),
                "artist": album_match.group(2).strip(),
                "source": "description"
            }
            music_data["album"] = {
                "name": album_match.group(1).strip(),
                "artist": album_match.group(2).strip()
            }
        
        # Check for Russell Radio
        russell_match = re.search(russell_radio_pattern, description, re.IGNORECASE)
        if russell_match:
            detected = {
                "type": "track",
                "title": russell_match.group(1).strip(),
                "artist": russell_match.group(2).strip(),
                "source": "russell_radio"
            }
            music_data["track"] = {
                "name": russell_match.group(1).strip(),
                "artist": russell_match.group(2).strip()
            }
        
        # Check for track
        track_match = re.search(track_pattern, description, re.IGNORECASE)
        if track_match:
            detected = {
                "type": "track",
                "title": track_match.group(1).strip(),
                "artist": track_match.group(2).strip() if track_match.group(2) else None,
                "source": "description"
            }
            music_data["track"] = {
                "name": track_match.group(1).strip(),
                "artist": track_match.group(2).strip() if track_match.group(2) else None
            }
        
        # Check for playlist
        playlist_match = re.search(playlist_pattern, description, re.IGNORECASE)
        if playlist_match:
            detected = {
                "type": "playlist",
                "title": playlist_match.group(1).strip(),
                "artist": "Various Artists",
                "source": "description"
            }
            music_data["playlist"] = {
                "name": playlist_match.group(1).strip()
            }
        
        # Add detected field for frontend compatibility
        if detected:
            music_data["detected"] = detected
            
            # Generate Deezer widget HTML
            music_data["widget_html"] = self._generate_deezer_widget(detected)
        
        return music_data
    
    def _generate_deezer_widget(self, detected: Dict[str, Any]) -> str:
        """Generate Deezer widget HTML for the detected music"""
        try:
            # Search for the track/album on Deezer
            deezer_id, id_type = self._search_deezer_for_id(
                detected["title"], 
                detected["artist"], 
                detected["type"]
            )
            
            if deezer_id and id_type:
                # Generate Deezer widget HTML
                if id_type == "track":
                    return f'<iframe scrolling="no" frameborder="0" allowTransparency="true" src="https://widget.deezer.com/widget/dark/{id_type}/{deezer_id}" width="100%" height="200"></iframe>'
                elif id_type == "album":
                    return f'<iframe scrolling="no" frameborder="0" allowTransparency="true" src="https://widget.deezer.com/widget/dark/{id_type}/{deezer_id}" width="100%" height="300"></iframe>'
            
            # Fallback: return a simple text representation
            return f'<div class="music-fallback"><p><strong>{detected["title"]}</strong> by {detected["artist"]}</p></div>'
            
        except Exception as e:
            logger.warning(f"Failed to generate Deezer widget: {e}")
            return f'<div class="music-fallback"><p><strong>{detected["title"]}</strong> by {detected["artist"]}</p></div>'
    
    def _search_deezer_for_id(self, title: str, artist: str, music_type: str) -> tuple[str, str]:
        """
        Search Deezer API for specific album/track ID with sophisticated matching
        Returns: (id_type, deezer_id) or (None, None) if not found
        """
        try:
            import requests
            
            # Clean and prepare search query
            clean_title = title.strip().replace('"', '').replace("'", "")
            clean_artist = artist.strip().replace('"', '').replace("'", "")
            
            # Try multiple search strategies with more flexible terms
            search_queries = [
                f"{clean_title} {clean_artist}",      # Simple concatenation (most effective)
                f"{clean_artist} {clean_title}",      # Artist first
                f'"{clean_title}" "{clean_artist}"',  # Exact match with quotes
                clean_title,                          # Title only
                clean_artist                          # Artist only
            ]
            
            # Prioritize the correct search type, but try both for better coverage
            search_endpoints = []
            if music_type == "album":
                # For albums, try album search first, then track search to find the album
                search_endpoints = [
                    ("https://api.deezer.com/search/album", "album"),
                    ("https://api.deezer.com/search/track", "album_from_track")  # Extract album from track
                ]
            elif music_type == "track":
                search_endpoints = [
                    ("https://api.deezer.com/search/track", "track"),
                    ("https://api.deezer.com/search/album", "track")  # Fallback to album search
                ]
            else:
                return None, None
            
            # Try each search query with each endpoint
            for search_query in search_queries:
                for search_endpoint, endpoint_type in search_endpoints:
                    try:
                        encoded_query = search_query.replace(" ", "%20")
                        search_url = f"{search_endpoint}?q={encoded_query}&limit=10"
                        
                        logger.debug(f"🎵 Searching Deezer for: {search_query} ({endpoint_type}) (URL: {search_url})")
                        
                        # Make request to Deezer API
                        response = requests.get(search_url, timeout=10)
                        if response.status_code == 200:
                            data = response.json()
                            
                            if data.get("data") and len(data["data"]) > 0:
                                # Look for exact matches first
                                for result in data["data"]:
                                    result_title = result.get("title", "").lower()
                                    result_artist = result.get("artist", {}).get("name", "").lower()
                                    
                                    # Check for exact match
                                    if (clean_title.lower() in result_title and clean_artist.lower() in result_artist) or \
                                       (clean_artist.lower() in result_title and clean_title.lower() in result_artist):
                                        
                                        # If we found a track but need an album, get the album ID
                                        if endpoint_type == "album_from_track" and music_type == "album":
                                            album_id = result.get("album", {}).get("id")
                                            if album_id:
                                                logger.info(f"🎵 Found exact Deezer match: {result_title} by {result_artist} (track) - using album ID: {album_id}")
                                                return album_id, "album"
                                            else:
                                                logger.warning(f"🎵 Found track match but no album ID available")
                                                continue
                                        else:
                                            logger.info(f"🎵 Found exact Deezer match: {result_title} by {result_artist} ({endpoint_type}) (ID: {result['id']})")
                                            return result["id"], endpoint_type
                                
                                # If no exact match found, try partial matches
                                for result in data["data"]:
                                    result_title = result.get("title", "").lower()
                                    result_artist = result.get("artist", {}).get("name", "").lower()
                                    
                                    # Check for partial match (at least 80% of words match)
                                    title_words = set(clean_title.lower().split())
                                    artist_words = set(clean_artist.lower().split())
                                    result_title_words = set(result_title.split())
                                    result_artist_words = set(result_artist.split())
                                    
                                    title_match_ratio = len(title_words.intersection(result_title_words)) / len(title_words) if title_words else 0
                                    artist_match_ratio = len(artist_words.intersection(result_artist_words)) / len(artist_words) if artist_words else 0
                                    
                                    if title_match_ratio >= 0.8 and artist_match_ratio >= 0.8:
                                        # If we found a track but need an album, get the album ID
                                        if endpoint_type == "album_from_track" and music_type == "album":
                                            album_id = result.get("album", {}).get("id")
                                            if album_id:
                                                logger.info(f"🎵 Found partial Deezer match: {result_title} by {result_artist} (track) - using album ID: {album_id}")
                                                return album_id, "album"
                                            else:
                                                logger.warning(f"🎵 Found track match but no album ID available")
                                                continue
                                        else:
                                            logger.info(f"🎵 Found partial Deezer match: {result_title} by {result_artist} ({endpoint_type}) (ID: {result['id']})")
                                            return result["id"], endpoint_type
                                
                                # If still no match, return the first result as fallback
                                result = data["data"][0]
                                
                                # If we found a track but need an album, get the album ID
                                if endpoint_type == "album_from_track" and music_type == "album":
                                    album_id = result.get("album", {}).get("id")
                                    if album_id:
                                        logger.warning(f"🎵 No exact match found, using first result album: {result.get('title')} by {result.get('artist', {}).get('name')} (track) - using album ID: {album_id}")
                                        return album_id, "album"
                                    else:
                                        logger.warning(f"🎵 Found track but no album ID available, skipping")
                                        continue
                                else:
                                    logger.warning(f"🎵 No exact match found, using first result: {result.get('title')} by {result.get('artist', {}).get('name')} ({endpoint_type}) (ID: {result['id']})")
                                    return result["id"], endpoint_type
                    
                    except Exception as e:
                        logger.debug(f"🎵 Search query failed: {search_query} ({endpoint_type}) - {e}")
                        continue
            
            logger.warning(f"🎵 No Deezer results found for: {title} by {artist}")
            return None, None
            
        except Exception as e:
            logger.warning(f"Failed to search Deezer API: {e}")
            return None, None
    
    def _process_photos_sync(self, photos: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous photo processing (CPU-bound)"""
        processed_photos = photos.copy()
        
        # Add photo metadata and optimize URLs
        if 'primary' in photos and photos['primary']:
            primary = photos['primary']
            if 'url' in primary:
                # Add optimized photo URL (could add image resizing service URL here)
                processed_photos['primary']['optimized_url'] = primary['url']
                processed_photos['primary']['has_photo'] = True
            else:
                processed_photos['primary']['has_photo'] = False
        
        return processed_photos
    
    def _format_activity_sync(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous activity formatting (CPU-bound)"""
        formatted = activity.copy()
        
        # Format distance
        if 'distance' in activity:
            distance = activity['distance']
            if distance >= 1000:
                formatted['distance_formatted'] = f"{distance/1000:.1f} km"
            else:
                formatted['distance_formatted'] = f"{distance:.0f} m"
        
        # Format duration
        if 'moving_time' in activity:
            seconds = activity['moving_time']
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds = seconds % 60
            
            if hours > 0:
                formatted['formatted_duration'] = f"{hours}h {minutes}m {seconds}s"
                formatted['duration_formatted'] = f"{hours}h {minutes}m {seconds}s"  # Keep both for compatibility
            elif minutes > 0:
                formatted['formatted_duration'] = f"{minutes}m {seconds}s"
                formatted['duration_formatted'] = f"{minutes}m {seconds}s"  # Keep both for compatibility
            else:
                formatted['formatted_duration'] = f"{seconds}s"
                formatted['duration_formatted'] = f"{seconds}s"  # Keep both for compatibility
        
        # Format pace (for runs)
        if activity.get('type') == 'Run' and 'distance' in activity and 'moving_time' in activity:
            distance_km = activity['distance'] / 1000
            time_minutes = activity['moving_time'] / 60
            if distance_km > 0 and time_minutes > 0:
                pace_per_km = time_minutes / distance_km
                pace_minutes = int(pace_per_km)
                pace_seconds = int((pace_per_km - pace_minutes) * 60)
                formatted['pace_per_km'] = f"{pace_minutes}:{pace_seconds:02d}/km"
        
        # Format date properly (restore original formatting)
        if 'start_date_local' in activity:
            formatted['date_formatted'] = self._format_activity_date(activity['start_date_local'])
        
        return formatted
    
    def _format_activity_date(self, start_date_local: str) -> str:
        """Format activity date in the original format: '27th of September 2025 at 9:05'"""
        try:
            # Parse the ISO date string
            dt = datetime.fromisoformat(start_date_local.replace('Z', '+00:00'))
            
            # Extract components
            day = dt.day
            month_name = dt.strftime('%B')
            year = dt.year
            time_formatted = dt.strftime('%H:%M')
            
            # Add ordinal suffix (1st, 2nd, 3rd, 4th, etc.)
            if 10 <= day % 100 <= 20:
                suffix = 'th'
            else:
                suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
            
            return f"{day}{suffix} of {month_name} {year} at {time_formatted}"
        except Exception:
            # Fallback to original format if parsing fails
            return start_date_local
    
    async def process_donations_parallel(self, donations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process multiple donations in parallel
        
        Args:
            donations: List of donation dictionaries
        
        Returns:
            List of processed donations
        """
        if not donations:
            return []
        
        # Create tasks for parallel processing
        tasks = []
        for donation in donations:
            task = self._process_single_donation(donation)
            tasks.append(task)
        
        # Process all donations concurrently
        try:
            processed_donations = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out any exceptions and log them
            valid_donations = []
            for i, result in enumerate(processed_donations):
                if isinstance(result, Exception):
                    logger.warning(f"Failed to process donation {i}: {result}")
                else:
                    valid_donations.append(result)
            
            logger.debug(f"Processed {len(valid_donations)}/{len(donations)} donations successfully")
            return valid_donations
            
        except Exception as e:
            logger.error(f"Error in parallel donation processing: {e}")
            # Fallback to sequential processing
            return await self._process_donations_sequential(donations)
    
    async def _process_single_donation(self, donation: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single donation"""
        processed_donation = donation.copy()
        
        # Run CPU-bound operations in thread pool
        loop = asyncio.get_event_loop()
        
        formatted_donation = await loop.run_in_executor(
            self.executor,
            self._format_donation_sync,
            processed_donation
        )
        
        return formatted_donation
    
    async def _process_donations_sequential(self, donations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fallback sequential processing for donations"""
        processed_donations = []
        for donation in donations:
            try:
                processed = await self._process_single_donation(donation)
                processed_donations.append(processed)
            except Exception as e:
                logger.warning(f"Failed to process donation sequentially: {e}")
                processed_donations.append(donation)  # Return original if processing fails
        
        return processed_donations
    
    def _format_donation_sync(self, donation: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous donation formatting (CPU-bound)"""
        formatted = donation.copy()
        
        # Format amount
        if 'amount' in donation:
            amount = donation['amount']
            formatted['amount_formatted'] = f"£{amount:.2f}"
        
        # Format date
        if 'date' in donation:
            try:
                # Parse and reformat date
                date_str = donation['date']
                if isinstance(date_str, str):
                    # Try to parse common date formats
                    for fmt in ['%d %b %Y', '%Y-%m-%d', '%d/%m/%Y']:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            formatted['date_formatted'] = parsed_date.strftime('%d %b %Y')
                            break
                        except ValueError:
                            continue
                    else:
                        formatted['date_formatted'] = date_str
            except Exception:
                formatted['date_formatted'] = donation.get('date', '')
        
        # Add anonymization flag for privacy
        if 'donor_name' in donation:
            donor_name = donation['donor_name']
            if donor_name and len(donor_name.strip()) > 0:
                # Keep first name, anonymize last name
                name_parts = donor_name.strip().split()
                if len(name_parts) > 1:
                    formatted['donor_name_anonymized'] = f"{name_parts[0]} {name_parts[1][0]}."
                else:
                    formatted['donor_name_anonymized'] = donor_name
            else:
                formatted['donor_name_anonymized'] = "Anonymous"
        
        return formatted
    
    def shutdown(self):
        """Shutdown the thread pool executor"""
        self.executor.shutdown(wait=True)
        logger.info("AsyncProcessor shutdown complete")

# Global instance
async_processor = AsyncProcessor()
