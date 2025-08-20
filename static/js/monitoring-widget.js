/**
 * MLB Betting Monitoring Widget
 * Real-time system health indicator for the main dashboard
 */

class MonitoringWidget {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.isVisible = false;
        this.lastStatus = null;
        this.init();
    }

    init() {
        this.createWidget();
        this.startMonitoring();
    }

    createWidget() {
        this.container.innerHTML = `
            <div id="monitoring-widget" class="monitoring-widget hidden">
                <div class="widget-header">
                    <span class="widget-title">🏟️ System Health</span>
                    <button class="widget-toggle" onclick="monitoringWidget.toggle()">−</button>
                </div>
                <div class="widget-content">
                    <div class="status-row">
                        <div class="status-indicator">
                            <div class="status-dot" id="widget-status-dot"></div>
                            <span id="widget-status-text">Checking...</span>
                        </div>
                        <div class="quick-actions">
                            <button class="btn-mini" onclick="monitoringWidget.openDashboard()">📊</button>
                            <button class="btn-mini" onclick="monitoringWidget.refresh()">🔄</button>
                        </div>
                    </div>
                    <div class="metrics-row" id="widget-metrics">
                        <div class="metric-item">
                            <span class="metric-label">Memory:</span>
                            <span class="metric-value" id="widget-memory">--</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">Cache:</span>
                            <span class="metric-value" id="widget-cache">--</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">API:</span>
                            <span class="metric-value" id="widget-api">--</span>
                        </div>
                    </div>
                    <div class="alerts-row" id="widget-alerts" style="display: none;">
                        <div class="alert-text" id="widget-alert-text"></div>
                    </div>
                </div>
            </div>
        `;

        this.addStyles();
    }

    addStyles() {
        if (document.getElementById('monitoring-widget-styles')) return;

        const styles = document.createElement('style');
        styles.id = 'monitoring-widget-styles';
        styles.textContent = `
            .monitoring-widget {
                position: fixed;
                top: 20px;
                right: 20px;
                width: 300px;
                background: rgba(0, 0, 0, 0.9);
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                color: white;
                font-size: 14px;
                font-family: 'Segoe UI', sans-serif;
                z-index: 1000;
                backdrop-filter: blur(10px);
                box-shadow: 0 5px 20px rgba(0, 0, 0, 0.5);
                transition: all 0.3s ease;
            }

            .monitoring-widget.hidden {
                transform: translateX(320px);
            }

            .monitoring-widget.collapsed .widget-content {
                display: none;
            }

            .widget-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px 15px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                cursor: pointer;
            }

            .widget-title {
                font-weight: 600;
                font-size: 13px;
            }

            .widget-toggle {
                background: none;
                border: none;
                color: white;
                font-size: 16px;
                cursor: pointer;
                padding: 0;
                width: 20px;
                height: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .widget-content {
                padding: 12px 15px;
            }

            .status-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }

            .status-indicator {
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .status-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                animation: pulse 2s infinite;
            }

            .status-dot.online {
                background: #00ff88;
            }

            .status-dot.warning {
                background: #ffaa00;
            }

            .status-dot.offline {
                background: #ff4444;
            }

            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.5; }
                100% { opacity: 1; }
            }

            .quick-actions {
                display: flex;
                gap: 5px;
            }

            .btn-mini {
                background: rgba(255, 255, 255, 0.1);
                border: none;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                cursor: pointer;
                transition: background 0.2s ease;
            }

            .btn-mini:hover {
                background: rgba(255, 255, 255, 0.2);
            }

            .metrics-row {
                display: flex;
                justify-content: space-between;
                gap: 10px;
                margin-bottom: 8px;
            }

            .metric-item {
                display: flex;
                flex-direction: column;
                align-items: center;
                flex: 1;
            }

            .metric-label {
                font-size: 11px;
                opacity: 0.7;
                margin-bottom: 2px;
            }

            .metric-value {
                font-size: 12px;
                font-weight: 600;
                padding: 2px 6px;
                border-radius: 8px;
                background: rgba(255, 255, 255, 0.1);
                min-width: 40px;
                text-align: center;
            }

            .metric-value.success {
                background: rgba(0, 255, 136, 0.2);
                color: #00ff88;
            }

            .metric-value.warning {
                background: rgba(255, 170, 0, 0.2);
                color: #ffaa00;
            }

            .metric-value.error {
                background: rgba(255, 68, 68, 0.2);
                color: #ff4444;
            }

            .alerts-row {
                padding: 8px 12px;
                background: rgba(255, 170, 0, 0.1);
                border-radius: 5px;
                border-left: 3px solid #ffaa00;
                margin-top: 8px;
            }

            .alert-text {
                font-size: 12px;
                line-height: 1.3;
            }

            /* Show widget on hover even when hidden */
            .monitoring-widget.hidden:hover {
                transform: translateX(280px);
            }

            /* Mobile responsiveness */
            @media (max-width: 768px) {
                .monitoring-widget {
                    width: 280px;
                    top: 10px;
                    right: 10px;
                }
                
                .monitoring-widget.hidden {
                    transform: translateX(300px);
                }
            }
        `;
        document.head.appendChild(styles);
    }

    async startMonitoring() {
        // Initial load
        await this.checkStatus();
        
        // Show widget with a delay
        setTimeout(() => {
            this.show();
        }, 2000);

        // Regular updates every 60 seconds
        setInterval(() => {
            this.checkStatus();
        }, 60000);
    }

    async checkStatus() {
        try {
            const response = await fetch('/api/monitoring/performance');
            const data = await response.json();

            if (data.success) {
                this.updateWidget(data.metrics);
            } else {
                this.updateWidget(null, 'Error loading status');
            }
        } catch (error) {
            console.error('Widget monitoring error:', error);
            this.updateWidget(null, 'Connection error');
        }
    }

    updateWidget(metrics, error = null) {
        const statusDot = document.getElementById('widget-status-dot');
        const statusText = document.getElementById('widget-status-text');
        const memoryValue = document.getElementById('widget-memory');
        const cacheValue = document.getElementById('widget-cache');
        const apiValue = document.getElementById('widget-api');
        const alertsRow = document.getElementById('widget-alerts');
        const alertText = document.getElementById('widget-alert-text');

        if (error) {
            statusDot.className = 'status-dot offline';
            statusText.textContent = error;
            memoryValue.textContent = '--';
            cacheValue.textContent = '--';
            apiValue.textContent = '--';
            return;
        }

        if (!metrics) {
            statusDot.className = 'status-dot warning';
            statusText.textContent = 'No data';
            return;
        }

        // System status
        const health = metrics.system_health || 'unknown';
        statusDot.className = `status-dot ${health === 'healthy' ? 'online' : 'warning'}`;
        statusText.textContent = health === 'healthy' ? 'System Healthy' : 'Issues Detected';

        // Memory
        const memory = metrics.memory;
        if (memory && memory.process_memory_mb) {
            const memMB = memory.process_memory_mb;
            memoryValue.textContent = `${memMB.toFixed(0)}MB`;
            memoryValue.className = `metric-value ${memMB > 1000 ? 'error' : memMB > 500 ? 'warning' : 'success'}`;
        } else {
            memoryValue.textContent = 'N/A';
            memoryValue.className = 'metric-value';
        }

        // Cache status
        const cache = metrics.cache;
        if (cache && cache.health) {
            const status = cache.health;
            const sizeKb = cache.size_kb || 0;
            cacheValue.textContent = status === 'good' ? `${sizeKb.toFixed(1)}KB` : 'ERROR';
            cacheValue.className = `metric-value ${status === 'good' ? 'success' : 'error'}`;
        } else {
            cacheValue.textContent = 'N/A';
            cacheValue.className = 'metric-value';
        }

        // API status
        const api = metrics.api;
        if (api && api.health) {
            const health = api.health;
            const responseTime = api.response_time_ms || 0;
            apiValue.textContent = health === 'good' ? `${responseTime}ms` : 'ERROR';
            apiValue.className = `metric-value ${health === 'good' ? 'success' : 'error'}`;
        } else {
            apiValue.textContent = 'N/A';
            apiValue.className = 'metric-value';
        }

        // Check for alerts
        const hasIssues = health !== 'healthy' || 
                         (memory && memory.process_memory_mb > 1000) || 
                         (cache && cache.health !== 'good') || 
                         (api && api.health !== 'good');

        if (hasIssues) {
            let alertMessage = 'Performance issues detected. ';
            if (memory && memory.process_memory_mb > 1000) alertMessage += 'High memory usage. ';
            if (cache && cache.health !== 'good') alertMessage += 'Cache issues. ';
            if (api && api.health !== 'good') alertMessage += 'API errors. ';
            
            alertText.textContent = alertMessage;
            alertsRow.style.display = 'block';
        } else {
            alertsRow.style.display = 'none';
        }

        this.lastStatus = metrics;
    }

    show() {
        const widget = document.getElementById('monitoring-widget');
        widget.classList.remove('hidden');
        this.isVisible = true;
    }

    hide() {
        const widget = document.getElementById('monitoring-widget');
        widget.classList.add('hidden');
        this.isVisible = false;
    }

    toggle() {
        const widget = document.getElementById('monitoring-widget');
        widget.classList.toggle('collapsed');
        
        const toggleBtn = widget.querySelector('.widget-toggle');
        const isCollapsed = widget.classList.contains('collapsed');
        toggleBtn.textContent = isCollapsed ? '+' : '−';
    }

    openDashboard() {
        window.open('/monitoring', '_blank');
    }

    refresh() {
        this.checkStatus();
    }
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Create container if it doesn't exist
    if (!document.getElementById('monitoring-widget-container')) {
        const container = document.createElement('div');
        container.id = 'monitoring-widget-container';
        document.body.appendChild(container);
    }
    
    // Initialize widget
    window.monitoringWidget = new MonitoringWidget('monitoring-widget-container');
});
