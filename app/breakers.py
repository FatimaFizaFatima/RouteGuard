import time


class CircuitBreaker:
    def __init__(self, failure_limit: int = 3, cooldown_s: float = 30.0):
        self.failure_limit = failure_limit
        self.cooldown_s = cooldown_s
        self.failures = 0
        self.state = "closed"
        self.opened_at = 0.0
        self.probe_in_flight = False

    def allow(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.monotonic() - self.opened_at >= self.cooldown_s:
                self.state = "half_open"
                self.probe_in_flight = True
                return True
            return False
        if self.probe_in_flight:
            return False
        self.probe_in_flight = True
        return True

    def record_success(self) -> None:
        self.failures = 0
        self.state = "closed"
        self.probe_in_flight = False

    def record_failure(self) -> None:
        self.probe_in_flight = False
        if self.state == "half_open":
            self._open()
            return
        self.failures += 1
        if self.failures >= self.failure_limit:
            self._open()

    def release(self) -> None:
        self.probe_in_flight = False

    def _open(self) -> None:
        self.state = "open"
        self.opened_at = time.monotonic()