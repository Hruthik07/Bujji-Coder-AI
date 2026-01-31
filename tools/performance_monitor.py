"""
Performance monitoring service for tracking system metrics
Tracks indexing time, response time, memory usage, and API costs
"""
import time
import psutil
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import json
from collections import deque
from threading import Lock


@dataclass
class PerformanceMetric:
    """Single performance metric entry"""
    timestamp: float
    metric_type: str  # 'indexing', 'response', 'memory', 'api_call'
    value: float
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class IndexingStats:
    """Statistics for indexing operations"""
    files_indexed: int
    chunks_created: int
    embeddings_generated: int
    duration_seconds: float
    files_per_second: float
    chunks_per_second: float


@dataclass
class ResponseStats:
    """Statistics for API response times"""
    total_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float


class PerformanceMonitor:
    """
    Monitors and tracks performance metrics for the AI Coding Assistant.
    Provides real-time metrics and historical data.
    """
    
    def __init__(self, workspace_path: str = ".", max_history: int = 1000):
        self.workspace_path = Path(workspace_path).resolve()
        self.max_history = max_history
        
        # Metrics storage
        self.metrics: deque = deque(maxlen=max_history)
        self.response_times: deque = deque(maxlen=max_history)
        self.indexing_stats: List[IndexingStats] = []
        
        # Current state
        self.current_indexing_start: Optional[float] = None
        self.process = psutil.Process(os.getpid())
        
        # Thread safety
        self._lock = Lock()
        
        # Metrics file for persistence
        self.metrics_file = self.workspace_path / ".cache" / "performance_metrics.json"
        self.metrics_file.parent.mkdir(exist_ok=True)
        
        # Caching for summary (1-2 second TTL)
        self._summary_cache: Optional[Dict[str, Any]] = None
        self._summary_cache_time: float = 0.0
        self._summary_cache_ttl: float = 2.0  # 2 seconds
        
        # Load historical metrics
        self._load_metrics()
    
    def start_indexing(self):
        """Mark the start of an indexing operation"""
        with self._lock:
            self.current_indexing_start = time.time()
    
    def end_indexing(self, files_indexed: int, chunks_created: int, 
                    embeddings_generated: int) -> IndexingStats:
        """
        Mark the end of an indexing operation and record stats.
        
        Args:
            files_indexed: Number of files indexed
            chunks_created: Number of chunks created
            embeddings_generated: Number of embeddings generated
            
        Returns:
            IndexingStats object
        """
        with self._lock:
            if self.current_indexing_start is None:
                duration = 0.0
            else:
                duration = time.time() - self.current_indexing_start
                self.current_indexing_start = None
            
            stats = IndexingStats(
                files_indexed=files_indexed,
                chunks_created=chunks_created,
                embeddings_generated=embeddings_generated,
                duration_seconds=duration,
                files_per_second=files_indexed / duration if duration > 0 else 0,
                chunks_per_second=chunks_created / duration if duration > 0 else 0
            )
            
            self.indexing_stats.append(stats)
            
            # Record metric
            self._record_metric(
                metric_type="indexing",
                value=duration,
                metadata={
                    "files_indexed": files_indexed,
                    "chunks_created": chunks_created,
                    "embeddings_generated": embeddings_generated,
                    "files_per_second": stats.files_per_second,
                    "chunks_per_second": stats.chunks_per_second
                }
            )
            
            return stats
    
    def record_response_time(self, response_time: float, 
                            metadata: Optional[Dict[str, Any]] = None):
        """
        Record an API response time.
        
        Args:
            response_time: Response time in seconds
            metadata: Optional metadata (e.g., model, endpoint)
        """
        with self._lock:
            self.response_times.append(response_time)
            self._record_metric(
                metric_type="response",
                value=response_time,
                metadata=metadata
            )
    
    def record_memory_usage(self):
        """Record current memory usage"""
        with self._lock:
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
            
            self._record_metric(
                metric_type="memory",
                value=memory_mb,
                metadata={
                    "rss_mb": memory_mb,
                    "vms_mb": memory_info.vms / (1024 * 1024)
                }
            )
    
    def record_api_call(self, provider: str, model: str, tokens_used: int,
                       cost: float, duration: float):
        """
        Record an API call with cost and duration.
        
        Args:
            provider: LLM provider (openai, deepseek, anthropic)
            model: Model name
            tokens_used: Number of tokens used
            cost: Cost in USD
            duration: Call duration in seconds
        """
        with self._lock:
            self._record_metric(
                metric_type="api_call",
                value=cost,
                metadata={
                    "provider": provider,
                    "model": model,
                    "tokens_used": tokens_used,
                    "cost": cost,
                    "duration": duration,
                    "tokens_per_second": tokens_used / duration if duration > 0 else 0
                }
            )
    
    def _record_metric(self, metric_type: str, value: float,
                      metadata: Optional[Dict[str, Any]] = None):
        """Internal method to record a metric"""
        metric = PerformanceMetric(
            timestamp=time.time(),
            metric_type=metric_type,
            value=value,
            metadata=metadata
        )
        self.metrics.append(metric)
        
        # Periodically save to disk
        if len(self.metrics) % 100 == 0:
            self._save_metrics()
    
    def get_current_stats(self) -> Dict[str, Any]:
        """
        Get current performance statistics.
        Optimized to avoid blocking operations and minimize lock time.
        
        Returns:
            Dictionary with current stats
        """
        # Get data quickly with minimal lock time
        with self._lock:
            metrics_count = len(self.metrics)
            response_times_count = len(self.response_times)
            latest_indexing = self.indexing_stats[-1] if self.indexing_stats else None
            recent_metrics = list(self.metrics)[-50:]  # Only last 50 for peak memory
        
        # Calculate outside lock to avoid blocking
        # Memory stats (non-blocking)
        try:
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
        except Exception:
            memory_mb = 0.0
        
        # Calculate peak memory efficiently (only check recent metrics)
        peak_mb = memory_mb
        try:
            recent_memory_metrics = [
                m.value for m in recent_metrics 
                if m.metric_type == "memory"
            ]
            if recent_memory_metrics:
                peak_mb = max(recent_memory_metrics)
        except Exception:
            pass
        
        # Response time stats (will acquire lock internally)
        response_stats = self._calculate_response_stats()
        
        # System stats (non-blocking CPU percent)
        try:
            # Use interval=None for non-blocking call (returns last value)
            cpu_percent = self.process.cpu_percent(interval=None)
        except Exception:
            cpu_percent = 0.0
        
        try:
            threads = self.process.num_threads()
        except Exception:
            threads = 0
        
        return {
            "memory": {
                "current_mb": memory_mb,
                "peak_mb": peak_mb
            },
            "response_times": response_stats,
            "indexing": asdict(latest_indexing) if latest_indexing else None,
            "system": {
                "cpu_percent": cpu_percent,
                "threads": threads
            },
            "metrics_count": metrics_count
        }
    
    def get_historical_stats(self, metric_type: Optional[str] = None,
                           hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get historical metrics.
        
        Args:
            metric_type: Filter by metric type (None = all)
            hours: Number of hours to look back
            
        Returns:
            List of metric dictionaries
        """
        with self._lock:
            cutoff_time = time.time() - (hours * 3600)
            
            filtered = [
                asdict(m) for m in self.metrics
                if m.timestamp >= cutoff_time and
                (metric_type is None or m.metric_type == metric_type)
            ]
            
            return filtered
    
    def _calculate_response_stats(self) -> Optional[Dict[str, Any]]:
        """Calculate response time statistics (optimized, minimal lock time)"""
        with self._lock:
            if not self.response_times:
                return None
            
            # Limit to recent 500 response times to avoid slow sorting
            times_list = list(self.response_times)
            if len(times_list) > 500:
                times_list = times_list[-500:]
        
        # Calculate outside lock
        if not times_list:
            return None
        
        # Use efficient calculations
        times_list.sort()
        total = len(times_list)
        total_sum = sum(times_list)
        
        return {
            "total_requests": total,
            "avg_ms": (total_sum / total) * 1000 if total > 0 else 0,
            "min_ms": times_list[0] * 1000 if times_list else 0,
            "max_ms": times_list[-1] * 1000 if times_list else 0,
            "p95_ms": times_list[int(total * 0.95)] * 1000 if total > 0 else 0,
            "p99_ms": times_list[int(total * 0.99)] * 1000 if total > 0 else 0
        }
    
    def get_indexing_history(self) -> List[Dict[str, Any]]:
        """Get all indexing statistics"""
        with self._lock:
            return [asdict(stats) for stats in self.indexing_stats]
    
    def _save_metrics(self):
        """Save metrics to disk"""
        try:
            # Only save recent metrics to avoid large files
            recent_metrics = list(self.metrics)[-500:]  # Last 500 metrics
            
            data = {
                "metrics": [asdict(m) for m in recent_metrics],
                "indexing_stats": [asdict(s) for s in self.indexing_stats[-50:]],  # Last 50 indexing runs
                "saved_at": datetime.now().isoformat()
            }
            
            with open(self.metrics_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️  Error saving metrics: {e}")
    
    def _load_metrics(self):
        """Load metrics from disk (non-blocking, limited)"""
        try:
            if self.metrics_file.exists():
                # Check file size first - skip if too large
                file_size = self.metrics_file.stat().st_size
                if file_size > 10 * 1024 * 1024:  # Skip if > 10MB
                    print(f"[WARN] Metrics file too large ({file_size / 1024 / 1024:.1f}MB), skipping load")
                    return
                
                with open(self.metrics_file, 'r') as f:
                    data = json.load(f)
                    
                    # Load indexing stats (limit to last 50)
                    if "indexing_stats" in data:
                        stats_list = data["indexing_stats"][-50:]  # Only last 50
                        for stats_dict in stats_list:
                            try:
                                self.indexing_stats.append(IndexingStats(**stats_dict))
                            except Exception:
                                pass  # Skip invalid entries
        except Exception as e:
            print(f"[WARN] Error loading metrics: {e}")
    
    def get_model_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics grouped by model/provider.
        
        Returns:
            Dictionary mapping model IDs to their statistics
        """
        with self._lock:
            model_stats = {}
            
            # Collect all API call metrics
            api_calls = [m for m in self.metrics if m.metric_type == "api_call"]
            
            # Group by provider/model
            for call in api_calls:
                provider = call.metadata.get("provider", "unknown")
                model = call.metadata.get("model", "unknown")
                
                # Use provider as model ID (openai, deepseek, anthropic)
                model_id = provider
                
                if model_id not in model_stats:
                    model_stats[model_id] = {
                        "totalRequests": 0,
                        "totalCost": 0.0,
                        "totalTokens": 0,
                        "responseTimes": [],
                        "model": model
                    }
                
                stats = model_stats[model_id]
                stats["totalRequests"] += 1
                stats["totalCost"] += call.value
                stats["totalTokens"] += call.metadata.get("tokens_used", 0)
                
                # Collect response times
                duration = call.metadata.get("duration", 0)
                if duration > 0:
                    stats["responseTimes"].append(duration)
            
            # Calculate averages
            for model_id, stats in model_stats.items():
                if stats["responseTimes"]:
                    stats["avgResponseTime"] = sum(stats["responseTimes"]) / len(stats["responseTimes"])
                    stats["minResponseTime"] = min(stats["responseTimes"])
                    stats["maxResponseTime"] = max(stats["responseTimes"])
                else:
                    stats["avgResponseTime"] = 0.0
                    stats["minResponseTime"] = 0.0
                    stats["maxResponseTime"] = 0.0
                
                # Remove responseTimes array (keep only aggregated stats)
                del stats["responseTimes"]
            
            return model_stats
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all performance metrics.
        Optimized to avoid iterating through all metrics.
        Uses caching to reduce computation.
        
        Returns:
            Dictionary with summary statistics
        """
        # Check cache first (without lock for speed)
        current_time = time.time()
        if (self._summary_cache is not None and 
            current_time - self._summary_cache_time < self._summary_cache_ttl):
            return self._summary_cache
        
        # Cache miss or expired, compute summary
        # Minimize lock time - get data quickly
        with self._lock:
            # Get metrics count and recent metrics only
            metrics_count = len(self.metrics)
            recent_metrics = list(self.metrics)[-200:]  # Only last 200 for speed
            indexing_count = len(self.indexing_stats)
            latest_indexing = self.indexing_stats[-1] if self.indexing_stats else None
        
        # Calculate outside lock to avoid blocking
        total_api_calls = 0
        total_cost = 0.0
        
        # Only check recent metrics (last 200) to avoid slow iteration
        for m in recent_metrics:
            if m.metric_type == "api_call":
                total_api_calls += 1
                if m.value is not None:
                    total_cost += float(m.value)
        
        # If we have more metrics, estimate totals
        if metrics_count > 200:
            ratio = metrics_count / 200.0
            total_api_calls = int(total_api_calls * ratio)
            total_cost = total_cost * ratio
        
        # Get current stats (this will acquire lock internally)
        current_stats = self.get_current_stats()
        
        summary = {
            "current": current_stats,
            "totals": {
                "api_calls": total_api_calls,
                "total_cost_usd": total_cost,
                "indexing_runs": indexing_count
            },
            "latest_indexing": asdict(latest_indexing) if latest_indexing else None
        }
        
        # Update cache (without lock for speed)
        self._summary_cache = summary
        self._summary_cache_time = current_time
        
        return summary
    
    def reset(self):
        """Reset all metrics (use with caution)"""
        with self._lock:
            self.metrics.clear()
            self.response_times.clear()
            self.indexing_stats.clear()
            if self.metrics_file.exists():
                self.metrics_file.unlink()






