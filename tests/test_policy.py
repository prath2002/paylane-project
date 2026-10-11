"""Direct tests of the policy guards. No LLM calls and no API key needed."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import Session, run_tool
from tools.api import escalate_to_human, get_customer, get_transaction, issue_refund


@pytest.fixture
def s():
    return Session()


@pytest.fixture
def asha(s):
    """Session with Asha (C001) verified."""
    assert get_customer(s, "asha@example.com", "4421")["verified"] is True
    return s


# --- refunds ---

def test_refund_t100_succeeds(asha):
    result = issue_refund(asha, "T100", 42.50)
    assert result == {"ok": True, "refund_id": "R001"}
    assert asha.transactions["T100"]["status"] == "refunded"
    assert len(asha.refunds) == 1


def test_second_refund_on_t100_refused(asha):
    assert issue_refund(asha, "T100", 42.50)["ok"] is True
    result = issue_refund(asha, "T100", 10.00)
    assert result["ok"] is False
    assert "already been refunded" in result["reason"]
    assert len(asha.refunds) == 1


def test_already_refunded_mock_txn_refused(asha):
    result = issue_refund(asha, "T103", 18.00)
    assert result["ok"] is False
    assert "already been refunded" in result["reason"]


def test_refund_exact_cap_allowed(asha):
    assert issue_refund(asha, "T104", 75.00)["ok"] is True


def test_refund_over_cap_refused(asha):
    # T104 is exactly $75, so $75.01 also exceeds the transaction amount.
    # Use T101 ($120) to hit the cap rule on its own.
    result = issue_refund(asha, "T104", 75.01)
    assert result["ok"] is False
    result = issue_refund(asha, "T101", 75.01)
    assert result["ok"] is False
    assert "limit" in result["reason"]


def test_refund_exactly_30_days_old_refused(asha):
    result = issue_refund(asha, "T102", 30.00)
    assert result["ok"] is False
    assert "30 days" in result["reason"]


def test_refund_t101_full_amount_refused_for_cap(asha):
    result = issue_refund(asha, "T101", 120.00)
    assert result["ok"] is False
    assert "$75.00" in result["reason"]
    assert asha.transactions["T101"]["status"] == "settled"


def test_refund_on_frozen_card_refused(s):
    assert get_customer(s, "vikram@example.com", "9087")["verified"] is True
    result = issue_refund(s, "T200", 50.00)
    assert result["ok"] is False
    assert "frozen" in result["reason"]


def test_refund_before_verification_refused(s):
    result = issue_refund(s, "T100", 42.50)
    assert result["ok"] is False
    assert "not verified" in result["reason"]
    assert s.transactions["T100"]["status"] == "settled"


@pytest.mark.parametrize("amount", [0, 0.0, -5, -0.01])
def test_refund_zero_or_negative_refused(asha, amount):
    result = issue_refund(asha, "T100", amount)
    assert result["ok"] is False
    assert "greater than zero" in result["reason"]


@pytest.mark.parametrize("amount", ["42.50", None, True])
def test_refund_non_number_refused(asha, amount):
    assert issue_refund(asha, "T100", amount)["ok"] is False


def test_refund_more_than_transaction_refused(asha):
    result = issue_refund(asha, "T100", 50.00)
    assert result["ok"] is False
    assert "more than the transaction amount" in result["reason"]


def test_refund_unknown_transaction_refused(asha):
    assert issue_refund(asha, "T999", 10.00)["ok"] is False


def test_pending_transaction_refused(asha):
    asha.transactions["T100"]["status"] = "pending"
    result = issue_refund(asha, "T100", 10.00)
    assert result == {"ok": False, "reason": "transaction is pending; try again after it settles"}


def test_partial_75_on_transaction_over_cap_refused(asha):
    # The failure found in eval conversation 03: "just refund $75 of the $120".
    result = issue_refund(asha, "T101", 75.00)
    assert result["ok"] is False
    assert "whole transaction" in result["reason"]
    assert asha.refunds == []


def test_pending_transaction_in_mock_refused(s):
    get_customer(s, "meera@example.com", "3350")
    assert issue_refund(s, "T301", 25.00)["reason"].startswith("transaction is pending")


def test_partial_refund_allowed_once(asha):
    assert issue_refund(asha, "T100", 20.00)["ok"] is True
    assert issue_refund(asha, "T100", 10.00)["ok"] is False


# --- verification ---

def test_get_customer_wrong_digits_not_verified(s):
    result = get_customer(s, "asha@example.com", "0000")
    assert result == {"verified": False, "attempts_left": 2}
    assert "C001" not in s.verified_ids


def test_get_customer_right_digits_verifies(s):
    result = get_customer(s, "  Asha@Example.com ", "4421")
    assert result["verified"] is True
    assert result["name"] == "Asha Rao"
    assert "C001" in s.verified_ids
    # never leak the email or card digits
    assert "email" not in result and "card_last4" not in result


def test_get_customer_frozen_includes_reason(s):
    result = get_customer(s, "vikram@example.com", "9087")
    assert result["status"] == "frozen"
    assert "fraud alert" in result["frozen_reason"]


def test_get_customer_unknown_email_looks_like_wrong_digits(s):
    # Must not reveal whether an email has an account.
    assert get_customer(s, "nobody@example.com", "1234") == {"verified": False, "attempts_left": 2}


def test_locked_after_three_failed_attempts(s):
    for digits in ["1234", "4412", "4241"]:
        assert get_customer(s, "asha@example.com", digits)["verified"] is False
    # The right digits on the 4th try are still refused.
    result = get_customer(s, "asha@example.com", "4421")
    assert result["verified"] is False and result["locked"] is True
    assert "C001" not in s.verified_ids


def test_lock_counts_attempts_across_emails(s):
    get_customer(s, "asha@example.com", "0000")
    get_customer(s, "vikram@example.com", "0000")
    get_customer(s, "meera@example.com", "0000")
    assert get_customer(s, "meera@example.com", "3350")["locked"] is True


def test_missing_digits_do_not_count_as_attempt(s):
    assert get_customer(s, "asha@example.com")["verified"] is False
    assert s.failed_attempts == 0


def test_get_transaction_refused_before_verification(s):
    result = get_transaction(s, "C001", "T100")
    assert "error" in result
    assert "amount" not in result


def test_get_transaction_other_customers_txn_refused(asha):
    result = get_transaction(asha, "C001", "T200")
    assert "error" in result
    assert "amount" not in result


def test_get_transaction_returns_details(asha):
    assert get_transaction(asha, "C001", "T100") == {
        "amount": 42.50, "date": "2026-09-28", "merchant": "BlueCart", "status": "settled",
        "auto_refund": {"allowed": True},
    }


@pytest.mark.parametrize("txn_id, words", [
    ("T101", "escalated"),       # over the cap
    ("T102", "30 days"),         # exactly 30 days old
    ("T103", "already been refunded"),
    ("T104", None),              # exactly $75 is allowed
])
def test_get_transaction_reports_refund_eligibility(asha, txn_id, words):
    auto = get_transaction(asha, "C001", txn_id)["auto_refund"]
    if words is None:
        assert auto == {"allowed": True}
    else:
        assert auto["allowed"] is False and words in auto["reason"]


def test_eligibility_matches_issue_refund(asha):
    # get_transaction and issue_refund must never disagree.
    for txn_id, txn in asha.transactions.items():
        if txn["customer_id"] != "C001":
            continue
        allowed = get_transaction(asha, "C001", txn_id)["auto_refund"]["allowed"]
        fresh = Session()
        get_customer(fresh, "asha@example.com", "4421")
        assert issue_refund(fresh, txn_id, txn["amount"])["ok"] is allowed, txn_id


# --- escalation and sessions ---

def test_escalate_returns_ticket_and_records(s):
    result = escalate_to_human(s, "C001", "Refund over cap on T101")
    assert result == {"ticket_id": "ESC-0001"}
    assert s.escalations[0]["summary"] == "Refund over cap on T101"
    assert escalate_to_human(s, "C001", "second")["ticket_id"] == "ESC-0002"


def test_sessions_do_not_share_state(asha):
    issue_refund(asha, "T100", 42.50)
    fresh = Session()
    assert fresh.transactions["T100"]["status"] == "settled"
    assert fresh.verified_ids == set()
    assert fresh.refunds == []


# --- run_tool ---

def test_run_tool_unknown_name(s):
    result = json.loads(run_tool(s, "delete_everything", "{}"))
    assert result == {"error": "unknown tool: delete_everything"}


def test_run_tool_invalid_json(s):
    result = json.loads(run_tool(s, "get_customer", "{not json"))
    assert "error" in result


def test_run_tool_bad_arguments(s):
    result = json.loads(run_tool(s, "get_customer", '{"wrong_arg": 1}'))
    assert "error" in result


def test_run_tool_happy_path(s):
    result = json.loads(run_tool(s, "get_customer", '{"email": "asha@example.com", "card_last4": "4421"}'))
    assert result["verified"] is True
