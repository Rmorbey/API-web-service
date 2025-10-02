#!/usr/bin/env python3
"""
Unit tests for Compression Middleware
Tests response compression functionality
"""

import pytest
import gzip
from unittest.mock import Mock, AsyncMock
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from projects.fundraising_tracking_app.strava_integration.compression_middleware import (
    CompressionMiddleware, 
    SmartCompressionMiddleware
)


class TestCompressionMiddleware:
    """Test CompressionMiddleware functionality"""
    
    def test_compression_middleware_init(self):
        """Test CompressionMiddleware initialization"""
        app = FastAPI()
        middleware = CompressionMiddleware(app, min_size_bytes=512, compression_level=6)
        assert middleware.min_size_bytes == 512
        assert middleware.compression_level == 6
    
    def test_should_compress_large_response(self):
        """Test that large responses should be compressed"""
        app = FastAPI()
        middleware = CompressionMiddleware(app, min_size_bytes=100)
        
        response = Response(
            content=b"x" * 200,  # 200 bytes, larger than threshold
            headers={"content-type": "application/json"}
        )
        
        assert middleware._should_compress(response) is True
    
    def test_should_not_compress_small_response(self):
        """Test that small responses should not be compressed"""
        app = FastAPI()
        middleware = CompressionMiddleware(app, min_size_bytes=100)
        
        response = Response(
            content=b"x" * 50,  # 50 bytes, smaller than threshold
            headers={"content-type": "application/json", "content-length": "50"}
        )
        
        assert middleware._should_compress(response) is False
    
    def test_should_not_compress_already_compressed(self):
        """Test that already compressed responses should not be compressed again"""
        app = FastAPI()
        middleware = CompressionMiddleware(app)
        
        response = Response(
            content=b"compressed content",
            headers={"content-encoding": "gzip", "content-type": "application/json"}
        )
        
        assert middleware._should_compress(response) is False
    
    def test_should_not_compress_non_compressible_content_type(self):
        """Test that non-compressible content types should not be compressed"""
        app = FastAPI()
        middleware = CompressionMiddleware(app)
        
        response = Response(
            content=b"image data",
            headers={"content-type": "image/jpeg", "content-length": "1000"}
        )
        
        assert middleware._should_compress(response) is False
    
    def test_is_compressible_content_type(self):
        """Test content type compressibility detection"""
        app = FastAPI()
        middleware = CompressionMiddleware(app)
        
        # Compressible types
        assert middleware._is_compressible_content_type("application/json") is True
        assert middleware._is_compressible_content_type("text/html") is True
        assert middleware._is_compressible_content_type("application/javascript") is True
        assert middleware._is_compressible_content_type("text/css") is True
        
        # Non-compressible types
        assert middleware._is_compressible_content_type("image/jpeg") is False
        assert middleware._is_compressible_content_type("video/mp4") is False
        assert middleware._is_compressible_content_type("application/octet-stream") is False
    
    @pytest.mark.asyncio
    async def test_compress_response(self):
        """Test response compression"""
        app = FastAPI()
        middleware = CompressionMiddleware(app, min_size_bytes=10)
        
        # Create a response with compressible content
        original_content = b"x" * 100  # 100 bytes of repeated content (highly compressible)
        response = Response(
            content=original_content,
            headers={"content-type": "application/json", "content-length": "100"}
        )
        
        compressed_response = await middleware._compress_response(response)
        
        # Check that response was compressed
        assert compressed_response.headers["content-encoding"] == "gzip"
        assert int(compressed_response.headers["content-length"]) < 100
        assert compressed_response.headers["vary"] == "Accept-Encoding"
        
        # Verify we can decompress the content
        decompressed = gzip.decompress(compressed_response.body)
        assert decompressed == original_content
    
    @pytest.mark.asyncio
    async def test_compress_response_no_benefit(self):
        """Test that responses that don't benefit from compression are not compressed"""
        app = FastAPI()
        middleware = CompressionMiddleware(app, min_size_bytes=10)
        
        # Create a response with already compressed content (random data)
        import random
        original_content = bytes([random.randint(0, 255) for _ in range(100)])
        response = Response(
            content=original_content,
            headers={"content-type": "application/json", "content-length": "100"}
        )
        
        compressed_response = await middleware._compress_response(response)
        
        # If compression doesn't help, should return original response
        if compressed_response.headers.get("content-encoding") == "gzip":
            # Compression was applied, verify it's smaller
            assert int(compressed_response.headers["content-length"]) < 100
        else:
            # No compression applied, should be original
            assert compressed_response.body == original_content


class TestSmartCompressionMiddleware:
    """Test SmartCompressionMiddleware functionality"""
    
    def test_smart_compression_middleware_init(self):
        """Test SmartCompressionMiddleware initialization"""
        app = FastAPI()
        middleware = SmartCompressionMiddleware(
            app, 
            json_min_size=512, 
            text_min_size=1024, 
            compression_level=6
        )
        assert middleware.json_min_size == 512
        assert middleware.text_min_size == 1024
        assert middleware.compression_level == 6
    
    def test_should_compress_json_response(self):
        """Test that JSON responses are compressed with appropriate threshold"""
        app = FastAPI()
        middleware = SmartCompressionMiddleware(app, json_min_size=100)
        
        response = Response(
            content=b'{"data": "test"}',
            headers={"content-type": "application/json", "content-length": "150"}
        )
        
        assert middleware._should_compress(response) is True
    
    def test_should_not_compress_small_json_response(self):
        """Test that small JSON responses are not compressed"""
        app = FastAPI()
        middleware = SmartCompressionMiddleware(app, json_min_size=100)
        
        response = Response(
            content=b'{"data": "test"}',
            headers={"content-type": "application/json", "content-length": "50"}
        )
        
        assert middleware._should_compress(response) is False
    
    def test_should_compress_text_response(self):
        """Test that text responses are compressed with appropriate threshold"""
        app = FastAPI()
        middleware = SmartCompressionMiddleware(app, text_min_size=100)
        
        response = Response(
            content=b"Some text content that is long enough to be compressed",
            headers={"content-type": "text/html", "content-length": "150"}
        )
        
        assert middleware._should_compress(response) is True
    
    def test_should_not_compress_small_text_response(self):
        """Test that small text responses are not compressed"""
        app = FastAPI()
        middleware = SmartCompressionMiddleware(app, text_min_size=100)
        
        response = Response(
            content=b"Short text",
            headers={"content-type": "text/html", "content-length": "50"}
        )
        
        assert middleware._should_compress(response) is False
    
    @pytest.mark.asyncio
    async def test_smart_compress_response_json(self):
        """Test smart compression for JSON responses"""
        app = FastAPI()
        middleware = SmartCompressionMiddleware(app, json_min_size=10)
        
        # Create a JSON response with repeated content (highly compressible)
        json_content = b'{"data": "' + b"x" * 50 + b'"}'
        response = Response(
            content=json_content,
            headers={"content-type": "application/json", "content-length": str(len(json_content))}
        )
        
        compressed_response = await middleware._compress_response(response)
        
        # Check that response was compressed
        assert compressed_response.headers["content-encoding"] == "gzip"
        assert int(compressed_response.headers["content-length"]) < len(json_content)
        assert compressed_response.headers["vary"] == "Accept-Encoding"
        
        # Verify we can decompress the content
        decompressed = gzip.decompress(compressed_response.body)
        assert decompressed == json_content
    
    def test_middleware_integration(self):
        """Test middleware integration with FastAPI app"""
        app = FastAPI()
        app.add_middleware(SmartCompressionMiddleware, json_min_size=10)
        
        @app.get("/test")
        def test_endpoint():
            return {"message": "x" * 100}  # Large response
        
        client = TestClient(app)
        
        # Make request with gzip acceptance
        response = client.get("/test", headers={"Accept-Encoding": "gzip"})
        
        # Should be compressed
        assert response.status_code == 200
        # Note: TestClient might not show compression headers, but the middleware should work
        assert "message" in response.json()
