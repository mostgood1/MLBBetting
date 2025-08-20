// Advanced Filtering and Search Features

// Filter state
var filterState = {
    team: '',
    grade: '',
    minScore: '',
    maxScore: '',
    winnerCorrect: '',
    showPredictionsOnly: false,
    showResultsOnly: false
};

// Add filter controls
function addFilterControls() {
    var container = document.querySelector('.container');
    if (container && !document.querySelector('.filter-panel')) {
        var filterPanel = document.createElement('div');
        filterPanel.className = 'filter-panel';
        filterPanel.style.cssText = `
            background: rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        `;
        
        filterPanel.innerHTML = `
            <div class="filter-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h3 style="color: #4ecdc4; margin: 0;">🔍 Advanced Filters</h3>
                <button class="btn secondary" onclick="toggleFilterPanel()" id="filter-toggle">Hide Filters</button>
            </div>
            <div class="filter-content" id="filter-content">
                <div class="filter-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                    <div class="filter-group">
                        <label style="color: #ccc; display: block; margin-bottom: 5px;">Team:</label>
                        <input type="text" id="filter-team" placeholder="Enter team name..." style="
                            padding: 8px;
                            border: 1px solid rgba(255, 255, 255, 0.3);
                            border-radius: 5px;
                            background: rgba(255, 255, 255, 0.1);
                            color: white;
                            width: 100%;
                        ">
                    </div>
                    <div class="filter-group">
                        <label style="color: #ccc; display: block; margin-bottom: 5px;">Grade:</label>
                        <select id="filter-grade" style="
                            padding: 8px;
                            border: 1px solid rgba(255, 255, 255, 0.3);
                            border-radius: 5px;
                            background: rgba(255, 255, 255, 0.1);
                            color: white;
                            width: 100%;
                        ">
                            <option value="">All Grades</option>
                            <option value="A+">A+</option>
                            <option value="A">A</option>
                            <option value="B+">B+</option>
                            <option value="B">B</option>
                            <option value="C+">C+</option>
                            <option value="C">C</option>
                            <option value="D">D</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label style="color: #ccc; display: block; margin-bottom: 5px;">Winner Prediction:</label>
                        <select id="filter-winner" style="
                            padding: 8px;
                            border: 1px solid rgba(255, 255, 255, 0.3);
                            border-radius: 5px;
                            background: rgba(255, 255, 255, 0.1);
                            color: white;
                            width: 100%;
                        ">
                            <option value="">All</option>
                            <option value="true">Correct</option>
                            <option value="false">Incorrect</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label style="color: #ccc; display: block; margin-bottom: 5px;">Data Type:</label>
                        <select id="filter-data-type" style="
                            padding: 8px;
                            border: 1px solid rgba(255, 255, 255, 0.3);
                            border-radius: 5px;
                            background: rgba(255, 255, 255, 0.1);
                            color: white;
                            width: 100%;
                        ">
                            <option value="">All Games</option>
                            <option value="predictions">Predictions Only</option>
                            <option value="results">Results Only</option>
                            <option value="complete">Complete Analysis</option>
                        </select>
                    </div>
                </div>
                <div class="filter-actions" style="margin-top: 15px; text-align: center;">
                    <button class="btn" onclick="applyFilters()">Apply Filters</button>
                    <button class="btn secondary" onclick="clearFilters()">Clear All</button>
                    <button class="btn secondary" onclick="saveFilterPreset()">Save Preset</button>
                </div>
            </div>
        `;
        
        // Insert after nav controls
        var navControls = document.querySelector('.nav-controls');
        if (navControls) {
            navControls.parentNode.insertBefore(filterPanel, navControls.nextSibling);
        }
        
        // Add event listeners
        document.getElementById('filter-team').addEventListener('input', debounce(applyFilters, 500));
        document.getElementById('filter-grade').addEventListener('change', applyFilters);
        document.getElementById('filter-winner').addEventListener('change', applyFilters);
        document.getElementById('filter-data-type').addEventListener('change', applyFilters);
    }
}

// Toggle filter panel visibility
function toggleFilterPanel() {
    var content = document.getElementById('filter-content');
    var toggle = document.getElementById('filter-toggle');
    
    if (content.style.display === 'none') {
        content.style.display = 'block';
        toggle.textContent = 'Hide Filters';
    } else {
        content.style.display = 'none';
        toggle.textContent = 'Show Filters';
    }
}

// Apply filters to current data
function applyFilters() {
    if (!currentDataCache) return;
    
    // Get filter values
    var teamFilter = document.getElementById('filter-team')?.value.toLowerCase() || '';
    var gradeFilter = document.getElementById('filter-grade')?.value || '';
    var winnerFilter = document.getElementById('filter-winner')?.value || '';
    var dataTypeFilter = document.getElementById('filter-data-type')?.value || '';
    
    // Filter games
    var filteredGames = currentDataCache.games.filter(function(game) {
        // Team filter
        if (teamFilter && 
            !game.away_team.toLowerCase().includes(teamFilter) && 
            !game.home_team.toLowerCase().includes(teamFilter)) {
            return false;
        }
        
        // Grade filter
        if (gradeFilter && 
            (!game.performance_analysis || game.performance_analysis.overall_grade !== gradeFilter)) {
            return false;
        }
        
        // Winner prediction filter
        if (winnerFilter !== '') {
            var isCorrect = game.performance_analysis?.winner_correct;
            if (winnerFilter === 'true' && !isCorrect) return false;
            if (winnerFilter === 'false' && isCorrect) return false;
        }
        
        // Data type filter
        if (dataTypeFilter === 'predictions' && !game.prediction) return false;
        if (dataTypeFilter === 'results' && !game.result) return false;
        if (dataTypeFilter === 'complete' && (!game.prediction || !game.result || !game.performance_analysis)) return false;
        
        return true;
    });
    
    // Update display with filtered data
    var filteredData = {
        games: filteredGames,
        summary: currentDataCache.summary
    };
    
    displayFilteredResults(filteredData);
    updateFilterStatus(filteredGames.length, currentDataCache.games.length);
}

function displayFilteredResults(data) {
    displayGames(data.games, 'enhanced');
    
    // Update recap with filtered data
    if (data.games.length > 0) {
        addQuickStatsDisplay(data);
    } else {
        var container = document.getElementById('games-container');
        container.innerHTML = '<div class="error">No games match the current filters. Try adjusting your criteria.</div>';
    }
}

function updateFilterStatus(filteredCount, totalCount) {
    var existing = document.getElementById('filter-status');
    if (existing) existing.remove();
    
    if (filteredCount !== totalCount) {
        var status = document.createElement('div');
        status.id = 'filter-status';
        status.style.cssText = `
            background: rgba(78, 205, 196, 0.2);
            border: 1px solid #4ecdc4;
            color: #4ecdc4;
            padding: 10px;
            border-radius: 8px;
            text-align: center;
            margin: 10px 0;
        `;
        status.innerHTML = `📊 Showing ${filteredCount} of ${totalCount} games (filtered)`;
        
        var filterPanel = document.querySelector('.filter-panel');
        if (filterPanel) {
            filterPanel.parentNode.insertBefore(status, filterPanel.nextSibling);
        }
    }
}

function clearFilters() {
    document.getElementById('filter-team').value = '';
    document.getElementById('filter-grade').value = '';
    document.getElementById('filter-winner').value = '';
    document.getElementById('filter-data-type').value = '';
    
    // Remove filter status
    var status = document.getElementById('filter-status');
    if (status) status.remove();
    
    // Redisplay all data
    if (currentDataCache) {
        displayEnhancedData(currentDataCache, document.getElementById('analysis-date')?.value || 'unknown');
    }
}

// Search functionality
function addSearchFeature() {
    var filterPanel = document.querySelector('.filter-panel');
    if (filterPanel && !document.querySelector('.search-box')) {
        var searchBox = document.createElement('div');
        searchBox.className = 'search-box';
        searchBox.style.cssText = `
            margin-top: 15px;
            display: flex;
            gap: 10px;
            align-items: center;
        `;
        
        searchBox.innerHTML = `
            <input type="text" id="global-search" placeholder="🔍 Search games, teams, or analysis..." style="
                flex: 1;
                padding: 10px;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                background: rgba(255, 255, 255, 0.1);
                color: white;
                font-size: 16px;
            ">
            <button class="btn" onclick="performGlobalSearch()" style="white-space: nowrap;">Search</button>
        `;
        
        filterPanel.appendChild(searchBox);
        
        // Add real-time search
        document.getElementById('global-search').addEventListener('input', debounce(performGlobalSearch, 300));
    }
}

function performGlobalSearch() {
    if (!currentDataCache) return;
    
    var searchTerm = document.getElementById('global-search')?.value.toLowerCase() || '';
    if (!searchTerm.trim()) {
        applyFilters(); // Apply existing filters
        return;
    }
    
    var searchResults = currentDataCache.games.filter(function(game) {
        // Search in team names
        if (game.away_team.toLowerCase().includes(searchTerm) || 
            game.home_team.toLowerCase().includes(searchTerm)) {
            return true;
        }
        
        // Search in grade
        if (game.performance_analysis?.overall_grade?.toLowerCase().includes(searchTerm)) {
            return true;
        }
        
        // Search in pitcher names
        if (game.prediction?.away_pitcher?.toLowerCase().includes(searchTerm) ||
            game.prediction?.home_pitcher?.toLowerCase().includes(searchTerm)) {
            return true;
        }
        
        // Search in game ID
        if (game.game_id?.toString().includes(searchTerm)) {
            return true;
        }
        
        return false;
    });
    
    displayFilteredResults({ games: searchResults, summary: currentDataCache.summary });
    updateFilterStatus(searchResults.length, currentDataCache.games.length);
}

// Debounce utility
function debounce(func, wait) {
    var timeout;
    return function executedFunction() {
        var later = function() {
            clearTimeout(timeout);
            func.apply(this, arguments);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Save/load filter presets
function saveFilterPreset() {
    var preset = {
        team: document.getElementById('filter-team')?.value || '',
        grade: document.getElementById('filter-grade')?.value || '',
        winner: document.getElementById('filter-winner')?.value || '',
        dataType: document.getElementById('filter-data-type')?.value || '',
        search: document.getElementById('global-search')?.value || ''
    };
    
    var presetName = prompt('Enter a name for this filter preset:');
    if (presetName) {
        var presets = JSON.parse(localStorage.getItem('mlb-filter-presets') || '{}');
        presets[presetName] = preset;
        localStorage.setItem('mlb-filter-presets', JSON.stringify(presets));
        alert('Filter preset "' + presetName + '" saved successfully!');
        updatePresetSelector();
    }
}

function updatePresetSelector() {
    var existing = document.getElementById('preset-selector');
    if (existing) existing.remove();
    
    var presets = JSON.parse(localStorage.getItem('mlb-filter-presets') || '{}');
    if (Object.keys(presets).length === 0) return;
    
    var selector = document.createElement('div');
    selector.id = 'preset-selector';
    selector.style.cssText = `
        margin-top: 10px;
        display: flex;
        gap: 10px;
        align-items: center;
        flex-wrap: wrap;
    `;
    
    var selectHTML = '<select id="preset-select" style="padding: 8px; border-radius: 5px; background: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.3);"><option value="">Load Preset...</option>';
    
    for (var name in presets) {
        selectHTML += '<option value="' + name + '">' + name + '</option>';
    }
    selectHTML += '</select>';
    
    selector.innerHTML = selectHTML + 
        '<button class="btn secondary" onclick="loadFilterPreset()">Load</button>' +
        '<button class="btn secondary" onclick="deleteFilterPreset()">Delete</button>';
    
    var filterPanel = document.querySelector('.filter-panel');
    if (filterPanel) {
        filterPanel.appendChild(selector);
    }
}

function loadFilterPreset() {
    var presetName = document.getElementById('preset-select')?.value;
    if (!presetName) return;
    
    var presets = JSON.parse(localStorage.getItem('mlb-filter-presets') || '{}');
    var preset = presets[presetName];
    
    if (preset) {
        document.getElementById('filter-team').value = preset.team || '';
        document.getElementById('filter-grade').value = preset.grade || '';
        document.getElementById('filter-winner').value = preset.winner || '';
        document.getElementById('filter-data-type').value = preset.dataType || '';
        document.getElementById('global-search').value = preset.search || '';
        
        applyFilters();
        performGlobalSearch();
    }
}

function deleteFilterPreset() {
    var presetName = document.getElementById('preset-select')?.value;
    if (!presetName) return;
    
    if (confirm('Delete filter preset "' + presetName + '"?')) {
        var presets = JSON.parse(localStorage.getItem('mlb-filter-presets') || '{}');
        delete presets[presetName];
        localStorage.setItem('mlb-filter-presets', JSON.stringify(presets));
        updatePresetSelector();
        alert('Preset deleted successfully!');
    }
}

// Initialize filtering features
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() {
        addFilterControls();
        addSearchFeature();
        updatePresetSelector();
    }, 1500);
});

console.log('Advanced filtering features loaded');
