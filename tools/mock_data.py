"""Fake customers and transactions for the Paylane prototype.

Do not mutate these dicts directly. Each Session takes a deep copy.
"""

CUSTOMERS = {
    "asha@example.com": {
        "id": "C001", "name": "Asha Rao", "card_last4": "4421", "status": "active",
    },
    "vikram@example.com": {
        "id": "C002", "name": "Vikram Shah", "card_last4": "9087", "status": "frozen",
        "frozen_reason": "Card frozen after a fraud alert on 2 Oct 2026.",  # added by us, see DECISIONS.md
    },
    "meera@example.com": {
        "id": "C003", "name": "Meera Iyer", "card_last4": "3350", "status": "active",
    },
}

TRANSACTIONS = {
    "T100": {"customer_id": "C001", "amount": 42.50,  "date": "2026-09-28", "merchant": "BlueCart",            "status": "settled"},
    "T101": {"customer_id": "C001", "amount": 120.00, "date": "2026-10-05", "merchant": "Skyline Tickets",     "status": "settled"},
    "T102": {"customer_id": "C001", "amount": 30.00,  "date": "2026-09-10", "merchant": "Metro Fuel",          "status": "settled"},  # exactly 30 days old
    "T103": {"customer_id": "C001", "amount": 18.00,  "date": "2026-10-08", "merchant": "Chai Corner",         "status": "refunded"},
    "T104": {"customer_id": "C001", "amount": 75.00,  "date": "2026-10-01", "merchant": "Desi Mart",           "status": "settled"},  # exactly the cap
    "T200": {"customer_id": "C002", "amount": 210.00, "date": "2026-10-01", "merchant": "Unknown Electronics", "status": "settled"},
    "T300": {"customer_id": "C003", "amount": 640.00, "date": "2026-10-07", "merchant": "LuxWatch Online",     "status": "settled"},  # fraud over $500
    "T301": {"customer_id": "C003", "amount": 25.00,  "date": "2026-10-09", "merchant": "Green Grocer",        "status": "pending"},
}
