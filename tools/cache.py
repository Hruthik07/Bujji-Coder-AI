"""
Caching system for performance optimization
Caches embeddings, AST analysis, and other expensive operations
"""
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional, Dict
from functools import wraps
import pickle
from collections import OrderedDict


class Cache:
    """
    Simple file-based cache for expensive operations.
    Uses pickle for Python objects and JSON for simple data.
    Supports LRU eviction and size limits.
    """
    
    def __init__(self, cache_dir: str = ".cache", max_size: int = 1000, max_memory_mb: int = 500):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.default_ttl = 3600 * 24 * 7  # 7 days default
        self.max_size = max_size  # Maximum number of cache entries
        self.max_memory_mb = max_memory_mb  # Maximum memory usage in MB
        self._access_order = OrderedDict()  # Track access order for LRU
        self._memory_usage = 0  # Track approximate memory usage
    
    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for a key"""
        # Create safe filename from key
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    def get(self, key: str, default: Any = None) -> Optional[Any]:
        """
        Get value from cache.
        Updates access order for LRU.
        
        Args:
            key: Cache key
            default: Default value if not found or expired
            
        Returns:
            Cached value or default
        """
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return default
        
        try:
            with open(cache_path, 'rb') as f:
                cache_data = pickle.load(f)
            
            # Check TTL
            if time.time() > cache_data.get('expires_at', 0):
                cache_path.unlink()  # Delete expired cache
                if key in self._access_order:
                    del self._access_order[key]
                return default
            
            # Update access order (move to end for LRU)
            if key in self._access_order:
                self._access_order.move_to_end(key)
            else:
                self._access_order[key] = time.time()
            
            return cache_data.get('value')
        
        except Exception:
            # If cache is corrupted, delete it
            if cache_path.exists():
                cache_path.unlink()
            if key in self._access_order:
                del self._access_order[key]
            return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.
        Evicts old entries if size/memory limits exceeded.
        
        Args:
            key: Cache key
            value: Value to cache (must be pickle-able)
            ttl: Time to live in seconds (default: 7 days)
            
        Returns:
            True if successful
        """
        cache_path = self._get_cache_path(key)
        ttl = ttl or self.default_ttl
        
        # Estimate memory usage (rough approximation)
        try:
            import sys
            value_size = sys.getsizeof(pickle.dumps(value)) / (1024 * 1024)  # MB
        except Exception:
            value_size = 0.1  # Default estimate
        
        # Evict if needed
        self._evict_if_needed(value_size)
        
        try:
            cache_data = {
                'value': value,
                'created_at': time.time(),
                'expires_at': time.time() + ttl
            }
            
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
            
            # Update access order
            if key in self._access_order:
                self._access_order.move_to_end(key)
            else:
                self._access_order[key] = time.time()
                self._memory_usage += value_size
            
            return True
        
        except Exception as e:
            print(f"⚠️  Cache write failed: {e}")
            return False
    
    def _evict_if_needed(self, new_value_size: float):
        """Evict old cache entries if limits exceeded"""
        # Evict by size limit
        while len(self._access_order) >= self.max_size:
            oldest_key = next(iter(self._access_order))
            self.delete(oldest_key)
        
        # Evict by memory limit
        while self._memory_usage + new_value_size > self.max_memory_mb and self._access_order:
            oldest_key = next(iter(self._access_order))
            # Estimate size of entry being deleted BEFORE calling delete (to avoid double-counting)
            cache_path = self._get_cache_path(oldest_key)
            size_mb = 0
            try:
                if cache_path.exists():
                    size_mb = cache_path.stat().st_size / (1024 * 1024)
                    self._memory_usage = max(0, self._memory_usage - size_mb)
            except (OSError, ValueError):
                pass
            self.delete(oldest_key)
    
    def delete(self, key: str) -> bool:
        """Delete a cache entry"""
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            try:
                # Update memory usage estimate (only if not already subtracted in eviction)
                if key in self._access_order:
                    size_mb = cache_path.stat().st_size / (1024 * 1024)
                    self._memory_usage = max(0, self._memory_usage - size_mb)
            except (OSError, ValueError):
                pass
            cache_path.unlink()
        
        # Remove from access order
        if key in self._access_order:
            del self._access_order[key]
        
        return True
    
    def clear(self):
        """Clear all cache entries"""
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        cache_files = list(self.cache_dir.glob("*.cache"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            "entries": len(cache_files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "cache_dir": str(self.cache_dir)
        }


def cached(ttl: Optional[int] = None, key_func: Optional[callable] = None):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time to live in seconds
        key_func: Function to generate cache key from args
    """
    def decorator(func):
        cache = Cache()
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default: use function name + args hash
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = "::".join(key_parts)
            
            # Try cache first
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Compute value
            value = func(*args, **kwargs)
            
            # Store in cache
            cache.set(cache_key, value, ttl=ttl)
            
            return value
        
        wrapper.cache = cache
        wrapper.clear_cache = lambda: cache.clear()
        return wrapper
    
    return decorator
