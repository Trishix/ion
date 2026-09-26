from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from ion.contracts import Phase


@dataclass(frozen=True)
class RequestReservation:
    attempt: int
    remaining: int


class BudgetLedger:
    def __init__(self, max_requests: int = 100, deadline_seconds: float = 1800) -> None:
        self.max_requests = max_requests
        self.deadline = monotonic() + deadline_seconds
        self.used = 0

    def admit(self, phase: Phase) -> RequestReservation:
        if monotonic() >= self.deadline or self.used >= self.max_requests:
            raise RuntimeError("budget exhausted")
        if self.used >= int(self.max_requests * 0.8) and phase not in (Phase.verify, Phase.finalize):
            raise RuntimeError("verification reserve reached")
        self.used += 1
        return RequestReservation(self.used, self.max_requests - self.used)
