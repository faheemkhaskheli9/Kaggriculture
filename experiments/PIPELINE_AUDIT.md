STATUS: IN_PROGRESS
PIPELINE_HASH: ce70a02442335d08e78dc15c72497221e35db7bc
LAST_RUN: 2026-09-08 (P0.4 done — archetype classifiers agree on the animal_factory bucket)

Plan: docs/PLAN_PIPELINE_AUDIT.md. `/ladder-auto` Phase P0 runs the next `[ ]`
section per iteration (subagent, terse return), applies mechanical fixes,
ticks the box. No agent-improvement build or new-candidate submission until
STATUS: PASS with a matching PIPELINE_HASH.

## Sections
- [x] P0.1 PASS — BUG found+fixed: live agent() except swallowed every raise silently (no stderr/sentinel) → indistinguishable from bad strategy on Kaggle debug=False. Added `traceback.print_exc()` durable marker + `import traceback`. Items 2/3/4 verified clean (fallback schema-valid; module level all literals/defs; hot path Hungarian O(A·(C+A)²), C≤96 tiles A≤40 units, well under 1s). Regression guard: post-run `grep -RIl "Traceback (most recent call last)" compete_runs/<stamp>/*.logs.json` must be empty before submit. Commit below.
- [x] P0.2 PASS — stock config all verified (episodeSteps 720 / actTimeout 1 / startingMoney 3000 / turnsPerDay 24 / maxMarketOrdersPerTurn 10 == engine JSON defaults; `debug=False` on the ladder path, `--debug` store_true default False; seat = per-game `rng.randint(0,1)` ~50/50; seed per-game 9-digit random, recorded to manifest + replay filename; `agents/*.py` + `contenders/c_*.py` globbed correctly). **BUG found+fixed:** `DEFAULT_POOL` was a hand-maintained list that silently omitted committed strong opponents `bots/bot_factory_v3.py` (real-ladder-mined animal_factory proxy) and `bots/bot_top10clone.py` (2850-3010-rated clone) — the gate was missing its two most ladder-representative opponents, a prime suspect for locally-clean changes gating flat on the ladder. Fix: `DEFAULT_POOL` now globs `bots/bot_*.py`; added an `assert _disk_bots <= set(DEFAULT_POOL)` regression guard; committed `bot_factory_v3.py` (was untracked). Commit `9e279df`. Smoke: both bots load & play 0-err.
- [x] P0.3 PASS — score-rate is `(W + 0.5·T)/n` **identically** in `analyze_runs.py:256` (`_rate`) and `ladder_analyze.py:157`; no local/ladder metric mismatch. WIN/TIE/LOSS logic consistent: both compare final reward (== `farm["money"]`) with strict `>` / `<`, exact equality → TIE (maps to Kaggle Bradley-Terry win/loss/tie; coin-margin 0 → TIE in both). Crash games: `compete.py` writes `result="CRASH"` / `margin=0.0` / `errored=True`; `analyze_runs.py._wtl` counts CRASH as neither W/T/L but keeps it in `len(rows)` → effectively a loss (0.0) in score-rate — **conservative, no inflation**; `errors=` surfaces them separately. `n` is never corrupted. Two limits documented below (neither inflates the gate). No code change; doc-only.
- [x] P0.4 PASS — the two tools that bucket by archetype agree exactly. `analyze_runs.py:112-133` `classify_opp` and `ladder_analyze.py:88-107` `classify_opp` are behaviorally identical (only line-wrapping differs): same 7-branch order, animal_factory = `amax>=4 and (FERT+MILK+WOOL)/tot_sells > 0.3`. Both classify **purely from the opponent's replay trajectory** (`ot`/`oa` = animals/plants/sells over days 0-29), never from filename or agent name — so a local `bot_animalfactory_v2` game and a real ladder `animal_factory` game go through the *same behavioral test*; local↔ladder "vs animal_factory" rows are comparable by construction. `classify_ladder.py` is NOT a classifier (hardcoded `SUB="55952982"`, tags games with raw `opp_anim/opp_plants` ints, never emits an animal_factory row → cannot disagree). `other` is a real labeled bucket kept in W/T/L totals + the per-arch dict (`ladder_analyze.py:161-165`); the "vs animal_factory" denominator is legitimately just af-classified games in both tools (symmetric). Replay-load failures `continue` out of *all* buckets in both — no af-specific denominator shrink. No code change. 2 limits below.
- [ ] P0.5  paired A/B is actually paired + CI is real  (compete.py A/B, analyze_runs.py)
- [ ] P0.6  replay miners read the right fields  (trace_crater / trace_cashflow / analyze_top / ladder_analyze)
- [ ] P0.7  data pulls complete + fresh  (download_episodes.py, download_top_replays.py)
- [ ] P0.8  loop bookkeeping self-consistent  (LEDGER / AUTO_IDEAS / RUNBOOK State / pipeline_state.json)

## NEEDS USER
(none)

## Documented limits (not bugs)
- **P0.3: CRASH-denominator mismatch between tools (cosmetic).** `compete.py`'s own
  stdout summary excludes CRASH games from the score-rate denominator (`decided =
  [r for r in rows if r["result"] != "CRASH"]`, line 332/360), while
  `analyze_runs.py` — the tool the loop actually gates on — includes them (counts
  as a loss). The gating path is the conservative one; the discrepancy only
  affects compete.py's console print, not any promote/revert decision.
- **P0.3: partial-errored games keep a money-based W/T/L.** A game where a player
  errored mid-run but the engine still finished (`errored=True`, `result` !=
  `CRASH`) is scored by the final coin comparison, not force-counted as a loss.
  Rare; the end-of-game coin delta already reflects the damage. `errors=` still
  flags the game for the exception sweep.
- **P0.4: `classify_opp` is duplicated verbatim in `analyze_runs.py` and `ladder_analyze.py`.**
  Currently byte-identical in behavior; future edits could drift them apart and
  silently make local vs ladder "vs animal_factory" rows non-comparable. Not a
  bug today. If either is edited, mirror the change or factor to one module.
- **P0.4: classification is behavioral, so a hybrid bot can miss the animal_factory bucket.**
  `bot_factory_v3.py` (14-head herd + melon/wheat/strawberry field) may land in
  `wheat_flood`/`other` rather than `animal_factory` if its FERT+MILK+WOOL sell
  fraction is ≤0.30 or `pmax`>25. Acceptable: the identical test is applied to
  ladder replays, so local and ladder rows stay internally comparable — a
  mis-bucketed local bot just doesn't contribute to the local af rate.
- **No local opponent reproduces the real-ladder animal_factory mid-game cash crater.** P0.2 smoke: `main.py` beats the purpose-built `bot_factory_v3` (mined from the 12 real animal_factory losses on sub 56029879) **3-0 / +68k avg margin / score 100%**, and beats `bot_top10clone` (2850-3010-rated config) +88k. The bots' own docstrings concede the scripted engine "isn't a real 2850 agent and can't ride the escape spiral". Consequence for the loop: a Class-2 A/B on the diverse pool measures self-play + weak-archetype performance, NOT the loss mechanism the teardowns name. Adding these two bots to the pool (P0.2 fix) closes the *omission*, not the *fidelity* gap. Recorded also in knowledge-base/07.
