---
description: Rank mechanical (not economy) gaps vs the board-best + top-10 to pick the next ladder change
---

Run Phase C step 1–2 of `docs/LADDER_RUNBOOK.md` in isolation: produce a
**ranked list of mechanical gaps** to feed the next `ENABLE_<NAME>` candidate.
This command does not build, gate, commit, or submit — it only decides *what is
worth building*. Obey `CLAUDE.md` § "Workflow rules (2026-09-06)".

Optional focus for this run: $ARGUMENTS

## Why this exists

Every economy/crop change in the ladder record failed to gate or was reverted
(wedge zones, market maker, sparse watering ×3, CARE-as-task, opportunistic
fertilize, per-day herd cap, B3 cash guard, P2k prune). The only changes that
ever moved the ladder were mechanical: the feed-floor bug fix (→574.6) and
routing + MAXHANDS-12 (→605.1). With ~5–7 clean main-slot reads left before
2026-09-30, the pick has to be a high-EV mechanical change every time.

## Steps

1. Read the **State table** in `docs/LADDER_RUNBOOK.md` to get the current
   board-best sub id (call it `$BEST`) and `experiments/LEDGER.md` for what has
   already been tried + reverted. Do not re-propose anything on that reverted
   list.

2. **Exception sweep first.** For `$BEST` and any pending sub, grep the
   downloaded `logs/*.logs.json` for a bare `PASS` fallback / traceback. A
   silent `agent()` raise looks identical to a bad strategy — if found, the
   "gap" is the bug; stop and report that.
   ```bash
   python download_episodes.py --submissions $BEST --refresh
   ```

3. **Our-agent diagnosis.** Loss buckets, lead-flip day, and per-game
   movement / plant / weed / animal / sell diagnostics for `$BEST`:
   ```bash
   python tools/ladder_analyze.py $BEST
   python tools/trace_crater.py $BEST --n 40
   python tools/trace_cashflow.py $BEST --arch animal_factory --n 8
   ```

4. **Top-10 comparison.** Pull the leaderboard's replays and reduce them to the
   same mechanical stats, then diff against ours:
   ```bash
   python download_top_replays.py --top 10
   python tools/analyze_top.py --detail
   ```
   Compare on: movement % of unit-actions, idle-hand turns, market-order-slot
   fill rate + priority order, routing detour length, weeds/turn, animal
   escapes, HIRE cadence, final-day liquidation completeness.

5. **Emit the ranked table.** 3–6 rows, most-attributable first. Each row:

   | gap | evidence (our stat vs top-10) | mechanical fix sketch | est. attributable EV | risk / worst-case margin |

   Rules for the table:
   - **Mechanical only** — movement, routing, slot priority, idle labour,
     liquidation, a bug. Reject every economy/crop/reserve-tuning idea; if the
     only gaps you find are economic, say so and recommend not spending a slot.
   - Each fix must be expressible as one `ENABLE_<NAME>` hunk + named config in
     a new `agents/main_v<NN>_<name>.py` (mirror into `main.py` only on
     promote). Note the flag name you'd use.
   - EV estimate is relative to the `vs animal_factory` score-rate row
     (`animal_factory` is ~56% of ladder games and the worst matchup) — that is
     the gate metric, not mean or margin.
   - If a gap's expected gain is not large, mark it **below submit bar** — per
     CLAUDE.md those are ask-user-first, not auto-queued.

6. Recommend the single top row as the next queued change, or explicitly
   recommend holding the slot if nothing clears the bar.

7. Check every gap against `experiments/AGENT_MISTAKES.md` first: skip gaps
   whose section-A row is `CLOSED`/`WONTFIX`, and cite the prior section-B
   attempts for any `OPEN` row. Give the pre-filled section-A row (evidence +
   est. cost/game) for each new gap so `/ladder` can add it.

End with: the ranked table, the one recommended pick (or "hold"), and the exact
`/ladder` invocation to build it. Do **not** edit `main.py`, `LEDGER.md`, or the
State table — `/ladder` owns those.
