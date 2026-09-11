"""Finite per-service call/token accounting; C must persist reservations across workers.

Default caps are zero. Independent normal/urgent ledgers cannot borrow capacity.
Input is budgeted conservatively by UTF-8 bytes, output by an explicit token cap.
"""

from dataclasses import dataclass


@dataclass
class ModelBudget:
    call_limit: int = 0
    token_limit: int = 0
    calls: int = 0
    blocked: int = 0
    tokens_reserved: int = 0
    tokens_used: int = 0

    def __post_init__(self):
        if not 0 <= self.call_limit <= 10000 or not 0 <= self.token_limit <= 100_000_000:
            raise ValueError("Model budgets must be finite and nonnegative")

    def reserve(self, tokens: int) -> bool:
        if (
            tokens < 1
            or self.calls >= self.call_limit
            or self.tokens_reserved + tokens > self.token_limit
        ):
            self.blocked += 1
            return False
        self.calls += 1
        self.tokens_reserved += (
            tokens  # Failed/unknown provider outcomes never refund a reservation.
        )
        return True

    def record_usage(self, tokens: int, reservation: int) -> None:
        if not 0 <= tokens <= reservation:
            raise ValueError("Model reported invalid usage")
        self.tokens_used += tokens
