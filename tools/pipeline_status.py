"""Mechanical status check for the submit -> wait -> analyze -> decide loop.

Run this at the top of every pipeline cycle. It answers three questions:

1. Is there a tracked submission with >=20 episodes that hasn't been marked
   analyzed yet? (a "read is ready" signal)
2. Are we clear to submit today? (last submission's date != today, per the
   one-submission-per-day discipline in CLAUDE.md / TASKS.md)
3. What are the two current tracked submissions and their episode counts?

State (which submissions have already been analyzed/decided) is kept in
experiments/pipeline_state.json so re-running this doesn't re-flag the same
read every cycle. Call `mark_analyzed(sub_id)` (or edit the JSON) once a read
has been turned into a keep/revert decision + LEDGER/TASKS update.

This script does NOT decide keep/revert and does NOT submit anything -- it
only reports state. The actual decision needs judgment (win-rate vs prior,
which archetype moved, whether the change is confounded) and stays with
whoever/whatever is driving the loop.
"""
import csv
import datetime
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "experiments" / "pipeline_state.json"
INDEX_CSV = ROOT / "episodes" / "index.csv"
KAGGLE_PY = r"C:\Users\LENOVO\AppData\Local\Programs\Python\Python313\python.exe"
READ_THRESHOLD = 20


def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"analyzed_submissions": [], "last_submit_date": None}


def save_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=2))


def get_submissions():
    """Return list of dicts: ref, fileName, date, status, publicScore -- newest first."""
    out = subprocess.run(
        [KAGGLE_PY, "-m", "kaggle", "competitions", "submissions",
         "kaggriculture", "-v"],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    rows = list(csv.DictReader(out.stdout.splitlines()))
    return rows


def episode_count(sub_id):
    if not INDEX_CSV.exists():
        return 0
    n = 0
    with open(INDEX_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("submission_ref") == str(sub_id):
                n += 1
    return n


def main():
    state = load_state()
    subs = get_submissions()
    today = datetime.date.today().isoformat()

    print(f"=== pipeline status @ {today} ===")

    if not subs:
        print("Could not read submissions (kaggle CLI issue) -- check manually.")
        sys.exit(1)

    tracked = subs[:2]  # latest-2 discipline
    print("\nTracked (latest 2) submissions:")
    ready = []
    for row in tracked:
        sid = row["ref"]
        n_eps = episode_count(sid)
        analyzed = sid in state["analyzed_submissions"]
        flag = "READY-FOR-READ" if (n_eps >= READ_THRESHOLD and not analyzed) else (
            "analyzed" if analyzed else f"waiting ({n_eps}/{READ_THRESHOLD} eps)")
        print(f"  {sid}  {row['fileName']:<20} score={row.get('publicScore','?'):<8} "
              f"eps={n_eps:<3} {flag}")
        if n_eps >= READ_THRESHOLD and not analyzed:
            ready.append(sid)

    last_submit_date = tracked[0]["date"][:10] if tracked else None
    can_submit_today = last_submit_date != today
    print(f"\nLast submission date: {last_submit_date}  "
          f"-> {'CLEAR to submit today' if can_submit_today else 'already submitted today, wait'}")

    if ready:
        print(f"\n>>> ACTION: run `python tools/ladder_analyze.py {ready[0]}` "
              f"and compare vs the other tracked submission, then update "
              f"experiments/LEDGER.md + TASKS.md with keep/revert.")
    else:
        print("\n>>> No read ready yet. Nothing to decide this cycle.")

    if can_submit_today and not ready:
        print(">>> Slot is free and no pending read -- safe to prep+submit the next queued change.")

    state["last_checked"] = today
    save_state(state)


if __name__ == "__main__":
    main()
