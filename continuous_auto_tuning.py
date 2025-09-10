"""
Stub continuous_auto_tuning module to avoid missing import errors in environments
where auto-tuning is not configured. Provides a no-op ContinuousAutoTuner.
"""
from typing import Optional

class ContinuousAutoTuner:
    def __init__(self, *args, **kwargs) -> None:
        self.enabled = False

    def start(self) -> None:
        self.enabled = True

    def stop(self) -> None:
        self.enabled = False

    def is_running(self) -> bool:
        return self.enabled

    # Methods expected by app.py scheduling hooks (no-op stubs)
    def daily_full_optimization(self):
        """No-op placeholder for daily optimization."""
        return None

    def quick_optimization_check(self):
        """No-op placeholder for periodic quick check."""
        return None
