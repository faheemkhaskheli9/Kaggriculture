---
description: Judge the pending ladder sub (Phase A+B) — episode count, exception sweep, win-rate vs animal_factory vs baseline, promote/retire/hold verdict + pre-filled LEDGER/State edits
---

Run **Phase A + Phase B** of `docs/LADDER_RUNBOOK.md` in isolation: decide what
the pending submission's ladder read *means* and produce the exact
promote / retire / hold action. This command does **not** build a candidate
(that's `/ladder` Phase C or `/ladder-teardown`) and **never** submits.
Obey `CLAUDE.md` § "Workflow rules (2026-09-06)".

Optional focus / explicit sub id for this run: $ARGUMENTS

## Why this exists

Every ladder misstep in the record is a *judging* error, not a build error:
routing-rejected was overturned as a 2-ep artifact; a 2026-09-04 audit found the
State facts had gone stale between cycles; the ML probe (202.5) sat in a live
rating slot misread as an agent; v8 / the ML probe were flat because `agent()`
was silently raising, not because the strategy was bad. The numeric comparison
that keeps going wrong is done by hand each cycle. This command makes it a
checklist with hard gates.

## Inputs

- `$BEST` — board-best sub id, from the **State table** in
  `docs/LADDER_RUNBOOK.md` ("Board-best sub" row), plus its recorded
  `vs animal_factory` score-rate (the baseline).
- `$PENDING` — the "Pending sub" row's id (or the id in `$ARGUMENTS` if given).
- Read `experiments/LEDGER.md` for the pending row and the reverted list.
- **Re-read both shared files immediately before writing to either** (Codex may
  be in the same tree).

## Steps

### Phase A — is `$PENDING` ready to judge?

```bash
python download_episodes.py --submissions $PENDING --refresh
python tools/ladder_analyze.py $PENDING
```

Report, before any verdict:

1. **Episode count** for `$PENDING`.
2. **Exception sweep** — grep the downloaded `logs/*.logs.json` for this sub for
   a bare `PASS` fallback / traceback / `Traceback`:
   ```bash
   grep -rlE "Traceback|\"PASS\"[^,]*fallback|agent\(\) raised" logs/ | head
   ```
   A silent `agent()` raise looks identical to a bad strategy. If found →
   **verdict = RETIRE-RAISING**: flag OFF, LEDGER note "silent raise, not a
   strategy read", `$BEST` stays baseline, go build. Stop here.
3. **Network / staleness check** — if `download_episodes.py` could not reach the
   Kaggle API, or the newest local episode for `$PENDING` predates its submit
   timestamp, say so explicitly and treat as **0 usable eps**.

Gate:
- **< 15 eps** → too thin to say anything. Verdict = **HOLD**. Do not touch the
  flag, the State table's baseline, or LEDGER beyond an ep-count note.
- **15–19 eps** → Verdict = **HOLD**, but you *may* note the provisional
  direction. **Never revert below 15 eps** (`CLAUDE.md`).
- **≥ 20 eps** → Phase B.

### Phase B — judge on the gate metric

Gate = **win-rate (score-rate) vs `animal_factory`**, from
`ladder_analyze.py`'s per-archetype block. `animal_factory` is ~56% of ladder
games and the worst matchup — mean, margin, and overall score-rate are **not**
the gate (Bradley-Terry discards margin).

1. Pull the same row for `$BEST` if not already downloaded:
   ```bash
   python download_episodes.py --submissions $BEST --refresh
   python tools/ladder_analyze.py $BEST
   ```
2. Compare `$PENDING`'s `vs animal_factory` score-rate against `$BEST`'s.
   Report both as `W-T-L / pct` and the delta.
3. Verdict:
   - **`$PENDING` ≥ `$BEST`** (within noise, treat ties/±1 game as ≥) →
     **PROMOTE**. Keep the flag ON. The candidate file
     `agents/main_v<NN>_<name>.py` mirrors into `main.py` **verbatim** — output
     the exact hunk to copy, or confirm `main.py` already equals it. Commit
     message stub included. State: Pending → Board-best; clear "Pending sub".
   - **`$PENDING` < `$BEST`** → **RETIRE**. Flag OFF (name the revert commit
     point). Candidate stays in `agents/`. `$BEST` retained as baseline.
   - Either way, the next step is Phase C (`/ladder-teardown` then `/ladder`).

### Submission-cap accounting (always run)

Independent of the verdict, report the day's budget so the next `/ladder`
Phase D knows the slot state:

```bash
kaggle competitions submissions kaggriculture | head -15
```

- Count **today's** submissions across **all** slugs/models (check LEDGER +
  `commands.txt` for same-day subs on other slugs too).
- Hard caps: **≤ 5 total/day**, **≤ 2 experiment agents/day** (anything not the
  promoted `main.py` on the real `kaggriculture` slug).
- State the tracked pair (Kaggle keeps only the latest 2) and which sub a new
  submit would evict.

## Output

End with, in this order:

1. **Verdict** — one of `HOLD` / `PROMOTE` / `RETIRE` / `RETIRE-RAISING`, with
   the ep count and the `vs animal_factory` delta that drives it.
2. **Pre-filled `experiments/LEDGER.md` row** for `$PENDING` (change → local →
   ladder → status) — ready to paste after a re-read.
3. **Pre-filled `docs/LADDER_RUNBOOK.md` State-table edits** — the exact new
   "Board-best sub" / "Pending sub" / "Last judged" / "Clean main-slot reads
   left" cell values.
4. **On PROMOTE only** — the `main.py` hunk to mirror + a commit message stub
   (no `Co-Authored-By`, per repo rule).
5. **Submission budget** — subs used today, experiment subs used today, tracked
   pair, next eviction.
6. **Single next action** — normally `/ladder-teardown` (or `/ladder` if a
   candidate is already queued in State).
7. **Pre-filled `experiments/AGENT_MISTAKES.md` edits** — the section-B row for
   `$PENDING` (ladder now, verdict, section-C code if the read was inside the
   noise band) and the new status of the section-A mistake it targeted.

Do **not** run `kaggle competitions submit`. Do **not** edit `main.py`,
`LEDGER.md`, or the State table without re-reading them first in the same
sitting; if `/ladder` is mid-run in this tree, only report the verdict and let
it apply the edits.
