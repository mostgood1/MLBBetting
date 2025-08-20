// JavaScript Compatibility Patches for Historical Analysis Page

// Add polyfill for String.padStart (for older browsers)
if (!String.prototype.padStart) {
    String.prototype.padStart = function padStart(targetLength, padString) {
        targetLength = targetLength >> 0;
        padString = String(typeof padString !== 'undefined' ? padString : ' ');
        if (this.length > targetLength) {
            return String(this);
        } else {
            targetLength = targetLength - this.length;
            if (targetLength > padString.length) {
                padString += padString.repeat(targetLength / padString.length);
            }
            return padString.slice(0, targetLength) + String(this);
        }
    };
}

// Add polyfill for Array.some (for older browsers)
if (!Array.prototype.some) {
    Array.prototype.some = function(fun, thisArg) {
        if (this == null) {
            throw new TypeError('Array.prototype.some called on null or undefined');
        }
        if (typeof fun !== 'function') {
            throw new TypeError();
        }
        var t = Object(this);
        var len = t.length >>> 0;
        for (var i = 0; i < len; i++) {
            if (i in t && fun.call(thisArg, t[i], i, t)) {
                return true;
            }
        }
        return false;
    };
}

// Add polyfill for Array.filter (for older browsers)
if (!Array.prototype.filter) {
    Array.prototype.filter = function(fun, thisArg) {
        if (this == null) {
            throw new TypeError('Array.prototype.filter called on null or undefined');
        }
        if (typeof fun !== 'function') {
            throw new TypeError();
        }
        var t = Object(this);
        var len = t.length >>> 0;
        var res = [];
        for (var i = 0; i < len; i++) {
            if (i in t) {
                var val = t[i];
                if (fun.call(thisArg, val, i, t)) {
                    res.push(val);
                }
            }
        }
        return res;
    };
}

// Enhanced error handling and logging
window.debugMode = true;

function debugLog(message) {
    if (window.debugMode) {
        console.log('[DEBUG] ' + new Date().toLocaleTimeString() + ': ' + message);
    }
}

function safeElementAccess(id, action) {
    try {
        var element = document.getElementById(id);
        if (element) {
            return action(element);
        } else {
            debugLog('Element not found: ' + id);
            return null;
        }
    } catch (error) {
        debugLog('Error accessing element ' + id + ': ' + error.message);
        return null;
    }
}

// Override console methods to show alerts if console is not available
if (typeof console === 'undefined') {
    window.console = {
        log: function(msg) { 
            if (window.debugMode) alert('LOG: ' + msg); 
        },
        error: function(msg) { 
            alert('ERROR: ' + msg); 
        },
        warn: function(msg) { 
            if (window.debugMode) alert('WARN: ' + msg); 
        }
    };
}

debugLog('Compatibility patches loaded successfully');
