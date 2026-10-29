import threading
from dataclasses import dataclass, field
from datetime import date


@dataclass
class DailyCap:
    limit: int
    day: date | None = None
    used: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def take(self, today: date) -> bool:
        with self._lock:
            if today != self.day:
                self.day, self.used = today, 0
            if self.used >= self.limit:
                return False
            self.used += 1
            return True

    def remaining(self, today: date) -> int:
        with self._lock:
            return self.limit if today != self.day else self.limit - self.used
