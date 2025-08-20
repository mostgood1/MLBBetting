"""
Enhanced Monitoring System for MLB Betting Application
Provides comprehensive monitoring, alerts, and performance tracking
"""

import json
import os
import time
import logging
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
try:
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Email functionality not available")
import requests
import threading
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monitoring_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MLBBettingMonitor:
    """Comprehensive monitoring system for MLB betting application"""
    
    def __init__(self, config_file='monitoring_config.json'):
        self.config_file = config_file
        self.config = self.load_config()
        self.performance_history = []
        self.alert_history = []
        self.is_monitoring = False
        self.monitor_thread = None
        
        # Create monitoring directory
        self.monitoring_dir = 'monitoring_data'
        os.makedirs(self.monitoring_dir, exist_ok=True)
        
        logger.info("MLB Betting Monitor initialized")
    
    def load_config(self) -> Dict[str, Any]:
        """Load monitoring configuration"""
        default_config = {
            'monitoring_enabled': True,
            'check_interval': 300,  # 5 minutes
            'api_base_url': 'http://localhost:5000',
            'alerts': {
                'email_enabled': False,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'email_from': '',
                'email_to': [],
                'email_password': ''
            },
            'thresholds': {
                'max_response_time': 5.0,  # seconds
                'min_success_rate': 95.0,  # percentage
                'max_memory_usage': 500,  # MB
                'max_cpu_usage': 80.0,  # percentage
                'prediction_generation_timeout': 30.0  # seconds
            },
            'endpoints_to_monitor': [
                '/api/today-games',
                '/api/daily-predictions',
                '/api/historical-recap/2025-08-19',
                '/admin/api/status',
                '/admin/api/performance-metrics'
            ]
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults for any missing keys
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            else:
                with open(self.config_file, 'w') as f:
                    json.dump(default_config, f, indent=2)
                return default_config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return default_config
    
    def save_config(self):
        """Save current configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def start_monitoring(self):
        """Start the monitoring system"""
        if self.is_monitoring:
            logger.warning("Monitoring already running")
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Monitoring system started")
    
    def stop_monitoring(self):
        """Stop the monitoring system"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Monitoring system stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                # Perform monitoring checks
                self.check_api_health()
                self.check_system_resources()
                self.check_prediction_performance()
                self.check_data_freshness()
                
                # Generate daily report if needed
                self.generate_daily_report_if_needed()
                
                # Sleep until next check
                time.sleep(self.config['check_interval'])
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def check_api_health(self):
        """Check health of key API endpoints"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'endpoint_health': {}
        }
        
        base_url = self.config['api_base_url']
        
        for endpoint in self.config['endpoints_to_monitor']:
            start_time = time.time()
            
            try:
                response = requests.get(f"{base_url}{endpoint}", timeout=10)
                response_time = time.time() - start_time
                
                health_data = {
                    'status_code': response.status_code,
                    'response_time': round(response_time, 3),
                    'success': response.status_code == 200,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Check response time threshold
                if response_time > self.config['thresholds']['max_response_time']:
                    self.send_alert(
                        'Slow API Response',
                        f"Endpoint {endpoint} took {response_time:.2f}s to respond (threshold: {self.config['thresholds']['max_response_time']}s)"
                    )
                
                # Check for errors
                if response.status_code != 200:
                    self.send_alert(
                        'API Error',
                        f"Endpoint {endpoint} returned status code {response.status_code}"
                    )
                
            except requests.exceptions.Timeout:
                health_data = {
                    'status_code': 0,
                    'response_time': None,
                    'success': False,
                    'error': 'Timeout',
                    'timestamp': datetime.now().isoformat()
                }
                self.send_alert('API Timeout', f"Endpoint {endpoint} timed out")
                
            except Exception as e:
                health_data = {
                    'status_code': 0,
                    'response_time': None,
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                self.send_alert('API Error', f"Endpoint {endpoint} error: {str(e)}")
            
            results['endpoint_health'][endpoint] = health_data
        
        # Save results
        self.save_monitoring_data('api_health', results)
        
        # Calculate overall success rate
        successful_checks = sum(1 for health in results['endpoint_health'].values() if health['success'])
        total_checks = len(results['endpoint_health'])
        success_rate = (successful_checks / total_checks) * 100 if total_checks > 0 else 0
        
        if success_rate < self.config['thresholds']['min_success_rate']:
            self.send_alert(
                'Low API Success Rate',
                f"API success rate is {success_rate:.1f}% (threshold: {self.config['thresholds']['min_success_rate']}%)"
            )
    
    def check_system_resources(self):
        """Check system resource usage"""
        try:
            # Get system stats
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            disk_usage = psutil.disk_usage('/')
            
            resource_data = {
                'timestamp': datetime.now().isoformat(),
                'memory': {
                    'total_mb': round(memory.total / 1024 / 1024, 2),
                    'available_mb': round(memory.available / 1024 / 1024, 2),
                    'used_mb': round(memory.used / 1024 / 1024, 2),
                    'percent': memory.percent
                },
                'cpu': {
                    'percent': cpu_percent
                },
                'disk': {
                    'total_gb': round(disk_usage.total / 1024 / 1024 / 1024, 2),
                    'free_gb': round(disk_usage.free / 1024 / 1024 / 1024, 2),
                    'used_gb': round(disk_usage.used / 1024 / 1024 / 1024, 2),
                    'percent': round((disk_usage.used / disk_usage.total) * 100, 1)
                }
            }
            
            # Check thresholds
            if memory.used / 1024 / 1024 > self.config['thresholds']['max_memory_usage']:
                self.send_alert(
                    'High Memory Usage',
                    f"Memory usage: {memory.used / 1024 / 1024:.1f}MB (threshold: {self.config['thresholds']['max_memory_usage']}MB)"
                )
            
            if cpu_percent > self.config['thresholds']['max_cpu_usage']:
                self.send_alert(
                    'High CPU Usage',
                    f"CPU usage: {cpu_percent:.1f}% (threshold: {self.config['thresholds']['max_cpu_usage']}%)"
                )
            
            # Save data
            self.save_monitoring_data('system_resources', resource_data)
            
        except Exception as e:
            logger.error(f"Error checking system resources: {e}")
    
    def check_prediction_performance(self):
        """Check prediction generation performance"""
        try:
            # Check if predictions are being generated daily
            today = datetime.now().strftime('%Y-%m-%d')
            unified_cache_path = 'data/unified_predictions_cache.json'
            
            performance_data = {
                'timestamp': datetime.now().isoformat(),
                'prediction_status': 'unknown',
                'cache_size': 0,
                'last_prediction_date': None,
                'cache_age_hours': None
            }
            
            if os.path.exists(unified_cache_path):
                try:
                    with open(unified_cache_path, 'r') as f:
                        cache_data = json.load(f)
                    
                    performance_data['cache_size'] = len(str(cache_data))
                    
                    # Check for today's predictions
                    predictions_by_date = cache_data.get('predictions_by_date', {})
                    if today in predictions_by_date:
                        performance_data['prediction_status'] = 'current'
                        performance_data['last_prediction_date'] = today
                    else:
                        # Find most recent prediction date
                        dates = [d for d in predictions_by_date.keys() if d.startswith('2025-')]
                        if dates:
                            latest_date = max(dates)
                            performance_data['last_prediction_date'] = latest_date
                            performance_data['prediction_status'] = 'outdated'
                            
                            # Calculate age
                            latest_dt = datetime.strptime(latest_date, '%Y-%m-%d')
                            age_hours = (datetime.now() - latest_dt).total_seconds() / 3600
                            performance_data['cache_age_hours'] = round(age_hours, 1)
                            
                            if age_hours > 36:  # More than 1.5 days old
                                self.send_alert(
                                    'Outdated Predictions',
                                    f"Latest predictions are {age_hours:.1f} hours old (last: {latest_date})"
                                )
                        else:
                            performance_data['prediction_status'] = 'empty'
                            self.send_alert('No Predictions', 'No predictions found in cache')
                    
                    # Check cache file modification time
                    cache_mtime = os.path.getmtime(unified_cache_path)
                    cache_age = time.time() - cache_mtime
                    
                    if cache_age > self.config['thresholds']['prediction_generation_timeout'] * 3600:
                        self.send_alert(
                            'Stale Prediction Cache',
                            f"Prediction cache hasn't been updated in {cache_age/3600:.1f} hours"
                        )
                
                except json.JSONDecodeError:
                    performance_data['prediction_status'] = 'corrupted'
                    self.send_alert('Corrupted Cache', 'Prediction cache file is corrupted')
            
            else:
                performance_data['prediction_status'] = 'missing'
                self.send_alert('Missing Cache', 'Prediction cache file does not exist')
            
            self.save_monitoring_data('prediction_performance', performance_data)
            
        except Exception as e:
            logger.error(f"Error checking prediction performance: {e}")
    
    def check_data_freshness(self):
        """Check freshness of various data sources"""
        try:
            freshness_data = {
                'timestamp': datetime.now().isoformat(),
                'data_sources': {}
            }
            
            # Check key data files
            files_to_check = [
                ('data/unified_predictions_cache.json', 'Predictions'),
                ('data/team_stats_cache.json', 'Team Stats'),
                ('data/betting_lines_cache.json', 'Betting Lines'),
                ('data/current_season_schedule.json', 'Season Schedule')
            ]
            
            for filepath, name in files_to_check:
                if os.path.exists(filepath):
                    mtime = os.path.getmtime(filepath)
                    age_hours = (time.time() - mtime) / 3600
                    
                    freshness_data['data_sources'][name] = {
                        'exists': True,
                        'age_hours': round(age_hours, 1),
                        'last_modified': datetime.fromtimestamp(mtime).isoformat()
                    }
                    
                    # Alert if data is too old
                    if age_hours > 48:  # 2 days
                        self.send_alert(
                            'Stale Data',
                            f"{name} data is {age_hours:.1f} hours old"
                        )
                else:
                    freshness_data['data_sources'][name] = {
                        'exists': False,
                        'age_hours': None,
                        'last_modified': None
                    }
                    self.send_alert('Missing Data', f"{name} file does not exist")
            
            self.save_monitoring_data('data_freshness', freshness_data)
            
        except Exception as e:
            logger.error(f"Error checking data freshness: {e}")
    
    def send_alert(self, alert_type: str, message: str, severity: str = 'warning'):
        """Send an alert notification"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'type': alert_type,
            'message': message,
            'severity': severity
        }
        
        # Add to alert history
        self.alert_history.append(alert)
        
        # Keep only last 100 alerts
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-100:]
        
        logger.warning(f"ALERT [{alert_type}]: {message}")
        
        # Send email if configured
        if self.config['alerts']['email_enabled']:
            self.send_email_alert(alert)
        
        # Save alert to file
        self.save_monitoring_data('alerts', alert)
    
    def send_email_alert(self, alert: Dict[str, Any]):
        """Send email alert"""
        if not EMAIL_AVAILABLE:
            logger.warning("Email functionality not available - cannot send email alert")
            return
            
        try:
            msg = MimeMultipart()
            msg['From'] = self.config['alerts']['email_from']
            msg['To'] = ', '.join(self.config['alerts']['email_to'])
            msg['Subject'] = f"MLB Betting Alert: {alert['type']}"
            
            body = f"""
            Alert Type: {alert['type']}
            Severity: {alert['severity']}
            Time: {alert['timestamp']}
            
            Message: {alert['message']}
            
            ---
            MLB Betting Monitoring System
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(self.config['alerts']['smtp_server'], self.config['alerts']['smtp_port'])
            server.starttls()
            server.login(self.config['alerts']['email_from'], self.config['alerts']['email_password'])
            
            text = msg.as_string()
            server.sendmail(self.config['alerts']['email_from'], self.config['alerts']['email_to'], text)
            server.quit()
            
            logger.info(f"Email alert sent for: {alert['type']}")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def save_monitoring_data(self, data_type: str, data: Any):
        """Save monitoring data to file"""
        try:
            filename = os.path.join(self.monitoring_dir, f"{data_type}_{datetime.now().strftime('%Y%m%d')}.jsonl")
            
            with open(filename, 'a') as f:
                f.write(json.dumps(data) + '\n')
                
        except Exception as e:
            logger.error(f"Error saving monitoring data: {e}")
    
    def generate_daily_report_if_needed(self):
        """Generate daily monitoring report if it's a new day"""
        today = datetime.now().strftime('%Y-%m-%d')
        report_file = os.path.join(self.monitoring_dir, f"daily_report_{today}.json")
        
        if not os.path.exists(report_file):
            self.generate_daily_report(today)
    
    def generate_daily_report(self, date: str = None):
        """Generate comprehensive daily monitoring report"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            report = {
                'date': date,
                'generated_at': datetime.now().isoformat(),
                'summary': {
                    'total_alerts': 0,
                    'critical_alerts': 0,
                    'api_success_rate': 0,
                    'average_response_time': 0,
                    'system_performance': 'good'
                },
                'details': {
                    'alerts': [],
                    'api_health': [],
                    'system_resources': [],
                    'prediction_performance': []
                }
            }
            
            # Load daily monitoring data
            data_files = [
                'alerts', 'api_health', 'system_resources', 
                'prediction_performance', 'data_freshness'
            ]
            
            for data_type in data_files:
                filename = os.path.join(self.monitoring_dir, f"{data_type}_{date.replace('-', '')}.jsonl")
                if os.path.exists(filename):
                    with open(filename, 'r') as f:
                        data_points = [json.loads(line.strip()) for line in f if line.strip()]
                        report['details'][data_type] = data_points
            
            # Calculate summary statistics
            if 'alerts' in report['details']:
                report['summary']['total_alerts'] = len(report['details']['alerts'])
                report['summary']['critical_alerts'] = sum(
                    1 for alert in report['details']['alerts'] 
                    if alert.get('severity') == 'critical'
                )
            
            if 'api_health' in report['details']:
                all_checks = []
                response_times = []
                
                for health_check in report['details']['api_health']:
                    for endpoint, health in health_check.get('endpoint_health', {}).items():
                        all_checks.append(health['success'])
                        if health.get('response_time'):
                            response_times.append(health['response_time'])
                
                if all_checks:
                    report['summary']['api_success_rate'] = round(
                        (sum(all_checks) / len(all_checks)) * 100, 1
                    )
                
                if response_times:
                    report['summary']['average_response_time'] = round(
                        sum(response_times) / len(response_times), 3
                    )
            
            # Save report
            report_file = os.path.join(self.monitoring_dir, f"daily_report_{date}.json")
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Daily monitoring report generated for {date}")
            return report
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current monitoring system status"""
        return {
            'monitoring_active': self.is_monitoring,
            'config_loaded': self.config is not None,
            'recent_alerts': self.alert_history[-10:] if self.alert_history else [],
            'monitoring_since': datetime.now().isoformat() if self.is_monitoring else None
        }


# Global monitor instance
monitor = MLBBettingMonitor()

def start_monitoring():
    """Start the monitoring system"""
    monitor.start_monitoring()

def stop_monitoring():
    """Stop the monitoring system"""
    monitor.stop_monitoring()

def get_monitor_status():
    """Get monitoring status"""
    return monitor.get_status()

def send_test_alert():
    """Send a test alert"""
    monitor.send_alert('Test Alert', 'This is a test alert from the monitoring system', 'info')

if __name__ == '__main__':
    # For testing
    print("Starting MLB Betting Monitoring System...")
    monitor.start_monitoring()
    
    try:
        # Keep running
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Stopping monitoring...")
        monitor.stop_monitoring()
