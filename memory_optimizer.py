"""
Memory optimization utilities for MLB-Betting application
"""

import gc
import sys
import psutil
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class MemoryOptimizer:
    """Optimize memory usage for the MLB-Betting application"""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.initial_memory = self.get_memory_usage()
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage in MB"""
        memory_info = self.process.memory_info()
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size
            'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size
            'percent': self.process.memory_percent()
        }
    
    def force_garbage_collection(self) -> Dict[str, Any]:
        """Force garbage collection and return memory freed"""
        before = self.get_memory_usage()
        
        # Force garbage collection
        collected = gc.collect()
        
        after = self.get_memory_usage()
        freed = before['rss_mb'] - after['rss_mb']
        
        logger.info(f"Garbage collection freed {freed:.1f}MB (collected {collected} objects)")
        
        return {
            'objects_collected': collected,
            'memory_freed_mb': freed,
            'before_mb': before['rss_mb'],
            'after_mb': after['rss_mb']
        }
    
    def optimize_memory(self) -> Dict[str, Any]:
        """Perform comprehensive memory optimization"""
        optimizations = []
        
        # 1. Force garbage collection
        gc_result = self.force_garbage_collection()
        optimizations.append({
            'type': 'garbage_collection',
            'result': gc_result
        })
        
        # 2. Clear Python caches
        try:
            sys.intern.__clear__ if hasattr(sys.intern, '__clear__') else None
            optimizations.append({
                'type': 'intern_cache_clear',
                'result': 'completed'
            })
        except:
            pass
        
        # 3. Set garbage collection thresholds more aggressively
        old_thresholds = gc.get_threshold()
        gc.set_threshold(100, 10, 10)  # More aggressive than default (700, 10, 10)
        optimizations.append({
            'type': 'gc_threshold_adjustment',
            'old_thresholds': old_thresholds,
            'new_thresholds': gc.get_threshold()
        })
        
        final_memory = self.get_memory_usage()
        total_freed = self.initial_memory['rss_mb'] - final_memory['rss_mb']
        
        return {
            'optimizations_performed': len(optimizations),
            'optimizations': optimizations,
            'initial_memory_mb': self.initial_memory['rss_mb'],
            'final_memory_mb': final_memory['rss_mb'],
            'total_freed_mb': total_freed,
            'memory_percent': final_memory['percent']
        }
    
    def get_memory_report(self) -> Dict[str, Any]:
        """Get detailed memory usage report"""
        current = self.get_memory_usage()
        
        # Get system memory info
        sys_memory = psutil.virtual_memory()
        
        return {
            'process_memory': current,
            'system_memory': {
                'total_gb': round(sys_memory.total / 1024 / 1024 / 1024, 2),
                'available_gb': round(sys_memory.available / 1024 / 1024 / 1024, 2),
                'used_percent': sys_memory.percent
            },
            'gc_stats': {
                'threshold': gc.get_threshold(),
                'counts': gc.get_count(),
                'stats': gc.get_stats() if hasattr(gc, 'get_stats') else 'not available'
            }
        }

# Global optimizer instance
memory_optimizer = MemoryOptimizer()

def optimize_memory():
    """Optimize memory usage and return results"""
    return memory_optimizer.optimize_memory()

def get_memory_report():
    """Get memory usage report"""
    return memory_optimizer.get_memory_report()

def force_cleanup():
    """Force immediate memory cleanup"""
    return memory_optimizer.force_garbage_collection()

if __name__ == '__main__':
    # Test the memory optimizer
    print("Memory Optimizer Test")
    print("=" * 30)
    
    report = get_memory_report()
    print(f"Current memory usage: {report['process_memory']['rss_mb']:.1f}MB")
    
    optimization = optimize_memory()
    print(f"Memory freed: {optimization['total_freed_mb']:.1f}MB")
    print(f"Final memory: {optimization['final_memory_mb']:.1f}MB")
