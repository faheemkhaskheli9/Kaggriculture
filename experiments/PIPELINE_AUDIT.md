STATUS: IN_PROGRESS
PIPELINE_HASH: e81c8602318f1f8c6242b1c83a603065280b6174
LAST_RUN: 2026-09-09 (P0.7 done — partial/truncated download now detected + deleted in both download_episodes.py & download_top_replays.py; incremental-skip replay check now size-gated. P0.8 remains)

Plan: docs/PLAN_PIPELINE_AUDIT.md. `/ladder-auto` Phase P0 runs the next `[ ]`
section per iteration (subagent, terse return), applies mechanical fixes,
ticks the box. No agent-improvement build or new-candidate submission until
STATUS: PASS with a matching PIPELINE_HASH.

## Sections
- [x] P0.1 PASS — BUG found+fixed: live agent() except swallowed every raise silently (no stderr/sentinel) → indistinguishable from bad strategy on Kaggle debug=False. Added `traceback.print_exc()` durable marker + `import traceback`. Items 2/3/4 verified clean (fallback schema-valid; module level all literals/defs; hot path Hungarian O(A·(C+A)²), C≤96 tiles A≤40 units, well under 1s). Regression guard: post-run `grep -RIl "Traceback (most recent call last)" compete_runs/<stamp>/*.logs.json` must be empty before submit. Commit below.
- [x] P0.2 PASS — stock config all verified (episodeSteps 720 / actTimeout 1 / startingMoney 3000 / turnsPerDay 24 / maxMarketOrdersPerTurn 10 == engine JSON defaults; `debug=False` on the ladder path, `--debug` store_true default False; seat = per-game `rng.randint(0,1)` ~50/50; seed per-game 9-digit random, recorded to manifest + replay filename; `agents/*.py` + `contenders/c_*.py` globbed correctly). **BUG found+fixed:** `DEFAULT_POOL` was a hand-maintained list that silently omitted committed strong opponents `bots/bot_factory_v3.py` (real-ladder-mined animal_factory proxy) and `bots/bot_top10clone.py` (2850-3010-rated clone) — the gate was missing its two most ladder-representative opponents, a prime suspect for locally-clean changes gating flat on the ladder. Fix: `DEFAULT_POOL` now globs `bots/bot_*.py`; added an `assert _disk_bots <= set(DEFAULT_POOL)` regression guard; committed `bot_factory_v3.py` (was untracked). Commit `9e279df`. Smoke: both bots load & play 0-err.
- [x] P0.3 PASS — score-rate is `(W + 0.5·T)/n` **identically** in `analyze_runs.py:256` (`_rate`) and `ladder_analyze.py:157`; no local/ladder metric mismatch. WIN/TIE/LOSS logic consistent: both compare final reward (== `farm["money"]`) with strict `>` / `<`, exact equality → TIE (maps to Kaggle Bradley-Terry win/loss/tie; coin-margin 0 → TIE in both). Crash games: `compete.py` writes `result="CRASH"` / `margin=0.0` / `errored=True`; `analyze_runs.py._wtl` counts CRASH as neither W/T/L but keeps it in `len(rows)` → effectively a loss (0.0) in score-rate — **conservative, no inflation**; `errors=` surfaces them separately. `n` is never corrupted. Two limits documented below (neither inflates the gate). No code change; doc-only.
- [x] P0.4 PASS — the two tools that bucket by archetype agree exactly. `analyze_runs.py:112-133` `classify_opp` and `ladder_analyze.py:88-107` `classify_opp` are behaviorally identical (only line-wrapping differs): same 7-branch order, animal_factory = `amax>=4 and (FERT+MILK+WOOL)/tot_sells > 0.3`. Both classify **purely from the opponent's replay trajectory** (`ot`/`oa` = animals/plants/sells over days 0-29), never from filename or agent name — so a local `bot_animalfactory_v2` game and a real ladder `animal_factory` game go through the *same behavioral test*; local↔ladder "vs animal_factory" rows are comparable by construction. `classify_ladder.py` is NOT a classifier (hardcoded `SUB="55952982"`, tags games with raw `opp_anim/opp_plants` ints, never emits an animal_factory row → cannot disagree). `other` is a real labeled bucket kept in W/T/L totals + the per-arch dict (`ladder_analyze.py:161-165`); the "vs animal_factory" denominator is legitimately just af-classified games in both tools (symmetric). Replay-load failures `continue` out of *all* buckets in both — no af-specific denominator shrink. No code change. 2 limits below.
- [x] P0.5 PASS — `compete.py --baseline` paired mode is a correctly paired design; no code change. **Pairing (compete.py:574-579):** the baseline arm is built as `dict(payload, agent_path=baseline_path, save_dir=baseline_dir)` for each candidate game — it reuses that game's exact `opponent`, `seed`, and `our_seat`, overriding only the agent file; `paired_summary` (compete.py:377-379) hard-asserts every pair aligns on `(opponent, seed, our_seat)` and raises otherwise. **CI (compete.py:387, 405-408, 423-424):** `score_delta = score_value(cand) - score_value(base)` is a per-pair difference; the bootstrap resamples those per-pair deltas with replacement, means each replicate, reports 5th/95th pctile → a proper paired-difference bootstrap CI, not two independent proportion CIs, not unpaired two-sample. **n (compete.py:404, 423):** `count = len(pairs)`, one unit per game per arm (not 2×); a CRASH in either arm drops the whole pair; bootstrap draws `len(deltas)` per replicate so variance is over the pair count. `analyze_runs.py --compare` is an unpaired per-opponent W/T/L side diagnostic with no CI of its own — the runbook's "CI[…]" numbers come only from `compete.py print_paired_summary`. Conclusion: "CI crosses 0" on recent A/Bs is a genuinely small effect vs noise, not a broken test throwing away power.
- [x] P0.6 PASS — all field reads, seat id, day/hour indexing verified correct against raw replays (hand cross-checks: trace_crater d0 disc tool=−2690/hand=−2690 & d10 money 1400=1400; trace_cashflow d10 cash 1400=1400; analyze_top step-math-free, day/hour/weeds fields ✓; ladder_analyze d10 money via `steps[i][0]` == seat path 1400=1400). Step→day is `k//24`, hour `k%24`, no off-by-one anywhere. `obs.farms` is the shared full list so `steps[i][0][...]["farms"][seat]` == `steps[i][seat][...]` (verified). Seat id via `info.Agents[].Name` vs `ME_NAMES` correct on every sampled replay. "hour 0 money" = start-of-day (after prior night's `_end_of_day`); no overnight money settlement exists; definition consistent across all four tools. Weeds = `kind=="WEED"` in both counters. **BUG (methodological) found + fixed:** `move%` was computed two incompatible ways — `analyze_top.py` (PASS in denominator, farmer excluded → 60.2% on test replay) vs `ladder_analyze.py` (PASS excluded, farmer included → 64.2% same replay) → systematic ~4pt inflation of our number vs top-10. Had NOT flipped a decision (teardown "63 vs 48" gap is 15pt >> 4pt artifact, direction unchanged) but future close comparisons weren't apples-to-apples. Fix: aligned `analyze_top.py analyze_farm` to the ladder_analyze convention (include farmer unit, skip PASS) + `assert "PASS" not in hand_token_counts` regression guard. Commit below. Smoke: analyze_top runs clean, assert holds.
- [x] P0.7 PASS — claims 1 (`--refresh` re-pulls, not a no-op), 2 (incremental keys on episode id, re-queries full list, doesn't skip new eps), 3 (Py3.13 invocation correct — `from __future__ import annotations` makes `list[str]` hints inert, no version gate, Python313 path ahead of `python3` in the interpreter-candidate list) all verified clean by static read. **BUG found + fixed (claim 4):** a partial/truncated download was NOT detected — both scripts confirmed a replay/log only via `Path(...).exists()`, no size or JSON-parse check, no temp+rename. A mid-transfer TCP reset (or any CLI failure leaving bytes on disk) wrote a short file to the final path; the failing run only printed a warning and left it, then every later incremental run saw it as present, set `need_replay=False`, and permanently indexed the stub as a legitimate episode → the "truncated pull → premature 20-ep read" failure. Fix: added `_valid_json(path)` to both scripts (size ≥ 2 B **and** `json.loads` parses, else `unlink()` the stub) — `download_replay`/`download_logs` (download_episodes.py) and `download()` (download_top_replays.py) now return False on a partial pull so the next run re-fetches; `replay_present()` incremental-skip check is now size-gated (`_MIN_REPLAY_BYTES = 100_000`; real env-dump replays are >4 MB) so pre-existing stubs are also re-pulled. Regression guard: module-level `assert _valid_json(<missing path>) is False` in both. Smoke: both import clean under Py3.13, guards hold. Commit below.
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
- **P0.6: `trace_crater.py` day_spend assumes every emitted order committed.** HIRE cost =
  `fib_cost(#HIRE orders)` and BUY_LAND tier both assume the engine accepted the order; on a
  cash-crunched day the agent can emit HIRE/BUY_LAND that the engine rejects for insufficient
  funds, so the tool over-counts discretionary spend on exactly the crater days it targets.
  Directional only — doesn't change which days are flagged as the crater.
- **P0.6: `trace_crater.py` drops a day whose step is malformed** (`money()` returns None); the
  crater-onset scan then treats the missing day as `0 < floor` and can false-flag an onset.
  Rare; sanity-check onset day against the raw replay before acting on it.
- **P0.6: `trace_cashflow.py` estimates BUY_LAND at a flat $1000** (self-documented in its
  docstring); actual tier cost varies. Only affects the cash-delta attribution line, not the
  cash trajectory itself.
- **P0.7: `logs_present()` in download_episodes.py still uses bare `.exists()`.** Only the
  replay incremental-skip path is size-gated (`_MIN_REPLAY_BYTES`); a valid log file has no
  reliable minimum size, so a pre-existing truncated *log* stub is not auto-re-pulled (new
  log pulls ARE gated by `_valid_json` at download time). Low stakes — episode judgement keys
  on replays + `ladder_analyze`; `--refresh` forces a clean re-pull if a log looks wrong.
- **P0.7: `_valid_json` size floor is 2 bytes for logs / 100 KB for the replay skip-check.**
  A download truncated at a byte offset that still happens to be valid JSON (`{}`, a complete
  but short object) would pass. Practically impossible for a multi-MB replay cut mid-transfer;
  the parse check catches every realistic truncation.
- **No local opponent reproduces the real-ladder animal_factory mid-game cash crater.** P0.2 smoke: `main.py` beats the purpose-built `bot_factory_v3` (mined from the 12 real animal_factory losses on sub 56029879) **3-0 / +68k avg margin / score 100%**, and beats `bot_top10clone` (2850-3010-rated config) +88k. The bots' own docstrings concede the scripted engine "isn't a real 2850 agent and can't ride the escape spiral". Consequence for the loop: a Class-2 A/B on the diverse pool measures self-play + weak-archetype performance, NOT the loss mechanism the teardowns name. Adding these two bots to the pool (P0.2 fix) closes the *omission*, not the *fidelity* gap. Recorded also in knowledge-base/07.
