"""The four mock Paylane tools and every policy check.

This file is the single source of truth for policy. The model can ask for
anything, but nothing happens unless the checks here pass.
"""

import copy
from datetime import date

from tools.mock_data import CUSTOMERS, TRANSACTIONS

# Fixed "today" so test runs are repeatable. Do not use the real clock.
TODAY = date(2026, 10, 10)

REFUND_CAP = 75.00
REFUND_WINDOW_DAYS = 30  # refund allowed only when age in days < 30, counted from the purchase date
MAX_VERIFY_ATTEMPTS = 3  # failed verification attempts before the session is locked


class Session:
    """State for one conversation. Each Session gets its own copy of the data."""

    def __init__(self):
        self.customers = copy.deepcopy(CUSTOMERS)
        self.transactions = copy.deepcopy(TRANSACTIONS)
        self.verified_ids = set()
        self.failed_attempts = 0
        self.refunds = []
        self.escalations = []
        self.next_refund_num = 1
        self.next_ticket_num = 1


def _find_customer_by_id(s, customer_id):
    for customer in s.customers.values():
        if customer["id"] == customer_id:
            return customer
    return None


def get_customer(s, email, card_last4=None):
    if s.failed_attempts >= MAX_VERIFY_ATTEMPTS:
        return {"verified": False, "locked": True,
                "reason": "too many failed attempts; do not try again, escalate to a human"}

    email = str(email).strip().lower()
    customer = s.customers.get(email)

    # Already verified this session: no digits needed again.
    if customer is not None and customer["id"] in s.verified_ids:
        return _verified_result(customer)

    if card_last4 is None:
        return {"verified": False, "reason": "ask for the last 4 digits of the card"}

    # Verification needs both the email (used for lookup) and the card digits.
    if customer is not None and str(card_last4).strip() == customer["card_last4"]:
        s.verified_ids.add(customer["id"])
        return _verified_result(customer)

    # Unknown email and wrong digits look the same, so the tool can't be used
    # to find out which emails have accounts. Both count as a failed attempt.
    s.failed_attempts += 1
    left = MAX_VERIFY_ATTEMPTS - s.failed_attempts
    if left == 0:
        return {"verified": False, "locked": True,
                "reason": "too many failed attempts; do not try again, escalate to a human"}
    return {"verified": False, "attempts_left": left}


def _verified_result(customer):
    # Never return the email or card digits, even when verified.
    result = {
        "id": customer["id"],
        "name": customer["name"],
        "status": customer["status"],
        "verified": True,
    }
    if customer["status"] == "frozen":
        result["frozen_reason"] = customer.get("frozen_reason", "No reason on file.")
    return result


def get_transaction(s, customer_id, txn_id):
    if customer_id not in s.verified_ids:
        return {"error": "customer is not verified; ask for the email and last 4 card digits first"}

    txn = s.transactions.get(str(txn_id).strip().upper())
    # Same message for "missing" and "someone else's" so we don't leak which ids exist.
    if txn is None or txn["customer_id"] != customer_id:
        return {"error": "transaction not found on this account"}

    # Tell the agent up front whether a full refund is allowed, using the same
    # checks as issue_refund, so it never has to call issue_refund to find out.
    reason = _refund_block_reason(s, txn, txn["amount"])
    return {
        "amount": txn["amount"],
        "date": txn["date"],
        "merchant": txn["merchant"],
        "status": txn["status"],
        "auto_refund": {"allowed": True} if reason is None else {"allowed": False, "reason": reason},
    }


def _refuse(reason):
    return {"ok": False, "reason": reason}


def _refund_block_reason(s, txn, amount):
    """Return why a refund of `amount` on `txn` is not allowed, or None if it is."""
    # 1. Customer verified
    customer_id = txn["customer_id"]
    if customer_id not in s.verified_ids:
        return "customer is not verified; verification is required before any refund"

    # 2. Card not frozen
    customer = _find_customer_by_id(s, customer_id)
    if customer is None or customer["status"] == "frozen":
        return "card is frozen; refunds cannot be issued on a frozen card"

    # 3. Not already refunded (never refund the same transaction twice)
    if txn["status"] == "refunded":
        return "transaction has already been refunded"

    # Only settled transactions can be refunded
    if txn["status"] == "pending":
        return "transaction is pending; try again after it settles"
    if txn["status"] != "settled":
        return f"transaction status is '{txn['status']}'; only settled transactions can be refunded"

    # 4. Transaction itself is within the cap. Over $75 the whole transaction
    #    goes to a human; no partial refund of $75 on a bigger transaction.
    if txn["amount"] > REFUND_CAP:
        return (f"transaction is ${txn['amount']:.2f}, over the ${REFUND_CAP:.2f} automatic refund limit; "
                "the whole transaction must be escalated to a human (no partial refunds)")

    # 5. Under 30 days old, counted from the purchase date
    age_days = (TODAY - date.fromisoformat(txn["date"])).days
    if age_days >= REFUND_WINDOW_DAYS:
        return (f"transaction is {age_days} days old; automatic refunds are only for transactions "
                f"under {REFUND_WINDOW_DAYS} days old, so it must be escalated to a human")

    # 6. Amount is a valid positive number (bool is an int in Python, so exclude it)
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        return "refund amount must be a number"
    amount = round(float(amount), 2)
    if amount <= 0:
        return "refund amount must be greater than zero"

    # 7. Not more than the transaction amount
    if amount > txn["amount"]:
        return f"refund amount is more than the transaction amount of ${txn['amount']:.2f}"

    return None


def issue_refund(s, txn_id, amount):
    txn_id = str(txn_id).strip().upper()

    txn = s.transactions.get(txn_id)
    if txn is None:
        return _refuse("transaction not found")

    reason = _refund_block_reason(s, txn, amount)
    if reason is not None:
        return _refuse(reason)

    # All checks passed
    amount = round(float(amount), 2)
    refund_id = f"R{s.next_refund_num:03d}"
    s.next_refund_num += 1
    txn["status"] = "refunded"
    s.refunds.append({"refund_id": refund_id, "txn_id": txn_id, "amount": amount, "customer_id": txn["customer_id"]})
    return {"ok": True, "refund_id": refund_id}


def escalate_to_human(s, customer_id, summary):
    ticket_id = f"ESC-{s.next_ticket_num:04d}"
    s.next_ticket_num += 1
    s.escalations.append({"ticket_id": ticket_id, "customer_id": customer_id, "summary": summary})
    return {"ticket_id": ticket_id}
