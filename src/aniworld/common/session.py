"""
Shared HTTP session with connection pooling and retry logic.

This module provides a singleton session instance that reuses connections
for better performance across the entire application.
"""

import logging
from typing import Optional
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class SharedSession:
    """
    Singleton HTTP session with connection pooling.
    
    Features:
    - Connection pooling (reuses TCP connections)
    - Automatic retries with exponential backoff
    - Shared across entire application
    - Thread-safe
    """
    
    _instance: Optional[Session] = None
    _initialized: bool = False
    
    def __new__(cls):
        """Create or return existing session instance."""
        if cls._instance is None:
            cls._instance = Session()
            cls._configure_session()
            cls._initialized = True
            logging.debug("SharedSession initialized with connection pooling")
        return cls._instance
    
    @classmethod
    def _configure_session(cls):
        """Configure session with optimal settings."""
        if cls._instance is None:
            return
        
        # Retry strategy for failed requests
        retry_strategy = Retry(
            total=3,                      # Maximum 3 retry attempts
            backoff_factor=1,            # Wait 1, 2, 4 seconds between retries
            status_forcelist=[429, 500, 502, 503, 504],  # Retry on these status codes
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
            raise_on_status=False        # Don't raise exception, let caller handle
        )
        
        # HTTP Adapter with connection pooling
        adapter = HTTPAdapter(
            pool_connections=10,          # Number of connection pools to cache
            pool_maxsize=20,             # Maximum connections per pool
            max_retries=retry_strategy,
            pool_block=False             # Don't block when pool is full
        )
        
        # Mount adapter for both HTTP and HTTPS
        cls._instance.mount("http://", adapter)
        cls._instance.mount("https://", adapter)
        
        # Set default headers
        cls._instance.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        logging.debug("Session configured: pool_connections=10, pool_maxsize=20, retries=3")
    
    @classmethod
    def get_session(cls) -> Session:
        """
        Get the shared session instance.
        
        Returns:
            Session: Configured requests session
        """
        if cls._instance is None:
            cls()
        return cls._instance
    
    @classmethod
    def close(cls):
        """Close the shared session and cleanup resources."""
        if cls._instance is not None:
            cls._instance.close()
            cls._instance = None
            cls._initialized = False
            logging.debug("SharedSession closed")


# Global session instance for easy import
session = SharedSession.get_session()


def get_session() -> Session:
    """
    Get the shared HTTP session instance.
    
    Usage:
        from aniworld.common.session import get_session
        
        session = get_session()
        response = session.get('https://example.com')
    
    Returns:
        Session: Configured requests session with connection pooling
    """
    return SharedSession.get_session()
