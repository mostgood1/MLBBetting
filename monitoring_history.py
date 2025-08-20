"""
Memory and Performance History Tracker
Stores real monitoring data for chart visualization
"""

import json
import os
from datetime import datetime, timedelta
from collections import deque
import threading
import time

class MonitoringHistoryTracker:
    def __init__(self, max_points=50):
        self.max_points = max_points
        self.memory_history = deque(maxlen=max_points)
        self.performance_history = deque(maxlen=max_points)
        self.history_file = 'monitoring_history.json'
        self.lock = threading.Lock()
        self.load_history()
        
    def load_history(self):
        """Load historical data from file"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    
                # Convert back to deque and limit size
                self.memory_history = deque(data.get('memory_history', []), maxlen=self.max_points)
                self.performance_history = deque(data.get('performance_history', []), maxlen=self.max_points)
                print(f"✅ Loaded monitoring history: {len(self.memory_history)} memory points, {len(self.performance_history)} performance points")
        except Exception as e:
            print(f"⚠️  Could not load monitoring history: {e}")
            self.memory_history = deque(maxlen=self.max_points)
            self.performance_history = deque(maxlen=self.max_points)
    
    def save_history(self):
        """Save historical data to file"""
        try:
            with self.lock:
                data = {
                    'memory_history': list(self.memory_history),
                    'performance_history': list(self.performance_history),
                    'last_updated': datetime.now().isoformat()
                }
                
                with open(self.history_file, 'w') as f:
                    json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️  Could not save monitoring history: {e}")
    
    def add_memory_data(self, process_memory_mb, system_memory_percent):
        """Add a memory data point"""
        timestamp = datetime.now()
        data_point = {
            'timestamp': timestamp.isoformat(),
            'display_time': timestamp.strftime('%H:%M:%S'),
            'process_memory_mb': round(process_memory_mb, 1),
            'system_memory_percent': round(system_memory_percent, 1)
        }
        
        with self.lock:
            self.memory_history.append(data_point)
            self.save_history()
    
    def add_performance_data(self, response_time, success_rate):
        """Add a performance data point"""
        timestamp = datetime.now()
        data_point = {
            'timestamp': timestamp.isoformat(),
            'display_time': timestamp.strftime('%H:%M:%S'),
            'response_time': round(response_time, 3),
            'success_rate': round(success_rate, 1)
        }
        
        with self.lock:
            self.performance_history.append(data_point)
            self.save_history()
    
    def get_memory_history(self):
        """Get memory history for charts"""
        with self.lock:
            return list(self.memory_history)
    
    def get_performance_history(self):
        """Get performance history for charts"""
        with self.lock:
            return list(self.performance_history)
    
    def get_combined_history(self):
        """Get both memory and performance history"""
        return {
            'memory': self.get_memory_history(),
            'performance': self.get_performance_history()
        }
    
    def cleanup_old_data(self, hours_to_keep=24):
        """Remove data older than specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours_to_keep)
        
        with self.lock:
            # Filter memory history
            self.memory_history = deque([
                point for point in self.memory_history
                if datetime.fromisoformat(point['timestamp']) > cutoff_time
            ], maxlen=self.max_points)
            
            # Filter performance history
            self.performance_history = deque([
                point for point in self.performance_history
                if datetime.fromisoformat(point['timestamp']) > cutoff_time
            ], maxlen=self.max_points)
            
            self.save_history()
    
    def get_stats(self):
        """Get basic statistics about stored data"""
        with self.lock:
            memory_count = len(self.memory_history)
            performance_count = len(self.performance_history)
            
            stats = {
                'memory_points': memory_count,
                'performance_points': performance_count,
                'oldest_memory': None,
                'oldest_performance': None,
                'latest_memory': None,
                'latest_performance': None
            }
            
            if memory_count > 0:
                stats['oldest_memory'] = self.memory_history[0]['timestamp']
                stats['latest_memory'] = self.memory_history[-1]['timestamp']
            
            if performance_count > 0:
                stats['oldest_performance'] = self.performance_history[0]['timestamp']
                stats['latest_performance'] = self.performance_history[-1]['timestamp']
            
            return stats

# Global instance
history_tracker = MonitoringHistoryTracker()

def start_background_collection():
    """Start background thread to collect monitoring data"""
    def collect_data():
        while True:
            try:
                # This would be called by the monitoring system
                # For now, we'll integrate it into the monitoring system
                time.sleep(60)  # Collect every minute
            except Exception as e:
                print(f"Error in background collection: {e}")
                time.sleep(60)
    
    thread = threading.Thread(target=collect_data, daemon=True)
    thread.start()
    print("✅ Started background monitoring data collection")

if __name__ == "__main__":
    # Test the history tracker
    import random
    
    tracker = MonitoringHistoryTracker()
    
    # Add some test data
    for i in range(10):
        memory_mb = 80 + random.uniform(-20, 40)
        system_percent = 45 + random.uniform(-10, 20)
        response_time = 0.8 + random.uniform(-0.3, 0.7)
        success_rate = 95 + random.uniform(-10, 5)
        
        tracker.add_memory_data(memory_mb, system_percent)
        tracker.add_performance_data(response_time, success_rate)
        time.sleep(0.1)
    
    print("Memory history:", len(tracker.get_memory_history()))
    print("Performance history:", len(tracker.get_performance_history()))
    print("Stats:", tracker.get_stats())
