#!/usr/bin/env python3
"""
Music Integration Module
Handles music detection, Deezer API integration, and widget generation
"""

import re
import requests
from typing import Dict, Any, Optional
from datetime import datetime

class MusicIntegration:
    """
    Unified music integration class that handles:
    - Music detection from text descriptions
    - Deezer API search and data retrieval
    - Widget generation and HTML embedding
    """
    
    def __init__(self):
        self.deezer_base_url = "https://api.deezer.com"
        self.widget_base_url = "https://widget.deezer.com"
        
        # Define regex patterns for different music types
        self.patterns = {
            'russell_radio': r"Russell Radio:\s*(.+?)\s+by\s+([^,\n]+)",
            'playlist': r"Playlist:\s*([^,\n]+)",
            'album': r"Album:\s*(.+?)\s+by\s+([^,\n]+)"
        }
    
    def extract_music_info(self, description: str) -> Optional[Dict[str, Any]]:
        """
        Extract music information from Strava activity description
        Supports patterns:
        - "Russell Radio: [song] by [artist]"
        - "Playlist: [playlist name]"
        - "Album: [album name] by [artist]"
        """
        if not description:
            return None
            
        # Pattern 1: Russell Radio: [song] by [artist]
        match = re.search(self.patterns['russell_radio'], description, re.IGNORECASE)
        if match:
            return {
                "type": "track",
                "title": match.group(1).strip(),
                "artist": match.group(2).strip(),
                "source": "russell_radio"
            }
        
        # Pattern 2: Playlist: [playlist name]
        match = re.search(self.patterns['playlist'], description, re.IGNORECASE)
        if match:
            return {
                "type": "playlist",
                "title": match.group(1).strip(),
                "source": "playlist"
            }
        
        # Pattern 3: Album: [album name] by [artist]
        match = re.search(self.patterns['album'], description, re.IGNORECASE)
        if match:
            return {
                "type": "album",
                "title": match.group(1).strip(),
                "artist": match.group(2).strip(),
                "source": "album"
            }

        return None
    
    def _search_track(self, music_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Search for a track on Deezer"""
        try:
            query = f"track:\"{music_info['title']}\" artist:\"{music_info['artist']}\""
            response = requests.get(f"{self.deezer_base_url}/search", params={"q": query})
            response.raise_for_status()
            
            data = response.json()
            if data.get("data") and len(data["data"]) > 0:
                track = data["data"][0]
                # Get working widget URL
                widget_url = self._get_working_widget_url(track["id"], "track")
                
                return {
                    "id": track["id"],
                    "title": track["title"],
                    "artist": track["artist"]["name"],
                    "album": track["album"]["title"],
                    "preview_url": track.get("preview"),
                    "cover_url": track["album"]["cover_medium"],
                    "widget_url": widget_url
                }
        except Exception as e:
            print(f"Error searching track on Deezer: {e}")
        return None
    
    def _search_album(self, music_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Search for an album on Deezer"""
        try:
            query = f"album:\"{music_info['title']}\" artist:\"{music_info['artist']}\""
            response = requests.get(f"{self.deezer_base_url}/search/album", params={"q": query})
            response.raise_for_status()
            
            data = response.json()
            if data.get("data") and len(data["data"]) > 0:
                album = data["data"][0]
                # Get working widget URL
                widget_url = self._get_working_widget_url(album["id"], "album")
                
                return {
                    "id": album["id"],
                    "title": album["title"],
                    "artist": album["artist"]["name"],
                    "cover_url": album["cover_medium"],
                    "widget_url": widget_url
                }
        except Exception as e:
            print(f"Error searching album on Deezer: {e}")
        return None
    
    def _search_playlist(self, music_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Search for a playlist on Deezer"""
        try:
            query = f"playlist:\"{music_info['title']}\""
            response = requests.get(f"{self.deezer_base_url}/search/playlist", params={"q": query})
            response.raise_for_status()
            
            data = response.json()
            if data.get("data") and len(data["data"]) > 0:
                playlist = data["data"][0]
                # Get working widget URL
                widget_url = self._get_working_widget_url(playlist["id"], "playlist")
                
                return {
                    "id": playlist["id"],
                    "title": playlist["title"],
                    "artist": playlist.get("user", {}).get("name", "Unknown"),
                    "cover_url": playlist["picture_medium"],
                    "widget_url": widget_url
                }
        except Exception as e:
            print(f"Error searching playlist on Deezer: {e}")
        return None
    
    def _search_deezer(self, music_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Search for music on Deezer based on the detected music type
        Returns Deezer data if found
        """
        music_type = music_info.get("type")
        
        if music_type == "track":
            return self._search_track(music_info)
        elif music_type == "album":
            return self._search_album(music_info)
        elif music_type == "playlist":
            return self._search_playlist(music_info)
        else:
            print(f"Unsupported music type: {music_type}")
            return None
    
    def _test_widget_url(self, url: str) -> bool:
        """Test if a Deezer widget URL is accessible"""
        try:
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _get_working_widget_url(self, deezer_id: str, content_type: str) -> str:
        """Get a working Deezer widget URL using auto theme"""
        if content_type == "album":
            return f"{self.widget_base_url}/widget/auto/album/{deezer_id}"
        elif content_type == "track":
            # For tracks, use track format (not playlist)
            return f"{self.widget_base_url}/widget/auto/track/{deezer_id}"
        else:
            return f"{self.widget_base_url}/widget/auto/playlist/{deezer_id}"

    def _generate_widget_html(self, deezer_data: Dict[str, Any], widget_type: str = "default") -> str:
        """Generate HTML iframe for Deezer widget"""
        widget_url = deezer_data.get("widget_url")
        if not widget_url:
            return ""
        
        # Different widget styles based on type
        widget_styles = {
            "default": 'width="100%" height="300"',
            "compact": 'width="100%" height="152"',
            "large": 'width="100%" height="400"'
        }
        
        style = widget_styles.get(widget_type, widget_styles["default"])
        
        return f'''<iframe title="deezer-widget" src="{widget_url}" {style} frameborder="0" allowtransparency="true" allow="encrypted-media; clipboard-write"></iframe>'''
    
    def get_music_widget(self, description: str, widget_type: str = "default") -> Optional[Dict[str, Any]]:
        """
        Complete workflow: extract music info, search Deezer, and generate widget
        Returns widget data if music is found and available on Deezer
        """
        # Step 1: Extract music information from description
        music_info = self.extract_music_info(description)
        if not music_info:
            return None
        
        # Step 2: Search for music on Deezer
        deezer_data = self._search_deezer(music_info)
        if not deezer_data:
            return None
        
        # Step 3: Generate widget data
        return {
            "detected": music_info,
            "deezer": deezer_data,
            "widget_html": self._generate_widget_html(deezer_data, widget_type),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_supported_patterns(self) -> Dict[str, str]:
        """Get information about supported music detection patterns"""
        return {
            "russell_radio": "Russell Radio: [song] by [artist]",
            "playlist": "Playlist: [playlist name]",
            "album": "Album: [album name] by [artist]"
        }
    
    def test_music_detection(self, test_descriptions: list) -> Dict[str, Any]:
        """
        Test music detection with sample descriptions
        Useful for debugging and validation
        """
        results = {}
        for i, description in enumerate(test_descriptions):
            music_info = self.extract_music_info(description)
            results[f"test_{i+1}"] = {
                "description": description,
                "detected": music_info is not None,
                "music_info": music_info
            }
        return results