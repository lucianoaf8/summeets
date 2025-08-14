"""
Performance optimization through intelligent caching.
Implements file-based and memory caching for expensive operations.
"""
import json
import pickle
import hashlib
import logging
from pathlib import Path
from typing import Any, Optional, Callable, Dict, Union
from functools import wraps
from datetime import datetime, timedelta
import tempfile
import os

from .config import SETTINGS
from .exceptions import FileOperationError
from .security import secure_temp_file

log = logging.getLogger(__name__)


class CacheConfig:
    """Configuration for caching behavior."""
    
    def __init__(
        self,
        ttl_seconds: int = 3600,  # 1 hour default
        max_size: int = 100,      # Max cached items
        cache_dir: Optional[Path] = None,
        memory_cache: bool = True,
        disk_cache: bool = True
    ):
        """
        Initialize cache configuration.
        
        Args:
            ttl_seconds: Time to live for cached items
            max_size: Maximum number of items in cache
            cache_dir: Directory for disk cache (uses temp if None)
            memory_cache: Enable in-memory caching
            disk_cache: Enable disk-based caching
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self.cache_dir = cache_dir or (SETTINGS.temp_dir / "cache")
        self.memory_cache = memory_cache
        self.disk_cache = disk_cache
        
        # Ensure cache directory exists
        if self.disk_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)


class CacheEntry:
    """Represents a cached entry with metadata."""
    
    def __init__(self, value: Any, created_at: datetime):
        """
        Initialize cache entry.
        
        Args:
            value: The cached value
            created_at: When the entry was created
        """
        self.value = value
        self.created_at = created_at
    
    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if the cache entry has expired."""
        if ttl_seconds <= 0:
            return False  # Never expires
        
        expiry_time = self.created_at + timedelta(seconds=ttl_seconds)
        return datetime.now() > expiry_time
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "value": self.value,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "CacheEntry":
        """Create from dictionary."""
        return cls(
            value=data["value"],
            created_at=datetime.fromisoformat(data["created_at"])
        )


class SmartCache:
    """
    Smart caching system with both memory and disk storage.
    Automatically manages cache size and expiration.
    """
    
    def __init__(self, config: Optional[CacheConfig] = None):
        """
        Initialize the cache.
        
        Args:
            config: Cache configuration
        """
        self.config = config or CacheConfig()
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._access_times: Dict[str, datetime] = {}
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate a cache key from arguments."""
        # Create a deterministic key from arguments
        key_data = {
            "args": args,
            "kwargs": sorted(kwargs.items())
        }
        
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def _get_disk_path(self, key: str) -> Path:
        """Get the disk path for a cache key."""
        return self.config.cache_dir / f"{key}.cache"
    
    def _cleanup_memory_cache(self):
        """Remove expired and least recently used items from memory cache."""
        now = datetime.now()
        
        # Remove expired items
        expired_keys = [
            key for key, entry in self._memory_cache.items()
            if entry.is_expired(self.config.ttl_seconds)
        ]
        
        for key in expired_keys:
            self._memory_cache.pop(key, None)
            self._access_times.pop(key, None)
            log.debug(f"Removed expired cache entry: {key[:8]}...")
        
        # Remove LRU items if over size limit
        if len(self._memory_cache) > self.config.max_size:
            # Sort by access time (oldest first)
            sorted_keys = sorted(
                self._access_times.items(),
                key=lambda x: x[1]
            )
            
            # Remove oldest items
            items_to_remove = len(self._memory_cache) - self.config.max_size
            for key, _ in sorted_keys[:items_to_remove]:
                self._memory_cache.pop(key, None)
                self._access_times.pop(key, None)
                log.debug(f"Removed LRU cache entry: {key[:8]}...")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        # Try memory cache first
        if self.config.memory_cache and key in self._memory_cache:
            entry = self._memory_cache[key]
            
            if not entry.is_expired(self.config.ttl_seconds):
                self._access_times[key] = datetime.now()
                log.debug(f"Memory cache hit: {key[:8]}...")
                return entry.value
            else:
                # Remove expired entry
                self._memory_cache.pop(key, None)
                self._access_times.pop(key, None)
        
        # Try disk cache
        if self.config.disk_cache:
            disk_path = self._get_disk_path(key)
            
            if disk_path.exists():
                try:
                    with open(disk_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        entry = CacheEntry.from_dict(data)
                    
                    if not entry.is_expired(self.config.ttl_seconds):
                        # Store in memory cache for faster access
                        if self.config.memory_cache:
                            self._memory_cache[key] = entry
                            self._access_times[key] = datetime.now()
                        
                        log.debug(f"Disk cache hit: {key[:8]}...")
                        return entry.value
                    else:
                        # Remove expired disk cache
                        disk_path.unlink()
                        log.debug(f"Removed expired disk cache: {key[:8]}...")
                
                except (json.JSONDecodeError, KeyError, OSError) as e:
                    log.warning(f"Failed to read disk cache {key[:8]}...: {e}")
                    # Remove corrupted cache file
                    try:
                        disk_path.unlink()
                    except OSError:
                        pass
        
        return None
    
    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        entry = CacheEntry(value, datetime.now())
        
        # Store in memory cache
        if self.config.memory_cache:
            self._memory_cache[key] = entry
            self._access_times[key] = datetime.now()
            self._cleanup_memory_cache()
            log.debug(f"Stored in memory cache: {key[:8]}...")
        
        # Store in disk cache
        if self.config.disk_cache:
            disk_path = self._get_disk_path(key)
            
            try:
                # Use secure temp file for atomic write
                with secure_temp_file(
                    suffix=".cache",
                    dir=self.config.cache_dir
                ) as temp_path:
                    with open(temp_path, 'w', encoding='utf-8') as f:
                        json.dump(entry.to_dict(), f, default=str)
                    
                    # Atomic move to final location
                    temp_path.replace(disk_path)
                    log.debug(f"Stored in disk cache: {key[:8]}...")
            
            except (OSError, json.JSONEncodeError) as e:
                log.warning(f"Failed to write disk cache {key[:8]}...: {e}")
    
    def invalidate(self, key: str) -> None:
        """
        Invalidate a cache entry.
        
        Args:
            key: Cache key to invalidate
        """
        # Remove from memory cache
        if self.config.memory_cache:
            self._memory_cache.pop(key, None)
            self._access_times.pop(key, None)
        
        # Remove from disk cache
        if self.config.disk_cache:
            disk_path = self._get_disk_path(key)
            try:
                disk_path.unlink()
                log.debug(f"Invalidated cache entry: {key[:8]}...")
            except OSError:
                pass
    
    def clear(self) -> None:
        """Clear all cache entries."""
        # Clear memory cache
        if self.config.memory_cache:
            self._memory_cache.clear()
            self._access_times.clear()
        
        # Clear disk cache
        if self.config.disk_cache and self.config.cache_dir.exists():
            for cache_file in self.config.cache_dir.glob("*.cache"):
                try:
                    cache_file.unlink()
                except OSError:
                    pass
        
        log.info("Cleared all cache entries")
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        memory_size = len(self._memory_cache) if self.config.memory_cache else 0
        
        disk_size = 0
        if self.config.disk_cache and self.config.cache_dir.exists():
            disk_size = len(list(self.config.cache_dir.glob("*.cache")))
        
        return {
            "memory_entries": memory_size,
            "disk_entries": disk_size,
            "memory_enabled": self.config.memory_cache,
            "disk_enabled": self.config.disk_cache,
            "ttl_seconds": self.config.ttl_seconds,
            "max_size": self.config.max_size
        }


# Global cache instance
_global_cache = SmartCache()


def cached(
    ttl_seconds: int = 3600,
    key_func: Optional[Callable] = None,
    cache_instance: Optional[SmartCache] = None
):
    """
    Decorator for caching function results.
    
    Args:
        ttl_seconds: Time to live for cached results
        key_func: Custom function to generate cache key
        cache_instance: Custom cache instance to use
        
    Returns:
        Decorated function
        
    Example:
        @cached(ttl_seconds=1800)
        def expensive_operation(file_path: Path) -> Dict:
            # Expensive computation here
            return result
    """
    def decorator(func: Callable) -> Callable:
        cache = cache_instance or _global_cache
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache._generate_key(func.__name__, *args, **kwargs)
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                log.debug(f"Cache hit for {func.__name__}: {cache_key[:8]}...")
                return cached_result
            
            # Execute function and cache result
            log.debug(f"Cache miss for {func.__name__}: {cache_key[:8]}...")
            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            
            return result
        
        # Add cache management methods
        wrapper.clear_cache = lambda: cache.clear()
        wrapper.invalidate = lambda *args, **kwargs: cache.invalidate(
            key_func(*args, **kwargs) if key_func 
            else cache._generate_key(func.__name__, *args, **kwargs)
        )
        
        return wrapper
    
    return decorator


def file_content_key(file_path: Path) -> str:
    """
    Generate cache key based on file path and modification time.
    Useful for caching results that depend on file content.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Cache key string
    """
    try:
        stat = file_path.stat()
        key_data = {
            "path": str(file_path.resolve()),
            "size": stat.st_size,
            "mtime": stat.st_mtime
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()
    except OSError:
        # If we can't stat the file, use just the path
        return hashlib.sha256(str(file_path).encode()).hexdigest()


# Cached expensive operations for audio processing
@cached(ttl_seconds=3600)  # Cache for 1 hour
def cached_ffprobe_info(file_path: Path) -> Dict:
    """
    Cached version of ffprobe_info for expensive audio analysis.
    Cache key includes file modification time to detect changes.
    """
    from .audio.ffmpeg_ops import ffprobe_info
    return ffprobe_info(file_path)


def clear_all_caches():
    """Clear all global caches."""
    _global_cache.clear()
    log.info("Cleared all global caches")


def get_cache_stats() -> Dict[str, Any]:
    """Get statistics for all caches."""
    return {
        "global_cache": _global_cache.stats(),
    }