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
