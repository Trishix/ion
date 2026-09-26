from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from time import monotonic

from ion.contracts import Phase


@dataclass(frozen=True)
class RequestReservation:
    attempt: int
    remaining: int


class BudgetLedger:
    def __init__(self, max_requests: int = 24, deadline_seconds: float = 600, max_total_tokens: int | None = None, reserve_verification: bool = True) -> None:
        self.max_requests = max_requests
        self.deadline = monotonic() + deadline_seconds
        self.used = 0
        self.max_total_tokens = max_total_tokens
        self.tokens_used = 0
        self.reserve_verification = reserve_verification
        self._reservations: dict[int, int] = {}
        self._lock = Lock()

    def admit(self, phase: Phase, input_tokens: int = 0, output_tokens: int = 0) -> RequestReservation:
        with self._lock:
            if monotonic() >= self.deadline or self.used >= self.max_requests:
                raise RuntimeError("budget exhausted")
            if self.reserve_verification and self.used >= int(self.max_requests * 0.8) and phase not in (Phase.verify, Phase.finalize):
                raise RuntimeError("verification reserve reached")
            reservation = max(0, input_tokens) + max(0, output_tokens)
            if self.max_total_tokens is not None and self.tokens_used + reservation > self.max_total_tokens:
                raise RuntimeError("total token budget exhausted")
            self.used += 1
            self._reservations[self.used] = reservation
            self.tokens_used += reservation
            return RequestReservation(self.used, self.max_requests - self.used)

    reserve = admit

    def settle(self, input_tokens: int, output_tokens: int, attempt: int | None = None) -> None:
        """Replace the estimate only when the provider reports complete usage."""
        with self._lock:
            if attempt is None:
                attempt = max(self._reservations, default=0)
            estimate = self._reservations.pop(attempt, 0)
            self.tokens_used += max(0, input_tokens) + max(0, output_tokens) - estimate
