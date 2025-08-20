// Data Export and Analysis Features

// Export data to CSV
function exportToCSV(data, filename) {
    if (!data || !data.games) {
        alert('No data available to export');
        return;
    }
    
    var csv = 'Date,Away Team,Home Team,Predicted Away Score,Predicted Home Score,Actual Away Score,Actual Home Score,Winner Correct,Grade,Grade Percentage\n';
    
    data.games.forEach(function(game) {
        var prediction = game.prediction || {};
        var result = game.result || {};
        var analysis = game.performance_analysis || {};
        
        csv += [
            game.game_date || 'N/A',
            game.away_team || 'N/A',
            game.home_team || 'N/A',
            prediction.predicted_away_score || 'N/A',
            prediction.predicted_home_score || 'N/A',
            result.away_score || 'N/A',
            result.home_score || 'N/A',
            analysis.winner_correct || 'N/A',
            analysis.overall_grade || 'N/A',
            analysis.grade_percentage || 'N/A'
        ].join(',') + '\n';
    });
    
    downloadCSV(csv, filename);
}

function downloadCSV(csv, filename) {
    var blob = new Blob([csv], { type: 'text/csv' });
    var url = window.URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
}

// Generate performance report
function generatePerformanceReport(data) {
    if (!data || !data.games) return null;
    
    var gamesWithAnalysis = data.games.filter(function(game) {
        return game.performance_analysis;
    });
    
    var totalGames = gamesWithAnalysis.length;
    var correctWinners = gamesWithAnalysis.filter(function(game) {
        return game.performance_analysis.winner_correct;
    }).length;
    
    var gradeDistribution = {};
    var totalGradePoints = 0;
    
    gamesWithAnalysis.forEach(function(game) {
        var grade = game.performance_analysis.overall_grade;
        if (grade) {
            gradeDistribution[grade] = (gradeDistribution[grade] || 0) + 1;
        }
        if (game.performance_analysis.grade_percentage) {
            totalGradePoints += game.performance_analysis.grade_percentage;
        }
    });
    
    var avgGrade = totalGames > 0 ? totalGradePoints / totalGames : 0;
    var winnerAccuracy = totalGames > 0 ? (correctWinners / totalGames) * 100 : 0;
    
    return {
        totalGames: totalGames,
        correctWinners: correctWinners,
        winnerAccuracy: winnerAccuracy.toFixed(1),
        avgGrade: avgGrade.toFixed(1),
        gradeDistribution: gradeDistribution
    };
}

// Add export controls
function addExportControls() {
    var navControls = document.querySelector('.nav-controls');
    if (navControls && !document.querySelector('.export-controls')) {
        var exportControls = document.createElement('div');
        exportControls.className = 'export-controls';
        exportControls.style.marginTop = '15px';
        exportControls.innerHTML = `
            <div style="display: flex; gap: 10px; flex-wrap: wrap; justify-content: center;">
                <button class="btn secondary" onclick="exportCurrentData()">📊 Export CSV</button>
                <button class="btn secondary" onclick="showPerformanceReport()">📈 Performance Report</button>
                <button class="btn secondary" onclick="showDataSummary()">📋 Data Summary</button>
            </div>
        `;
        navControls.appendChild(exportControls);
    }
}

var currentDataCache = null;

function exportCurrentData() {
    if (currentDataCache) {
        var dateInput = document.getElementById('analysis-date');
        var date = dateInput ? dateInput.value : 'unknown';
        var filename = 'mlb-analysis-' + date + '.csv';
        exportToCSV(currentDataCache, filename);
    } else {
        alert('No data loaded to export. Please load a date first.');
    }
}

function showPerformanceReport() {
    if (!currentDataCache) {
        alert('No data loaded. Please load a date first.');
        return;
    }
    
    var report = generatePerformanceReport(currentDataCache);
    if (!report) {
        alert('Unable to generate performance report.');
        return;
    }
    
    var gradeDistText = '';
    for (var grade in report.gradeDistribution) {
        gradeDistText += grade + ': ' + report.gradeDistribution[grade] + ' games\n';
    }
    
    var reportText = `Performance Report\n` +
        `==================\n` +
        `Total Games: ${report.totalGames}\n` +
        `Correct Winners: ${report.correctWinners}\n` +
        `Winner Accuracy: ${report.winnerAccuracy}%\n` +
        `Average Grade: ${report.avgGrade}%\n\n` +
        `Grade Distribution:\n${gradeDistText}`;
    
    // Create modal or alert
    showModal('Performance Report', reportText);
}

function showDataSummary() {
    if (!currentDataCache) {
        alert('No data loaded. Please load a date first.');
        return;
    }
    
    var gamesWithPredictions = currentDataCache.games.filter(function(game) {
        return game.prediction;
    }).length;
    
    var gamesWithResults = currentDataCache.games.filter(function(game) {
        return game.result;
    }).length;
    
    var gamesWithAnalysis = currentDataCache.games.filter(function(game) {
        return game.performance_analysis;
    }).length;
    
    var summaryText = `Data Summary\n` +
        `=============\n` +
        `Total Games: ${currentDataCache.games.length}\n` +
        `Games with Predictions: ${gamesWithPredictions}\n` +
        `Games with Results: ${gamesWithResults}\n` +
        `Games with Analysis: ${gamesWithAnalysis}\n` +
        `Data Completeness: ${Math.round((gamesWithAnalysis / currentDataCache.games.length) * 100)}%`;
    
    showModal('Data Summary', summaryText);
}

function showModal(title, content) {
    // Remove existing modal
    var existingModal = document.getElementById('data-modal');
    if (existingModal) {
        existingModal.remove();
    }
    
    var modal = document.createElement('div');
    modal.id = 'data-modal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.8);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 1000;
    `;
    
    modal.innerHTML = `
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            max-width: 500px;
            max-height: 70vh;
            overflow-y: auto;
            position: relative;
            border: 1px solid rgba(255, 255, 255, 0.2);
        ">
            <h3 style="margin-bottom: 20px; color: #4ecdc4;">${title}</h3>
            <pre style="
                font-family: monospace;
                white-space: pre-wrap;
                font-size: 14px;
                line-height: 1.4;
                margin-bottom: 20px;
            ">${content}</pre>
            <button onclick="document.getElementById('data-modal').remove()" style="
                background: #4ecdc4;
                color: #000;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-weight: bold;
            ">Close</button>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Close on click outside
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.remove();
        }
    });
}

// Cache data when loaded
function cacheLoadedData(data) {
    currentDataCache = data;
}

console.log('Data export features loaded');
