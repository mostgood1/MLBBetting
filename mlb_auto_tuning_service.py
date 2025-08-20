"""
MLB Auto-Tuning Windows Service
Runs continuously in the background, optimizing based on real game results
"""

import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import time
import logging
from datetime import datetime

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auto_tuning_scheduler import AutoTuningScheduler

class MLBAutoTuningService(win32serviceutil.ServiceFramework):
    _svc_name_ = "MLBAutoTuningService"
    _svc_display_name_ = "MLB Prediction Engine Auto-Tuning Service"
    _svc_description_ = "Continuously optimizes MLB prediction engine based on real game results"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.is_alive = True
        
        # Setup logging for the service
        self.setup_service_logging()
        
    def setup_service_logging(self):
        """Setup logging specifically for the Windows service"""
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'service.log')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path),
            ]
        )
        self.logger = logging.getLogger('MLBAutoTuningService')

    def SvcStop(self):
        """Stop the service"""
        self.logger.info("SERVICE: Stop signal received")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.is_alive = False

    def SvcDoRun(self):
        """Main service loop"""
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        
        self.logger.info("SERVICE: MLB Auto-Tuning Service started")
        self.main()

    def main(self):
        """Main service logic"""
        try:
            scheduler = AutoTuningScheduler()
            self.logger.info("SERVICE: Auto-tuning scheduler initialized")
            
            # Setup the schedule but don't run the blocking scheduler
            scheduler.setup_daily_schedule()
            self.logger.info("SERVICE: Daily schedule configured")
            
            # Run an initial performance check
            scheduler.performance_check()
            
            # Main service loop
            while self.is_alive:
                # Check for scheduled tasks every minute
                import schedule
                schedule.run_pending()
                
                # Check if we should stop
                rc = win32event.WaitForSingleObject(self.hWaitStop, 60000)  # 60 seconds
                if rc == win32event.WAIT_OBJECT_0:
                    # Stop event was signaled
                    self.logger.info("SERVICE: Stop event received")
                    break
                    
        except Exception as e:
            self.logger.error(f"SERVICE: Error in main loop: {e}")
            servicemanager.LogErrorMsg(f"MLB Auto-Tuning Service error: {e}")

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(MLBAutoTuningService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(MLBAutoTuningService)
