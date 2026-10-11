"""Paylane support agent: setup, agent loop, interactive CLI and scripted runner.

Usage:
    python main.py                      # interactive chat
    python main.py --script path.json   # run a scripted conversation
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from tools import TOOL_SCHEMAS, Session, run_tool

BASE_DIR = Path(__file__).parent
PROMPT_PATH = BASE_DIR / "prompts" / "system_prompt.md"
TRANSCRIPTS_DIR = BASE_DIR / "transcripts"

MAX_STEPS = 6  # max tool rounds per customer message
FALLBACK_REPLY = "Sorry, I couldn't finish that just now. Could you try again, or rephrase your request?"

# Set in setup()
client = None
model = None
system_prompt = ""


def setup():
    """Load env, build the OpenRouter client, read the system prompt. Exit cleanly on problems."""
    global client, model, system_prompt
    load_dotenv(BASE_DIR / ".env")

    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key or api_key == "your_key_here":
        print("OPENROUTER_API_KEY is not set. Copy .env.example to .env and add your key.")
        sys.exit(1)

    model = os.getenv("MODEL_NAME", "").strip()
    if not model or model == "your_model_here":
        print("MODEL_NAME is not set. Add it to .env (an OpenRouter model id, e.g. provider/model-name).")
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")


def new_history():
    return [{"role": "system", "content": system_prompt}]


def take_turn(messages, session, log):
    """Run the model until it replies with text. Tool calls are executed and fed back."""
    for _ in range(MAX_STEPS):
        response = client.chat.completions.create(model=model, messages=messages, tools=TOOL_SCHEMAS)
        msg = response.choices[0].message

        # Store the assistant message as a plain dict so history stays JSON-friendly
        assistant = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            assistant["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ]
        messages.append(assistant)

        if not msg.tool_calls:
            return msg.content or ""

        # Policy is enforced inside run_tool -> tools/api.py, not here
        for tc in msg.tool_calls:
            result = run_tool(session, tc.function.name, tc.function.arguments)
            log.append({"tool": tc.function.name, "args": tc.function.arguments, "result": result})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    log.append({"tool": None, "note": f"MAX_STEPS ({MAX_STEPS}) reached; returned fallback reply"})
    messages.append({"role": "assistant", "content": FALLBACK_REPLY})
    return FALLBACK_REPLY


def session_state(session):
    return {"refunds": session.refunds, "escalations": session.escalations}


def save_transcript(name, turns, session):
    TRANSCRIPTS_DIR.mkdir(exist_ok=True)
    path = TRANSCRIPTS_DIR / f"{name}.json"
    data = {"name": name, "model": model, "turns": turns, "final_state": session_state(session)}
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def print_tool_log(log):
    for entry in log:
        if entry.get("tool"):
            print(f"  [tool] {entry['tool']}({entry['args']}) -> {entry['result']}")
        else:
            print(f"  [note] {entry['note']}")


def run_conversation(customer_messages, name):
    """Run a scripted list of customer messages and save the transcript."""
    session = Session()
    messages = new_history()
    turns = []

    for text in customer_messages:
        print(f"\nCustomer: {text}")
        messages.append({"role": "user", "content": text})
        log = []
        try:
            reply = take_turn(messages, session, log)
        except Exception as e:  # network or API errors: stop the script but still save what we have
            print(f"  [error] model call failed: {e}")
            break
        print_tool_log(log)
        print(f"Agent: {reply}")
        turns.append({"customer": text, "tool_calls": log, "agent": reply})

    path = save_transcript(name, turns, session)
    print(f"\nTranscript saved to {path}")
    return turns


def chat_cli():
    """Interactive chat. Type 'quit' to exit."""
    session = Session()
    messages = new_history()
    turns = []
    print(f"Paylane support (model: {model}). Type 'quit' to exit.\n")

    while True:
        try:
            text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if text.lower() == "quit":
            break
        if not text:
            continue

        history_len = len(messages)
        messages.append({"role": "user", "content": text})
        log = []
        try:
            reply = take_turn(messages, session, log)
        except Exception as e:  # network or API errors: report and keep the chat alive
            print(f"  [error] model call failed: {e}")
            print_tool_log(log)  # tools may already have run (e.g. a refund) before the failure
            del messages[history_len:]  # drop the half-finished turn so history stays valid
            continue
        print_tool_log(log)
        print(f"Agent: {reply}\n")
        turns.append({"customer": text, "tool_calls": log, "agent": reply})

    if turns:
        path = save_transcript("chat", turns, session)
        print(f"Transcript saved to {path}")


def load_script(path):
    """A script is a JSON list of customer messages, or {"name": ..., "messages": [...]}."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return Path(path).stem, data
    return data.get("name", Path(path).stem), data["messages"]


def main():
    parser = argparse.ArgumentParser(description="Paylane support agent")
    parser.add_argument("--script", help="path to a JSON file of customer messages")
    args = parser.parse_args()

    setup()
    if args.script:
        try:
            name, customer_messages = load_script(args.script)
        except (OSError, json.JSONDecodeError, KeyError) as e:
            print(f"Could not read script {args.script}: {e}")
            sys.exit(1)
        run_conversation(customer_messages, name)
    else:
        chat_cli()


if __name__ == "__main__":
    main()
