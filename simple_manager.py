"""
Simple MLB System Manager
Lightweight process manager for both Flask apps
"""

import subprocess
import time
import sys
import os
from concurrent.futures import ThreadPoolExecutor

class SimpleMLBManager:
    def __init__(self):
        self.processes = {}
    
    def start_service(self, script_name, service_name):
        """Start a service and return the process"""
        try:
            print(f"Starting {service_name}...")
            process = subprocess.Popen([
                sys.executable, script_name
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            self.processes[service_name] = process
            print(f"✅ {service_name} started (PID: {process.pid})")
            return process
        except Exception as e:
            print(f"❌ Failed to start {service_name}: {e}")
            return None
    
    def run(self):
        print("🏟️ Simple MLB System Manager")
        print("=" * 40)
        
        # Start both services
        main_app = self.start_service('app.py', 'Main App')
        time.sleep(2)  # Give main app a moment to start
        historical_app = self.start_service('historical_analysis_app.py', 'Historical App')
        
        if main_app and historical_app:
            print("\n🎉 Both services started!")
            print("📍 Main App: http://localhost:5000")
            print("📍 Historical: http://localhost:5001")
            print("\n💡 Press Ctrl+C to stop")
            
            try:
                # Keep running until interrupted
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Stopping services...")
                for name, process in self.processes.items():
                    process.terminate()
                    print(f"✅ {name} stopped")
                print("🏁 Done")

if __name__ == '__main__':
    manager = SimpleMLBManager()
    manager.run()
