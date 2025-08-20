"""
Performance Timing Decorator and Utilities
Adds timing metrics to key MLB betting functions for monitoring
"""

import time
import logging
import functools
from datetime import datetime
from typing import Dict, Any, Callable
import json
import os

logger = logging.getLogger(__name__)

class PerformanceTracker:
    """Track performance metrics for key functions"""
    
    def __init__(self):
        self.metrics = {}
        self.metrics_file = 'performance_metrics.json'
    
    def track_timing(self, function_name: str = None):
        """Decorator to track function execution time"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                func_name = function_name or f"{func.__module__}.{func.__name__}"
                
                try:
                    result = func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    self._record_metric(func_name, execution_time, True)
                    
                    # Log slow functions
                    if execution_time > 5.0:
                        logger.warning(f"⚠️ Slow function detected: {func_name} took {execution_time:.2f}s")
                    elif execution_time > 2.0:
                        logger.info(f"📊 Function timing: {func_name} took {execution_time:.2f}s")
                    
                    return result
                    
                except Exception as e:
                    execution_time = time.time() - start_time
                    self._record_metric(func_name, execution_time, False, str(e))
                    raise
                    
            return wrapper
        return decorator
    
    def _record_metric(self, function_name: str, execution_time: float, success: bool, error: str = None):
        """Record performance metric"""
        metric = {
            'timestamp': datetime.now().isoformat(),
            'function': function_name,
            'execution_time': round(execution_time, 3),
            'success': success,
            'error': error
        }
        
        # Add to in-memory metrics
        if function_name not in self.metrics:
            self.metrics[function_name] = []
        
        self.metrics[function_name].append(metric)
        
        # Keep only last 100 metrics per function
        if len(self.metrics[function_name]) > 100:
            self.metrics[function_name] = self.metrics[function_name][-100:]
        
        # Save to file periodically
        self._save_metrics()
    
    def _save_metrics(self):
        """Save metrics to file"""
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump(self.metrics, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving performance metrics: {e}")
    
    def get_summary(self, function_name: str = None) -> Dict[str, Any]:
        """Get performance summary for a function or all functions"""
        if function_name:
            metrics = self.metrics.get(function_name, [])
        else:
            metrics = []
            for func_metrics in self.metrics.values():
                metrics.extend(func_metrics)
        
        if not metrics:
            return {'error': 'No metrics found'}
        
        # Calculate statistics
        execution_times = [m['execution_time'] for m in metrics if m['success']]
        success_count = sum(1 for m in metrics if m['success'])
        total_count = len(metrics)
        
        if execution_times:
            avg_time = sum(execution_times) / len(execution_times)
            min_time = min(execution_times)
            max_time = max(execution_times)
        else:
            avg_time = min_time = max_time = 0
        
        return {
            'function': function_name or 'ALL',
            'total_calls': total_count,
            'successful_calls': success_count,
            'success_rate': round((success_count / total_count) * 100, 1) if total_count > 0 else 0,
            'average_time': round(avg_time, 3),
            'min_time': round(min_time, 3),
            'max_time': round(max_time, 3),
            'recent_metrics': metrics[-10:] if metrics else []
        }
    
    def get_slow_functions(self, threshold: float = 2.0) -> Dict[str, Any]:
        """Get functions that are consistently slow"""
        slow_functions = {}
        
        for func_name, metrics in self.metrics.items():
            recent_metrics = [m for m in metrics[-20:] if m['success']]  # Last 20 successful calls
            
            if len(recent_metrics) >= 5:  # Need at least 5 samples
                avg_time = sum(m['execution_time'] for m in recent_metrics) / len(recent_metrics)
                
                if avg_time > threshold:
                    slow_functions[func_name] = {
                        'average_time': round(avg_time, 3),
                        'sample_count': len(recent_metrics),
                        'slowest_call': max(m['execution_time'] for m in recent_metrics)
                    }
        
        return slow_functions

# Global performance tracker instance
performance_tracker = PerformanceTracker()

# Convenience functions
def track_timing(function_name: str = None):
    """Decorator to track function timing"""
    return performance_tracker.track_timing(function_name)

def get_performance_summary(function_name: str = None):
    """Get performance summary"""
    return performance_tracker.get_summary(function_name)

def get_slow_functions(threshold: float = 2.0):
    """Get slow functions"""
    return performance_tracker.get_slow_functions(threshold)

# Context manager for manual timing
class TimingContext:
    """Context manager for timing code blocks"""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        execution_time = time.time() - self.start_time
        
        if exc_type is None:
            performance_tracker._record_metric(self.operation_name, execution_time, True)
        else:
            performance_tracker._record_metric(self.operation_name, execution_time, False, str(exc_val))
        
        logger.info(f"⏱️ {self.operation_name}: {execution_time:.3f}s")

def time_operation(operation_name: str):
    """Create a timing context manager"""
    return TimingContext(operation_name)
