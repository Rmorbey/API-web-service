#!/usr/bin/env python3
"""
Response Compression Middleware
Compresses large responses to reduce bandwidth usage
"""

import gzip
import logging
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
import io

logger = logging.getLogger(__name__)

class CompressionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to compress large responses using gzip compression
    Only compresses responses larger than the threshold
    """
    
    def __init__(self, app, min_size_bytes: int = 1024, compression_level: int = 6):
        super().__init__(app)
        self.min_size_bytes = min_size_bytes
        self.compression_level = compression_level
        logger.info(f"CompressionMiddleware initialized with min_size={min_size_bytes} bytes, level={compression_level}")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and compress response if needed"""
        response = await call_next(request)
        
        # Only compress if response is large enough and not already compressed
        if self._should_compress(response):
            response = await self._compress_response(response)
        
        return response
    
    def _should_compress(self, response: Response) -> bool:
        """Check if response should be compressed"""
        # Don't compress if already compressed
        if response.headers.get("content-encoding"):
            return False
        
        # Don't compress if content-type is not compressible
        content_type = response.headers.get("content-type", "")
        if not self._is_compressible_content_type(content_type):
            return False
        
        # Don't compress if response is too small
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) < self.min_size_bytes:
            return False
        
        return True
    
    def _is_compressible_content_type(self, content_type: str) -> bool:
        """Check if content type is suitable for compression"""
        compressible_types = [
            "application/json",
            "application/javascript",
            "text/html",
            "text/css",
            "text/plain",
            "text/xml",
            "application/xml",
            "text/csv"
        ]
        
        return any(ct in content_type for ct in compressible_types)
    
    async def _compress_response(self, response: Response) -> Response:
        """Compress the response body"""
        try:
            # Get the response body
            body = b""
            if hasattr(response, 'body'):
                body = response.body
            elif hasattr(response, 'body_iterator'):
                # For streaming responses, collect the body
                async for chunk in response.body_iterator:
                    body += chunk
            
            # Compress the body
            compressed_body = gzip.compress(body, compresslevel=self.compression_level)
            
            # Only use compression if it actually reduces size
            if len(compressed_body) < len(body):
                # Create new response with compressed body
                compressed_response = Response(
                    content=compressed_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
                
                # Add compression headers
                compressed_response.headers["content-encoding"] = "gzip"
                compressed_response.headers["content-length"] = str(len(compressed_body))
                compressed_response.headers["vary"] = "Accept-Encoding"
                
                logger.debug(f"Compressed response: {len(body)} -> {len(compressed_body)} bytes ({len(compressed_body)/len(body)*100:.1f}%)")
                return compressed_response
            else:
                # Compression didn't help, return original
                logger.debug(f"Compression not beneficial: {len(body)} bytes")
                return response
                
        except Exception as e:
            logger.warning(f"Failed to compress response: {e}")
            return response


class SmartCompressionMiddleware(BaseHTTPMiddleware):
    """
    Smart compression middleware that adapts compression based on content type and size
    """
    
    def __init__(self, app, 
                 json_min_size: int = 512,
                 text_min_size: int = 1024,
                 compression_level: int = 6):
        super().__init__(app)
        self.json_min_size = json_min_size
        self.text_min_size = text_min_size
        self.compression_level = compression_level
        logger.info(f"SmartCompressionMiddleware initialized with JSON min={json_min_size}, text min={text_min_size}")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with smart compression"""
        response = await call_next(request)
        
        # Check if client accepts gzip encoding
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding:
            return response
        
        # Only compress if response is large enough and not already compressed
        if self._should_compress(response):
            response = await self._compress_response(response)
        
        return response
    
    def _should_compress(self, response: Response) -> bool:
        """Check if response should be compressed based on content type and size"""
        # Don't compress if already compressed
        if response.headers.get("content-encoding"):
            return False
        
        content_type = response.headers.get("content-type", "")
        content_length = response.headers.get("content-length")
        
        if not content_length:
            return False
        
        size = int(content_length)
        
        # Different thresholds for different content types
        if "application/json" in content_type:
            return size >= self.json_min_size
        elif any(ct in content_type for ct in ["text/", "application/javascript", "application/css"]):
            return size >= self.text_min_size
        else:
            return False
    
    async def _compress_response(self, response: Response) -> Response:
        """Compress the response body with smart settings"""
        try:
            # Get the response body
            body = b""
            if hasattr(response, 'body'):
                body = response.body
            elif hasattr(response, 'body_iterator'):
                # For streaming responses, collect the body
                async for chunk in response.body_iterator:
                    body += chunk
            
            # Use different compression levels based on content type
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                # JSON can be compressed more aggressively
                compression_level = min(self.compression_level + 2, 9)
            else:
                compression_level = self.compression_level
            
            # Compress the body
            compressed_body = gzip.compress(body, compresslevel=compression_level)
            
            # Only use compression if it actually reduces size significantly
            compression_ratio = len(compressed_body) / len(body)
            if compression_ratio < 0.9:  # At least 10% reduction
                # Create new response with compressed body
                compressed_response = Response(
                    content=compressed_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
                
                # Add compression headers
                compressed_response.headers["content-encoding"] = "gzip"
                compressed_response.headers["content-length"] = str(len(compressed_body))
                compressed_response.headers["vary"] = "Accept-Encoding"
                
                logger.debug(f"Smart compressed {content_type}: {len(body)} -> {len(compressed_body)} bytes ({compression_ratio*100:.1f}%)")
                return compressed_response
            else:
                # Compression didn't help enough, return original
                logger.debug(f"Smart compression not beneficial for {content_type}: {compression_ratio*100:.1f}%")
                return response
                
        except Exception as e:
            logger.warning(f"Failed to smart compress response: {e}")
            return response
