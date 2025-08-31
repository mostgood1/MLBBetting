"""
Stub monitoring_history module exposing a minimal history_tracker object
to satisfy imports during development or limited deployments.
"""
from typing import Dict, Any, List

class _HistoryTracker:
    def get_combined_history(self) -> List[Dict[str, Any]]:
        return []

    def get_stats(self) -> Dict[str, Any]:
        return {"events": 0, "errors": 0}

history_tracker = _HistoryTracker()
