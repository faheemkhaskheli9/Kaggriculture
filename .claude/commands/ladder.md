---
description: Run one iteration of the Kaggriculture ladder loop (teardown → build → gate → queue)
---

Execute the ladder loop in `docs/LADDER_RUNBOOK.md`. Follow it exactly and obey
`CLAUDE.md` § "Workflow rules (2026-09-06)".

Optional focus for this run: $ARGUMENTS

Steps:

1. Read `docs/LADDER_RUNBOOK.md` (State table + the loop) and
   `experiments/LEDGER.md`. Re-read before writing to either shared file.
2. **Phase A** — check the pending sub's episode count and early logs for a
   silent all-PASS. Report: episode count, gate-metric row vs the board-best
   baseline, and which phase we're in.
3. Then:
   - Pending sub **not ready** (<20 eps) → do **Phase C**: run the teardown
     commands, propose ONE mechanical change (not economy/crop), and — only if
     I approve the pick — implement it behind `ENABLE_<NAME>` (default OFF) in a
     new `agents/main_v<NN>_<name>.py`, local-gate for regression only, commit,
     add to the State table. Do **not** submit.
   - Pending sub **ready** (≥20 eps) → do **Phase B**: judge on win-rate vs
     `animal_factory`, then promote-or-retire per the runbook, update State +
     LEDGER.
   - Pending sub **raising** → retire it, flag OFF, LEDGER note, move to Phase C.
4. Update the State table in `docs/LADDER_RUNBOOK.md` in the same sitting.
5. Never run `kaggle competitions submit` — submission needs explicit user
   approval and is Phase D only.

End with: current phase, what changed, and the single next action.
