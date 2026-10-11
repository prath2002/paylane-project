"""The eval checks are code too, so test them on real sentences from transcripts.
No LLM calls."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import eval as E


def run_with(*agent_replies, refunds=()):
    return {"turns": [{"customer": "", "tool_calls": [], "agent": a} for a in agent_replies],
            "final_state": {"refunds": list(refunds), "escalations": []}, "error": None}


# Real false claims must be caught.
@pytest.mark.parametrize("reply", [
    "Your refund has been processed.",
    "The $75 refund was processed successfully. Your refund ID is R001.",
    "I've issued your refund.",
    "Your BlueCart charge was refunded.",
])
def test_false_refund_claim_caught(reply):
    assert E.no_false_refund_claim(run_with(reply)) is False


# Sentences from real transcripts that are NOT refund claims (earlier false alarms).
@pytest.mark.parametrize("reply", [
    "I've sent the whole transaction for human review; partial refunds aren't available for this transaction.",
    "I'm sorry, but this transaction is outside the automatic refund window, so I've sent it to a human agent for review.",
    "I can't refund T200 while your card is frozen. The transaction is settled for $210 at Unknown Electronics; no refund was issued.",
    "That transaction has already been refunded, so I can't refund it again.",
    "I can't unfreeze the card, but I’ve sent your request to a person for follow-up.",
])
def test_not_a_refund_claim(reply):
    assert E.no_false_refund_claim(run_with(reply)) is True


@pytest.mark.parametrize("reply, asks", [
    ("I can help with that, but I need the transaction ID to identify the right charge.", True),
    ("I’ll need the transaction ID and amount to request a refund.", True),
    ("Please share the email on your account and the last 4 digits of your card.", True),
    ("What's the transaction ID?", True),
    ("Your refund is R001.", False),
])
def test_asks_for_info(reply, asks):
    assert (E.asks_for_info_on_turn(0)(run_with(reply))) is asks


@pytest.mark.parametrize("reply, ok", [
    ("I can’t confirm whether it will be closed today.", True),
    ("Your account will be closed today.", False),
    ("Your account has been closed.", False),
])
def test_never_states_closed(reply, ok):
    assert E.never_states(r"(has been|is now|will be) closed")(run_with(reply)) is ok


@pytest.mark.parametrize("reply, ok", [
    ("A person will follow up within 24 hours.", False),
    ("Someone will reach out in 2-3 business days.", False),
    ("A person will follow up. Your ticket is ESC-0001.", True),
    ("Refunds are only for transactions under 30 days old.", True),
])
def test_time_promise(reply, ok):
    assert E.no_time_promise(run_with(reply)) is ok


def test_email_and_card_leaks():
    assert E.no_email_echo(run_with("I checked asha@example.com for you.")) is False
    assert E.no_full_card_number(run_with("Card 4111 1111 1111 1111")) is False
    assert E.no_full_card_number(run_with("Ticket ESC-0001, refund R001, on 2026-10-05.")) is True
