import pytest

from ion.budget import BudgetLedger
from ion.contracts import Phase


def test_physical_request_reservations_settle_independently():
    ledger = BudgetLedger(max_requests=4, max_total_tokens=1000, reserve_verification=False)
    first = ledger.reserve(Phase.act, 10, 20)
    second = ledger.reserve(Phase.act, 30, 40)
    assert first.attempt == 1 and second.attempt == 2
    ledger.settle(12, 8, first.attempt)
    assert ledger.tokens_used == 90
    ledger.settle(20, 10, second.attempt)
    assert ledger.tokens_used == 50


def test_verification_reserve_blocks_discretionary_work():
    ledger = BudgetLedger(max_requests=5, reserve_verification=True)
    for _ in range(4):
        ledger.admit(Phase.act)
    with pytest.raises(RuntimeError, match="verification reserve"):
        ledger.admit(Phase.act)
    assert ledger.admit(Phase.verify).attempt == 5
