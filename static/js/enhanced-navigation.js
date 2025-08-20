// Enhanced Historical Navigation Features
// Add to the existing historical.html functionality

// Add date range navigation
function addDateRangeNavigation() {
    var navControls = document.querySelector('.date-controls');
    if (navControls) {
        // Add date range controls
        var rangeControls = document.createElement('div');
        rangeControls.className = 'date-range-controls';
        rangeControls.style.marginTop = '10px';
        rangeControls.innerHTML = `
            <button class="btn secondary" onclick="navigateDate(-7)">← 1 Week</button>
            <button class="btn secondary" onclick="navigateDate(-1)">← 1 Day</button>
            <button class="btn secondary" onclick="navigateDate(1)">1 Day →</button>
            <button class="btn secondary" onclick="navigateDate(7)">1 Week →</button>
        `;
        navControls.appendChild(rangeControls);
    }
}

// Navigate by days
function navigateDate(days) {
    var dateInput = document.getElementById('analysis-date');
    if (dateInput && dateInput.value) {
        var currentDate = new Date(dateInput.value + 'T00:00:00');
        currentDate.setDate(currentDate.getDate() + days);
        
        var year = currentDate.getFullYear();
        var month = (currentDate.getMonth() + 1).toString();
        if (month.length === 1) month = '0' + month;
        var day = currentDate.getDate().toString();
        if (day.length === 1) day = '0' + day;
        var newDateString = year + '-' + month + '-' + day;
        
        dateInput.value = newDateString;
        loadHistoricalAnalysis();
    }
}

// Quick date presets
function addQuickDatePresets() {
    var navControls = document.querySelector('.nav-controls');
    if (navControls) {
        var presetControls = document.createElement('div');
        presetControls.className = 'preset-controls';
        presetControls.style.display = 'flex';
        presetControls.style.gap = '10px';
        presetControls.style.flexWrap = 'wrap';
        presetControls.innerHTML = `
            <button class="btn secondary" onclick="loadPresetDate('2025-08-13')">Aug 13</button>
            <button class="btn secondary" onclick="loadPresetDate('2025-08-12')">Aug 12</button>
            <button class="btn secondary" onclick="loadPresetDate('2025-08-11')">Aug 11</button>
            <button class="btn secondary" onclick="loadPresetDate('2025-08-10')">Aug 10</button>
            <button class="btn secondary" onclick="loadPresetDate('2025-08-09')">Aug 9</button>
            <button class="btn secondary" onclick="loadPresetDate('2025-08-08')">Aug 8</button>
            <button class="btn secondary" onclick="loadPresetDate('2025-08-07')">Aug 7</button>
        `;
        navControls.appendChild(presetControls);
    }
}

function loadPresetDate(dateString) {
    var dateInput = document.getElementById('analysis-date');
    if (dateInput) {
        dateInput.value = dateString;
        loadHistoricalAnalysis();
    }
}

// Enhanced loading states
function showLoadingState(message) {
    var container = document.getElementById('games-container');
    if (container) {
        container.innerHTML = `
            <div class="loading-enhanced">
                <div class="loading-spinner"></div>
                <div class="loading-text">${message || 'Loading historical analysis...'}</div>
                <div class="loading-subtext">This may take a moment...</div>
            </div>
        `;
    }
}

// Add loading styles
function addEnhancedStyles() {
    var style = document.createElement('style');
    style.textContent = `
        .date-range-controls {
            display: flex;
            gap: 5px;
            flex-wrap: wrap;
            justify-content: center;
            margin-top: 10px;
        }
        
        .preset-controls {
            margin: 15px 0;
            padding: 15px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 8px;
        }
        
        .loading-enhanced {
            text-align: center;
            padding: 60px 20px;
        }
        
        .loading-spinner {
            width: 40px;
            height: 40px;
            border: 4px solid rgba(255, 255, 255, 0.3);
            border-top: 4px solid #4ecdc4;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .loading-text {
            font-size: 1.2rem;
            color: #4ecdc4;
            margin-bottom: 10px;
        }
        
        .loading-subtext {
            color: #ccc;
            font-size: 0.9rem;
        }
        
        .performance-indicator {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: bold;
        }
        
        .performance-excellent { background: #51cf66; color: #000; }
        .performance-good { background: #4ecdc4; color: #000; }
        .performance-average { background: #ffd43b; color: #000; }
        .performance-poor { background: #ff6b6b; color: #fff; }
        
        .quick-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin: 20px 0;
        }
        
        .quick-stat {
            background: rgba(255, 255, 255, 0.1);
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        
        .quick-stat-value {
            font-size: 1.5rem;
            font-weight: bold;
            color: #4ecdc4;
        }
        
        .quick-stat-label {
            font-size: 0.9rem;
            color: #ccc;
            margin-top: 5px;
        }
        
        @media (max-width: 768px) {
            .date-range-controls, .preset-controls {
                justify-content: center;
            }
            
            .preset-controls {
                padding: 10px;
            }
        }
    `;
    document.head.appendChild(style);
}

// Initialize enhancements when page loads
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() {
        addEnhancedStyles();
        addDateRangeNavigation();
        addQuickDatePresets();
    }, 500);
});

// Performance analysis helpers
function getPerformanceIndicator(grade) {
    if (!grade) return '';
    
    var className = 'performance-average';
    if (grade === 'A+' || grade === 'A') className = 'performance-excellent';
    else if (grade === 'B+' || grade === 'B') className = 'performance-good';
    else if (grade === 'D' || grade === 'F') className = 'performance-poor';
    
    return `<span class="performance-indicator ${className}">${grade}</span>`;
}

function addQuickStatsDisplay(data) {
    var recapSection = document.getElementById('recap-section');
    if (recapSection && data.games) {
        var quickStats = document.createElement('div');
        quickStats.className = 'quick-stats';
        
        var gamesWithAnalysis = data.games.filter(function(game) {
            return game.performance_analysis;
        });
        
        var excellentGrades = gamesWithAnalysis.filter(function(game) {
            var grade = game.performance_analysis.overall_grade;
            return grade === 'A+' || grade === 'A';
        }).length;
        
        var correctWinners = gamesWithAnalysis.filter(function(game) {
            return game.performance_analysis.winner_correct;
        }).length;
        
        quickStats.innerHTML = `
            <div class="quick-stat">
                <div class="quick-stat-value">${data.games.length}</div>
                <div class="quick-stat-label">Total Games</div>
            </div>
            <div class="quick-stat">
                <div class="quick-stat-value">${excellentGrades}</div>
                <div class="quick-stat-label">A-Grade Predictions</div>
            </div>
            <div class="quick-stat">
                <div class="quick-stat-value">${correctWinners}</div>
                <div class="quick-stat-label">Correct Winners</div>
            </div>
            <div class="quick-stat">
                <div class="quick-stat-value">${gamesWithAnalysis.length}</div>
                <div class="quick-stat-label">Complete Analysis</div>
            </div>
        `;
        
        // Insert after recap title
        var recapTitle = recapSection.querySelector('.recap-title');
        if (recapTitle) {
            recapTitle.parentNode.insertBefore(quickStats, recapTitle.nextSibling);
        }
    }
}

console.log('Enhanced navigation features loaded');
