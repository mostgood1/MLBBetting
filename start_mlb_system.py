#!/usr/bin/env python3
"""
MLB Betting System Launcher
Starts both the main prediction app and historical analysis app simultaneously
"""

import os
import sys
import time
import subprocess
import threading
import signal
from pathlib import Path

class MLBSystemLauncher:
    def __init__(self):
        self.processes = []
        self.running = True
        
    def start_app(self, script_name, port, app_name):
        """Start a Flask app in a separate process"""
        try:
            print(f"🚀 Starting {app_name} on port {port}...")
            
            # Set environment variables for the app
            env = os.environ.copy()
            env['FLASK_ENV'] = 'development'
            env['FLASK_DEBUG'] = '1'
            
            # Start the process
            process = subprocess.Popen(
                [sys.executable, script_name],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            self.processes.append({
                'process': process,
                'name': app_name,
                'port': port,
                'script': script_name
            })
            
            # Start a thread to monitor the output
            monitor_thread = threading.Thread(
                target=self.monitor_process,
                args=(process, app_name),
                daemon=True
            )
            monitor_thread.start()
            
            print(f"✅ {app_name} started successfully (PID: {process.pid})")
            return process
            
        except Exception as e:
            print(f"❌ Failed to start {app_name}: {e}")
            return None
    
    def monitor_process(self, process, app_name):
        """Monitor process output and display it with prefixes"""
        try:
            for line in iter(process.stdout.readline, ''):
                if self.running and line.strip():
                    print(f"[{app_name}] {line.strip()}")
        except Exception as e:
            if self.running:
                print(f"❌ Error monitoring {app_name}: {e}")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print("\n🛑 Shutdown signal received. Stopping all services...")
        self.shutdown()
    
    def shutdown(self):
        """Gracefully shutdown all processes"""
        self.running = False
        
        for app_info in self.processes:
            process = app_info['process']
            app_name = app_info['name']
            
            if process.poll() is None:  # Process is still running
                print(f"🔄 Stopping {app_name}...")
                try:
                    process.terminate()
                    process.wait(timeout=5)
                    print(f"✅ {app_name} stopped")
                except subprocess.TimeoutExpired:
                    print(f"⚠️ Force killing {app_name}...")
                    process.kill()
                    process.wait()
                except Exception as e:
                    print(f"❌ Error stopping {app_name}: {e}")
        
        print("🏁 All services stopped")
        sys.exit(0)
    
    def wait_for_startup(self, port, max_attempts=30):
        """Wait for a service to be ready"""
        import socket
        
        for attempt in range(max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1)
                    result = sock.connect_ex(('localhost', port))
                    if result == 0:
                        return True
            except:
                pass
            
            time.sleep(1)
        
        return False
    
    def run(self):
        """Main launcher function"""
        print("🏟️ MLB Betting System Launcher")
        print("=" * 50)
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Check if required files exist
        required_files = ['app.py', 'historical_analysis_app.py']
        for file in required_files:
            if not Path(file).exists():
                print(f"❌ Required file not found: {file}")
                return False
        
        # Start the main prediction app (port 5000)
        main_process = self.start_app(
            'app.py', 
            5000, 
            'Main Prediction App'
        )
        
        if not main_process:
            print("❌ Failed to start main app. Exiting.")
            return False
        
        # Wait a moment for main app to initialize
        time.sleep(3)
        
        # Start the historical analysis app (port 5001)
        historical_process = self.start_app(
            'historical_analysis_app.py',
            5001,
            'Historical Analysis App'
        )
        
        if not historical_process:
            print("❌ Failed to start historical analysis app.")
            self.shutdown()
            return False
        
        # Wait for both services to be ready
        print("\n⏳ Waiting for services to be ready...")
        
        main_ready = self.wait_for_startup(5000)
        historical_ready = self.wait_for_startup(5001)
        
        if main_ready and historical_ready:
            print("\n🎉 Both services are ready!")
            print("📍 Main Prediction App: http://localhost:5000")
            print("📍 Historical Analysis: http://localhost:5001")
            print("📊 Full System Access: http://localhost:5000/historical-analysis")
            print("\n💡 Press Ctrl+C to stop both services")
            
            # Keep the launcher running
            try:
                while self.running:
                    time.sleep(1)
                    
                    # Check if any process has died
                    for app_info in self.processes:
                        if app_info['process'].poll() is not None:
                            print(f"⚠️ {app_info['name']} has stopped unexpectedly")
                            self.shutdown()
                            return False
                            
            except KeyboardInterrupt:
                self.signal_handler(signal.SIGINT, None)
        else:
            print("❌ One or more services failed to start properly")
            self.shutdown()
            return False

if __name__ == '__main__':
    launcher = MLBSystemLauncher()
    success = launcher.run()
    sys.exit(0 if success else 1)
