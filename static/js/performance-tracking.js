// Real-time Performance Tracking and Analytics

// Performance tracking state
var performanceTracker = {
    sessions: [],
    currentSession: null,
    startTime: null
};

// Start tracking session
function startPerformanceTracking() {
    performanceTracker.currentSession = {
        id: Date.now(),
        startTime: new Date(),
        datesAnalyzed: [],
        totalGamesViewed: 0,
        averageLoadTime: 0,
        loadTimes: [],
        errors: []
    };
    performanceTracker.startTime = performance.now();
    console.log('Performance tracking started');
}

// Track page load performance
function trackLoadPerformance(date, startTime, endTime, gameCount) {
    if (!performanceTracker.currentSession) {
        startPerformanceTracking();
    }
    
    var loadTime = endTime - startTime;
    var session = performanceTracker.currentSession;
    
    session.datesAnalyzed.push({
        date: date,
        loadTime: loadTime,
        gameCount: gameCount,
        timestamp: new Date()
    });
    
    session.loadTimes.push(loadTime);
    session.totalGamesViewed += gameCount;
    session.averageLoadTime = session.loadTimes.reduce(function(a, b) { return a + b; }, 0) / session.loadTimes.length;
    
    console.log('Load tracked:', date, 'in', loadTime.toFixed(2), 'ms');
}

// Track errors
function trackError(error, context) {
    if (!performanceTracker.currentSession) {
        startPerformanceTracking();
    }
    
    performanceTracker.currentSession.errors.push({
        error: error.toString(),
        context: context,
        timestamp: new Date()
    });
    
    console.error('Error tracked:', error, 'in context:', context);
}

// Enhanced load function with performance tracking
function loadHistoricalAnalysisWithTracking() {
    var startTime = performance.now();
    var dateInput = document.getElementById('analysis-date');
    var date = dateInput ? dateInput.value : '';
    
    if (!date) {
        trackError(new Error('No date selected'), 'loadHistoricalAnalysis');
        showError('Please select a date for analysis');
        return;
    }
    
    // Show enhanced loading state
    showLoadingState('Loading historical analysis for ' + date + '...');
    
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/historical-recap/' + encodeURIComponent(date), true);
    
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4) {
            var endTime = performance.now();
            
            if (xhr.status === 200) {
                try {
                    var data = JSON.parse(xhr.responseText);
                    
                    if (data.success && data.games && data.games.length > 0) {
                        trackLoadPerformance(date, startTime, endTime, data.games.length);
                        cacheLoadedData(data); // Cache for export
                        displayEnhancedData(data, date);
                        
                        // Add performance indicator
                        addPerformanceIndicator(endTime - startTime, data.games.length);
                    } else {
                        trackError(new Error('No games found'), 'loadHistoricalAnalysis');
                        tryFallbackEndpoint(date, startTime);
                    }
                } catch (parseError) {
                    trackError(parseError, 'JSON parsing');
                    tryFallbackEndpoint(date, startTime);
                }
            } else {
                trackError(new Error('HTTP ' + xhr.status), 'API request');
                tryFallbackEndpoint(date, startTime);
            }
        }
    };
    
    xhr.onerror = function() {
        var endTime = performance.now();
        trackError(new Error('Network error'), 'API request');
        showError('Network error occurred. Please check your connection.');
    };
    
    xhr.send();
}

// Add performance indicator to the page
function addPerformanceIndicator(loadTime, gameCount) {
    var existing = document.getElementById('performance-indicator');
    if (existing) existing.remove();
    
    var indicator = document.createElement('div');
    indicator.id = 'performance-indicator';
    indicator.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: rgba(0, 0, 0, 0.8);
        color: #4ecdc4;
        padding: 10px;
        border-radius: 5px;
        font-size: 12px;
        z-index: 1000;
        border: 1px solid rgba(78, 205, 196, 0.3);
    `;
    
    var loadTimeColor = loadTime < 1000 ? '#51cf66' : loadTime < 3000 ? '#ffd43b' : '#ff6b6b';
    
    indicator.innerHTML = `
        <div>⚡ Load: <span style="color: ${loadTimeColor}">${loadTime.toFixed(0)}ms</span></div>
        <div>📊 Games: ${gameCount}</div>
        <div>💾 Cached: ✅</div>
    `;
    
    document.body.appendChild(indicator);
    
    // Auto-hide after 3 seconds
    setTimeout(function() {
        if (indicator && indicator.parentNode) {
            indicator.style.opacity = '0';
            indicator.style.transition = 'opacity 0.5s';
            setTimeout(function() {
                if (indicator && indicator.parentNode) {
                    indicator.remove();
                }
            }, 500);
        }
    }, 3000);
}

// Generate performance analytics
function showPerformanceAnalytics() {
    if (!performanceTracker.currentSession || performanceTracker.currentSession.datesAnalyzed.length === 0) {
        alert('No performance data available. Use the system first to generate analytics.');
        return;
    }
    
    var session = performanceTracker.currentSession;
    var avgLoadTime = session.averageLoadTime;
    var totalDates = session.datesAnalyzed.length;
    var totalGames = session.totalGamesViewed;
    var errorCount = session.errors.length;
    
    var fastLoads = session.loadTimes.filter(function(time) { return time < 1000; }).length;
    var slowLoads = session.loadTimes.filter(function(time) { return time > 3000; }).length;
    
    var analyticsText = `Performance Analytics\n` +
        `=====================\n` +
        `Session Duration: ${Math.round((Date.now() - session.startTime.getTime()) / 1000)}s\n` +
        `Dates Analyzed: ${totalDates}\n` +
        `Total Games Viewed: ${totalGames}\n` +
        `Average Load Time: ${avgLoadTime.toFixed(0)}ms\n` +
        `Fast Loads (<1s): ${fastLoads}/${totalDates}\n` +
        `Slow Loads (>3s): ${slowLoads}/${totalDates}\n` +
        `Errors Encountered: ${errorCount}\n` +
        `Games per Analysis: ${(totalGames / totalDates).toFixed(1)}\n\n` +
        `Performance Rating: ${getPerformanceRating(avgLoadTime, errorCount, totalDates)}`;
    
    showModal('Performance Analytics', analyticsText);
}

function getPerformanceRating(avgLoadTime, errorCount, totalAnalyses) {
    var score = 100;
    
    // Deduct for slow load times
    if (avgLoadTime > 3000) score -= 30;
    else if (avgLoadTime > 1500) score -= 15;
    else if (avgLoadTime > 800) score -= 5;
    
    // Deduct for errors
    var errorRate = errorCount / totalAnalyses;
    if (errorRate > 0.2) score -= 25;
    else if (errorRate > 0.1) score -= 15;
    else if (errorRate > 0.05) score -= 5;
    
    if (score >= 95) return '🟢 Excellent';
    if (score >= 85) return '🟡 Good';
    if (score >= 70) return '🟠 Fair';
    return '🔴 Needs Improvement';
}

// Add performance controls
function addPerformanceControls() {
    var navControls = document.querySelector('.nav-controls');
    if (navControls && !document.querySelector('.performance-controls')) {
        var perfControls = document.createElement('div');
        perfControls.className = 'performance-controls';
        perfControls.style.marginTop = '10px';
        perfControls.innerHTML = `
            <div style="display: flex; gap: 10px; flex-wrap: wrap; justify-content: center;">
                <button class="btn secondary" onclick="showPerformanceAnalytics()">📈 Performance</button>
                <button class="btn secondary" onclick="clearPerformanceData()">🗑️ Clear Data</button>
                <button class="btn secondary" onclick="togglePerformanceMode()">⚡ Speed Mode</button>
            </div>
        `;
        navControls.appendChild(perfControls);
    }
}

var speedMode = false;

function togglePerformanceMode() {
    speedMode = !speedMode;
    var button = event.target;
    
    if (speedMode) {
        button.textContent = '⚡ Speed: ON';
        button.style.background = '#51cf66';
        button.style.color = '#000';
        console.log('Speed mode enabled - reduced animations and faster loading');
    } else {
        button.textContent = '⚡ Speed Mode';
        button.style.background = '';
        button.style.color = '';
        console.log('Speed mode disabled');
    }
}

function clearPerformanceData() {
    if (confirm('Clear all performance tracking data?')) {
        performanceTracker.sessions = [];
        performanceTracker.currentSession = null;
        performanceTracker.startTime = null;
        console.log('Performance data cleared');
        alert('Performance data cleared successfully');
    }
}

// Initialize performance tracking
document.addEventListener('DOMContentLoaded', function() {
    startPerformanceTracking();
    
    setTimeout(function() {
        addPerformanceControls();
    }, 1000);
});

// Override the original loadHistoricalAnalysis with tracking
if (typeof loadHistoricalAnalysis === 'function') {
    var originalLoad = loadHistoricalAnalysis;
    loadHistoricalAnalysis = loadHistoricalAnalysisWithTracking;
}

console.log('Performance tracking loaded');
