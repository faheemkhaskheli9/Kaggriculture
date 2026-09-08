STATUS: IN_PROGRESS
PIPELINE_HASH: f2d73e6cc54e96f9eddbc192f7e9ae52c322d2fa
LAST_RUN: 2026-09-08 (P0.1 done — main.py crash-marker fix, hash bumped)

Plan: docs/PLAN_PIPELINE_AUDIT.md. `/ladder-auto` Phase P0 runs the next `[ ]`
section per iteration (subagent, terse return), applies mechanical fixes,
ticks the box. No agent-improvement build or new-candidate submission until
STATUS: PASS with a matching PIPELINE_HASH.

## Sections
- [x] P0.1 PASS — BUG found+fixed: live agent() except swallowed every raise silently (no stderr/sentinel) → indistinguishable from bad strategy on Kaggle debug=False. Added `traceback.print_exc()` durable marker + `import traceback`. Items 2/3/4 verified clean (fallback schema-valid; module level all literals/defs; hot path Hungarian O(A·(C+A)²), C≤96 tiles A≤40 units, well under 1s). Regression guard: post-run `grep -RIl "Traceback (most recent call last)" compete_runs/<stamp>/*.logs.json` must be empty before submit. Commit below.
- [ ] P0.2  local gate config == Kaggle stock config  (compete.py)
- [ ] P0.3  W/T/L / score-rate math  (analyze_runs.py, ladder_analyze.py)
- [ ] P0.4  archetype classifier agreement  (analyze_runs / ladder_analyze / classify_ladder)
- [ ] P0.5  paired A/B is actually paired + CI is real  (compete.py A/B, analyze_runs.py)
- [ ] P0.6  replay miners read the right fields  (trace_crater / trace_cashflow / analyze_top / ladder_analyze)
- [ ] P0.7  data pulls complete + fresh  (download_episodes.py, download_top_replays.py)
- [ ] P0.8  loop bookkeeping self-consistent  (LEDGER / AUTO_IDEAS / RUNBOOK State / pipeline_state.json)

## NEEDS USER
(none)

## Documented limits (not bugs)
(none yet)
