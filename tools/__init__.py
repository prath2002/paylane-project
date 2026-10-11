"""Tool registry and a safe dispatcher for the agent loop."""

import json

from tools.api import Session, escalate_to_human, get_customer, get_transaction, issue_refund
from tools.schemas import TOOL_SCHEMAS

TOOL_FUNCS = {
    "get_customer": get_customer,
    "get_transaction": get_transaction,
    "issue_refund": issue_refund,
    "escalate_to_human": escalate_to_human,
}


def run_tool(session, name, arguments_json):
    """Run a tool by name. Always returns a JSON string and never raises."""
    func = TOOL_FUNCS.get(name)
    if func is None:
        return json.dumps({"error": f"unknown tool: {name}"})

    try:
        args = json.loads(arguments_json or "{}")
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "invalid JSON arguments"})
    if not isinstance(args, dict):
        return json.dumps({"error": "arguments must be a JSON object"})

    try:
        result = func(session, **args)
    except TypeError as e:
        return json.dumps({"error": f"bad arguments for {name}: {e}"})
    except Exception as e:  # last resort so one bad call never kills the conversation
        return json.dumps({"error": f"tool {name} failed: {e}"})
    return json.dumps(result)


__all__ = ["Session", "TOOL_SCHEMAS", "run_tool"]
