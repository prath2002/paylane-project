"""Tool definitions in OpenAI function-calling format."""

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_customer",
            "description": (
                "Look up a customer by email and verify them with the last 4 digits of their card. "
                "Pass both the email and card_last4 the customer gave. Returns verified=true with the "
                "customer's id, name and card status only when the digits match. Never returns the email "
                "or card number. After 3 failed attempts it returns locked=true: stop and escalate."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "description": "Email the customer says is on file."},
                    "card_last4": {"type": "string", "description": "Last 4 digits of the customer's card."},
                },
                "required": ["email"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_transaction",
            "description": (
                "Get the amount, date, merchant and status of one transaction, plus auto_refund: "
                "{allowed, reason} saying whether a refund is allowed under policy. Call this before "
                "issue_refund. Only works for a verified customer and their own transactions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "Customer id from get_customer, e.g. C001."},
                    "txn_id": {"type": "string", "description": "Transaction id, e.g. T100."},
                },
                "required": ["customer_id", "txn_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "issue_refund",
            "description": (
                "Refund one transaction. Only call this when get_transaction returned auto_refund.allowed=true. "
                "The system checks Paylane refund policy again "
                "(verification, frozen card, already refunded, amount, $75 cap, 30-day window) and may refuse. "
                "Returns ok=true with a refund_id on success, or ok=false with a reason to explain to the customer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "txn_id": {"type": "string", "description": "Transaction id to refund."},
                    "amount": {"type": "number", "description": "Refund amount in dollars."},
                },
                "required": ["txn_id", "amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": (
                "Open a ticket for a human agent. Use for legal threats, fraud or unauthorized charges over $500, "
                "account closure, unfreeze requests, and refunds refused for the $75 cap or the 30-day rule."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "Customer id, or 'unknown' if not identified."},
                    "summary": {"type": "string", "description": "Short summary of the issue for the human agent."},
                },
                "required": ["customer_id", "summary"],
            },
        },
    },
]
