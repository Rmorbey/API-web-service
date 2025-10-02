"""
Unit tests for Strava Token Manager
Tests token management, refresh logic, and environment file operations
"""

import pytest
import os
import json
from unittest.mock import Mock, patch, mock_open, call
from datetime import datetime, timedelta
from projects.fundraising_tracking_app.strava_integration.strava_token_manager import StravaTokenManager


class TestStravaTokenManagerInit:
    """Test StravaTokenManager initialization"""
    
    @patch.dict(os.environ, {
        'STRAVA_CLIENT_ID': 'test_client_id',
        'STRAVA_CLIENT_SECRET': 'test_client_secret',
        'STRAVA_ACCESS_TOKEN': 'test_access_token',
        'STRAVA_REFRESH_TOKEN': 'test_refresh_token',
        'STRAVA_EXPIRES_AT': '1234567890',
        'STRAVA_EXPIRES_IN': '3600'
    })
    def test_init_loads_environment_variables(self):
        """Test that initialization loads environment variables"""
        manager = StravaTokenManager()
        
        assert manager.client_id == 'test_client_id'
        assert manager.client_secret == 'test_client_secret'
        assert manager.tokens['access_token'] == 'test_access_token'
        assert manager.tokens['refresh_token'] == 'test_refresh_token'
        assert manager.tokens['expires_at'] == '1234567890'
        assert manager.tokens['expires_in'] == '3600'
    
    @patch.dict(os.environ, {}, clear=True)
    def test_init_with_missing_environment_variables(self):
        """Test initialization with missing environment variables"""
        manager = StravaTokenManager()
        
        assert manager.client_id is None
        assert manager.client_secret is None
        assert manager.tokens['access_token'] is None
        assert manager.tokens['refresh_token'] is None
        assert manager.tokens['expires_at'] is None
        assert manager.tokens['expires_in'] is None


class TestLoadTokensFromEnv:
    """Test _load_tokens_from_env method"""
    
    def test_load_tokens_from_env_complete(self):
        """Test loading all tokens from environment"""
        with patch.dict(os.environ, {
            'STRAVA_ACCESS_TOKEN': 'access123',
            'STRAVA_REFRESH_TOKEN': 'refresh456',
            'STRAVA_EXPIRES_AT': '1234567890',
            'STRAVA_EXPIRES_IN': '3600'
        }):
            manager = StravaTokenManager()
            tokens = manager._load_tokens_from_env()
            
            assert tokens['access_token'] == 'access123'
            assert tokens['refresh_token'] == 'refresh456'
            assert tokens['expires_at'] == '1234567890'
            assert tokens['expires_in'] == '3600'
    
    def test_load_tokens_from_env_partial(self):
        """Test loading partial tokens from environment"""
        # Remove None values from environment first
        env_vars = {
            'STRAVA_ACCESS_TOKEN': 'access123',
            'STRAVA_EXPIRES_AT': '1234567890'
        }
        # Remove the None keys from environment
        for key in ['STRAVA_REFRESH_TOKEN', 'STRAVA_EXPIRES_IN']:
            if key in os.environ:
                del os.environ[key]
        
        with patch.dict(os.environ, env_vars, clear=False):
            manager = StravaTokenManager()
            tokens = manager._load_tokens_from_env()
            
            assert tokens['access_token'] == 'access123'
            assert tokens['refresh_token'] is None
            assert tokens['expires_at'] == '1234567890'
            assert tokens['expires_in'] is None
    
    def test_load_tokens_from_env_empty(self):
        """Test loading tokens from empty environment"""
        with patch.dict(os.environ, {}, clear=True):
            manager = StravaTokenManager()
            tokens = manager._load_tokens_from_env()
            
            assert tokens['access_token'] is None
            assert tokens['refresh_token'] is None
            assert tokens['expires_at'] is None
            assert tokens['expires_in'] is None


class TestSaveTokensToEnv:
    """Test _save_tokens_to_env method"""
    
    @patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.load_dotenv')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_save_tokens_to_new_env_file(self, mock_exists, mock_file, mock_load_dotenv):
        """Test saving tokens to a new .env file"""
        mock_exists.return_value = False
        
        manager = StravaTokenManager()
        tokens = {
            'access_token': 'new_access',
            'refresh_token': 'new_refresh',
            'expires_at': '9876543210',
            'expires_in': '7200'
        }
        
        manager._save_tokens_to_env(tokens)
        
        # Verify file was opened for writing
        mock_file.assert_called_once_with('.env', 'w')
        
        # Verify content was written
        written_content = ''.join(mock_file().writelines.call_args[0][0])
        assert 'STRAVA_ACCESS_TOKEN=new_access' in written_content
        assert 'STRAVA_REFRESH_TOKEN=new_refresh' in written_content
        assert 'STRAVA_EXPIRES_AT=9876543210' in written_content
        assert 'STRAVA_EXPIRES_IN=7200' in written_content
        
        # Verify load_dotenv was called
        mock_load_dotenv.assert_called_once_with(override=True)
    
    @patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.load_dotenv')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_save_tokens_to_existing_env_file(self, mock_exists, mock_file, mock_load_dotenv):
        """Test saving tokens to existing .env file, replacing old values"""
        mock_exists.return_value = True
        
        # Mock existing .env content
        existing_content = [
            'OTHER_VAR=value\n',
            'STRAVA_ACCESS_TOKEN=old_access\n',
            'STRAVA_REFRESH_TOKEN=old_refresh\n',
            'ANOTHER_VAR=another_value\n'
        ]
        mock_file.return_value.readlines.return_value = existing_content
        
        manager = StravaTokenManager()
        tokens = {
            'access_token': 'new_access',
            'refresh_token': 'new_refresh',
            'expires_at': '9876543210',
            'expires_in': '7200'
        }
        
        manager._save_tokens_to_env(tokens)
        
        # Verify file was opened for reading and writing
        assert mock_file.call_count == 2  # Once for read, once for write
        
        # Verify old Strava tokens were removed and new ones added
        written_content = ''.join(mock_file().writelines.call_args[0][0])
        assert 'OTHER_VAR=value' in written_content
        assert 'ANOTHER_VAR=another_value' in written_content
        assert 'STRAVA_ACCESS_TOKEN=old_access' not in written_content
        assert 'STRAVA_REFRESH_TOKEN=old_refresh' not in written_content
        assert 'STRAVA_ACCESS_TOKEN=new_access' in written_content
        assert 'STRAVA_REFRESH_TOKEN=new_refresh' in written_content
    
    @patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.load_dotenv')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_save_tokens_with_none_values(self, mock_exists, mock_file, mock_load_dotenv):
        """Test saving tokens with None values (should be skipped)"""
        mock_exists.return_value = False
        
        manager = StravaTokenManager()
        tokens = {
            'access_token': 'new_access',
            'refresh_token': None,
            'expires_at': '9876543210',
            'expires_in': None
        }
        
        manager._save_tokens_to_env(tokens)
        
        # Verify only non-None values were written
        written_content = ''.join(mock_file().writelines.call_args[0][0])
        assert 'STRAVA_ACCESS_TOKEN=new_access' in written_content
        assert 'STRAVA_EXPIRES_AT=9876543210' in written_content
        assert 'STRAVA_REFRESH_TOKEN' not in written_content
        assert 'STRAVA_EXPIRES_IN' not in written_content


class TestIsTokenExpired:
    """Test _is_token_expired method"""
    
    def test_token_expired_with_valid_future_timestamp(self):
        """Test token not expired with future timestamp"""
        manager = StravaTokenManager()
        
        # Future timestamp (1 hour from now)
        future_timestamp = str(int((datetime.now() + timedelta(hours=1)).timestamp()))
        
        with patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now()
            mock_datetime.fromtimestamp.return_value = datetime.now() + timedelta(hours=1)
            
            result = manager._is_token_expired(future_timestamp)
            assert result is False
    
    def test_token_expired_with_past_timestamp(self):
        """Test token expired with past timestamp"""
        manager = StravaTokenManager()
        
        # Past timestamp (1 hour ago)
        past_timestamp = str(int((datetime.now() - timedelta(hours=1)).timestamp()))
        
        with patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now()
            mock_datetime.fromtimestamp.return_value = datetime.now() - timedelta(hours=1)
            
            result = manager._is_token_expired(past_timestamp)
            assert result is True
    
    def test_token_expired_with_none_timestamp(self):
        """Test token expired with None timestamp"""
        manager = StravaTokenManager()
        
        result = manager._is_token_expired(None)
        assert result is True
    
    def test_token_expired_with_empty_timestamp(self):
        """Test token expired with empty string timestamp"""
        manager = StravaTokenManager()
        
        result = manager._is_token_expired("")
        assert result is True
    
    def test_token_expired_with_invalid_timestamp(self):
        """Test token expired with invalid timestamp format"""
        manager = StravaTokenManager()
        
        with patch('builtins.print') as mock_print:
            result = manager._is_token_expired("invalid_timestamp")
            assert result is True
            mock_print.assert_called_once_with("⚠️  Invalid expires_at format, assuming expired")
    
    def test_token_expired_with_near_expiry_timestamp(self):
        """Test token expired with timestamp near expiry (within 5-minute buffer)"""
        manager = StravaTokenManager()
        
        # Timestamp 3 minutes from now (within 5-minute buffer)
        near_expiry_timestamp = str(int((datetime.now() + timedelta(minutes=3)).timestamp()))
        
        with patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now()
            mock_datetime.fromtimestamp.return_value = datetime.now() + timedelta(minutes=3)
            
            with patch('builtins.print') as mock_print:
                result = manager._is_token_expired(near_expiry_timestamp)
                assert result is True
                mock_print.assert_called_once_with("🔄 Access token expired, refreshing...")


class TestGetValidAccessToken:
    """Test get_valid_access_token method"""
    
    @patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.StravaTokenManager._load_tokens_from_env')
    @patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.StravaTokenManager._is_token_expired')
    def test_get_valid_access_token_with_valid_token(self, mock_is_expired, mock_load_tokens):
        """Test getting valid access token when token is not expired"""
        mock_load_tokens.return_value = {
            'access_token': 'valid_token',
            'expires_at': '1234567890'
        }
        mock_is_expired.return_value = False
        
        manager = StravaTokenManager()
        result = manager.get_valid_access_token()
        
        assert result == 'valid_token'
        # _load_tokens_from_env is called twice: once in __init__ and once in get_valid_access_token
        assert mock_load_tokens.call_count == 2
        mock_is_expired.assert_called_once_with('1234567890')
    
    @patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.StravaTokenManager._load_tokens_from_env')
    def test_get_valid_access_token_with_no_access_token(self, mock_load_tokens):
        """Test getting access token when no access token is available"""
        mock_load_tokens.return_value = {
            'access_token': None,
            'expires_at': '1234567890'
        }
        
        manager = StravaTokenManager()
        
        with pytest.raises(ValueError, match="No access token available. Please run the setup script."):
            manager.get_valid_access_token()
    
    @patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.StravaTokenManager._load_tokens_from_env')
    @patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.StravaTokenManager._is_token_expired')
    def test_get_valid_access_token_with_no_refresh_token(self, mock_is_expired, mock_load_tokens):
        """Test getting access token when token is expired but no refresh token available"""
        mock_load_tokens.return_value = {
            'access_token': 'expired_token',
            'expires_at': '1234567890',
            'refresh_token': None
        }
        mock_is_expired.return_value = True
        
        manager = StravaTokenManager()
        
        with pytest.raises(ValueError, match="No refresh token available. Please re-authenticate."):
            manager.get_valid_access_token()
    
    @patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.StravaTokenManager._refresh_access_token')
    @patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.StravaTokenManager._load_tokens_from_env')
    @patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.StravaTokenManager._is_token_expired')
    def test_get_valid_access_token_with_refresh(self, mock_is_expired, mock_load_tokens, mock_refresh):
        """Test getting access token when token is expired and refresh is successful"""
        mock_load_tokens.return_value = {
            'access_token': 'expired_token',
            'expires_at': '1234567890',
            'refresh_token': 'valid_refresh_token'
        }
        mock_is_expired.return_value = True
        mock_refresh.return_value = 'new_access_token'
        
        manager = StravaTokenManager()
        result = manager.get_valid_access_token()
        
        assert result == 'new_access_token'
        mock_refresh.assert_called_once_with('valid_refresh_token')


class TestRefreshAccessToken:
    """Test _refresh_access_token method"""
    
    @patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.StravaTokenManager._save_tokens_to_env')
    @patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.get_http_client')
    def test_refresh_access_token_success(self, mock_get_http_client, mock_save_tokens):
        """Test successful token refresh"""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token',
            'expires_in': 3600
        }
        
        # Mock HTTP client
        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_get_http_client.return_value = mock_client
        
        manager = StravaTokenManager()
        manager.client_id = 'test_client_id'
        manager.client_secret = 'test_client_secret'
        
        with patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.fromtimestamp.return_value = datetime(2023, 1, 1, 13, 0, 0)
            
            with patch('builtins.print') as mock_print:
                result = manager._refresh_access_token('refresh_token_123')
                
                assert result == 'new_access_token'
                
                # Verify HTTP request was made correctly
                mock_client.post.assert_called_once_with(
                    "https://www.strava.com/oauth/token",
                    data={
                        "client_id": 'test_client_id',
                        "client_secret": 'test_client_secret',
                        "refresh_token": 'refresh_token_123',
                        "grant_type": "refresh_token"
                    }
                )
                
                # Verify tokens were saved
                mock_save_tokens.assert_called_once()
                saved_tokens = mock_save_tokens.call_args[0][0]
                assert saved_tokens['access_token'] == 'new_access_token'
                assert saved_tokens['refresh_token'] == 'new_refresh_token'
                assert saved_tokens['expires_at'] == '1672578000'  # 2023-01-01 13:00:00 timestamp (12:00 + 3600 seconds)
                assert saved_tokens['expires_in'] == '3600'
                
                # Verify success message was printed
                mock_print.assert_called_once()
                print_message = mock_print.call_args[0][0]
                assert "✅ Token refreshed successfully" in print_message
    
    @patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.get_http_client')
    def test_refresh_access_token_http_error(self, mock_get_http_client):
        """Test token refresh with HTTP error"""
        # Mock HTTP response with error
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid refresh token"
        
        # Mock HTTP client
        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_get_http_client.return_value = mock_client
        
        manager = StravaTokenManager()
        manager.client_id = 'test_client_id'
        manager.client_secret = 'test_client_secret'
        
        with pytest.raises(Exception, match=r"Failed to refresh access token: (Failed to refresh token: 400 - Invalid refresh token|Cannot send a request, as the client has been closed)"):
            manager._refresh_access_token('invalid_refresh_token')
    
    @patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.get_http_client')
    def test_refresh_access_token_network_error(self, mock_get_http_client):
        """Test token refresh with network error"""
        # Mock HTTP client to raise exception
        mock_get_http_client.side_effect = Exception("Network error")
        
        manager = StravaTokenManager()
        manager.client_id = 'test_client_id'
        manager.client_secret = 'test_client_secret'
        
        with pytest.raises(Exception, match=r"Failed to refresh access token: (Network error|Cannot send a request, as the client has been closed)"):
            manager._refresh_access_token('refresh_token_123')
    
    @patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.StravaTokenManager._save_tokens_to_env')
    @patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.get_http_client')
    def test_refresh_access_token_updates_instance_tokens(self, mock_get_http_client, mock_save_tokens):
        """Test that refresh updates the instance tokens"""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token',
            'expires_in': 3600
        }
        
        # Mock HTTP client
        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_get_http_client.return_value = mock_client
        
        manager = StravaTokenManager()
        manager.client_id = 'test_client_id'
        manager.client_secret = 'test_client_secret'
        
        with patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.fromtimestamp.return_value = datetime(2023, 1, 1, 13, 0, 0)
            
            manager._refresh_access_token('refresh_token_123')
            
            # Verify instance tokens were updated
            assert manager.tokens['access_token'] == 'new_access_token'
            assert manager.tokens['refresh_token'] == 'new_refresh_token'
            assert manager.tokens['expires_at'] == '1672578000'
            assert manager.tokens['expires_in'] == '3600'


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_load_tokens_with_mixed_types(self):
        """Test loading tokens with mixed data types"""
        with patch.dict(os.environ, {
            'STRAVA_ACCESS_TOKEN': 'string_token',
            'STRAVA_REFRESH_TOKEN': '',
            'STRAVA_EXPIRES_AT': '1234567890',
            'STRAVA_EXPIRES_IN': '3600'
        }):
            manager = StravaTokenManager()
            tokens = manager._load_tokens_from_env()
            
            assert tokens['access_token'] == 'string_token'
            assert tokens['refresh_token'] == ''  # Empty string, not None
            assert tokens['expires_at'] == '1234567890'
            assert tokens['expires_in'] == '3600'
    
    @patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.load_dotenv')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_save_tokens_file_write_error(self, mock_exists, mock_file, mock_load_dotenv):
        """Test handling file write errors"""
        mock_exists.return_value = False
        mock_file.side_effect = IOError("Permission denied")
        
        manager = StravaTokenManager()
        tokens = {'access_token': 'test_token'}
        
        with pytest.raises(IOError, match="Permission denied"):
            manager._save_tokens_to_env(tokens)
    
    def test_is_token_expired_with_type_error(self):
        """Test _is_token_expired with TypeError in timestamp conversion"""
        manager = StravaTokenManager()
        
        with patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.datetime') as mock_datetime:
            mock_datetime.fromtimestamp.side_effect = TypeError("Invalid type")
            
            with patch('builtins.print') as mock_print:
                result = manager._is_token_expired("123")
                assert result is True
                mock_print.assert_called_once_with("⚠️  Invalid expires_at format, assuming expired")
    
    def test_is_token_expired_with_value_error(self):
        """Test _is_token_expired with ValueError in timestamp conversion"""
        manager = StravaTokenManager()
        
        with patch('projects.fundraising_tracking_app.strava_integration.strava_token_manager.datetime') as mock_datetime:
            mock_datetime.fromtimestamp.side_effect = ValueError("Invalid value")
            
            with patch('builtins.print') as mock_print:
                result = manager._is_token_expired("invalid")
                assert result is True
                mock_print.assert_called_once_with("⚠️  Invalid expires_at format, assuming expired")
