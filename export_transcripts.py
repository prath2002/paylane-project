"""Turn eval run files into one readable TRANSCRIPTS.md (run 1 of each conversation,
plus the baseline 'before' transcripts for the failures that were fixed)."""

import json
from pathlib import Path

BASE = Path(__file__).parent
FINAL = BASE / "eval_results" / "final"
BASELINE = BASE / "eval_results" / "baseline"


def render(rec, heading):
    out = [f"## {heading}", "", f"_Why this case:_ {rec['why']}", ""]
    for t in rec["turns"]:
        out.append(f"**Customer:** {t['customer']}  ")
        for c in t["tool_calls"]:
            if c.get("tool"):
                out.append(f"> `{c['tool']}({c['args']})` → `{c['result']}`  ")
        out.append(f"**Agent:** {t['agent'].replace(chr(10), ' ')}")
        out.append("")
    st = rec["final_state"]
    out.append(f"_Final state:_ refunds {[(r['txn_id'], r['amount']) for r in st['refunds']] or 'none'}, "
               f"escalations {[e['ticket_id'] for e in st['escalations']] or 'none'}  ")
    failed = [c["check"] for c in rec["checks"] if not c["pass"]]
    out.append(f"_Checks:_ {'all ' + str(len(rec['checks'])) + ' passed' if not failed else 'FAILED: ' + '; '.join(failed)}")
    out += ["", "---", ""]
    return out


lines = ["# Transcripts", "",
         "Run 1 of each conversation from the final eval (`eval_results/final/`). Tool calls are shown as quotes.",
         "All runs, including runs 2 and 3, are in `eval_results/final/*.json`.", "",
         "Today's date in the mock is fixed at 2026-10-10.", ""]
for path in sorted(FINAL.glob("*__run1.json")):
    rec = json.loads(path.read_text(encoding="utf-8"))
    lines += render(rec, rec["name"])

lines += ["# Before the fix (baseline)", "",
          "The same conversations run on the agent before the fixes in FAILURES.md.", ""]
for name in ["03_over_cap_pushback", "08_verification_guessing", "04_thirty_day_boundary"]:
    rec = json.loads((BASELINE / f"{name}__run1.json").read_text(encoding="utf-8"))
    lines += render(rec, f"BEFORE: {name}")

(BASE / "TRANSCRIPTS.md").write_text("\n".join(lines), encoding="utf-8")
print("wrote TRANSCRIPTS.md")
