---
description: Autonomous Kaggriculture climb loop — mine the top of the leaderboard, batch-build agent improvements, gate them locally, submit the best each slot, and keep going until the promoted agent is near the top
---

Run the **fully autonomous** ladder loop with **one job: move the promoted
agent up the `kaggriculture` leaderboard.** Every iteration should end with the
agent measurably better or a submission in flight — not "held both slots, vein
is dry". The mechanical micro-tweak era is over; this loop is allowed to make
**real strategy changes** and to **build and test several at once**.

Intended usage: `/loop /ladder-auto` (no interval — self-paced). One iteration
per firing, then `ScheduleWakeup` the next. All loop state lives in the shared
files below; after an auto-summary / `--resume` / `/compact` the next iteration
rebuilds by re-reading them.

Optional focus / target override for this run: $ARGUMENTS
(default target: promoted-agent rank ≤ 3000 on `kaggriculture`, then keep
climbing toward the top.)

## What changed and why (read once)

The previous version of this loop was heavily self-throttled: mechanical-only
changes, one atomic flag per submission, an 8-section pipeline audit that
blocked all agent work, a `STALL COUNT` circuit-breaker that *stopped the loop*
after 3 flat reads, and an explicit list of reject reasons that made "ship
nothing" the default. It ran 9+ iterations and the score did not move.

User order (2026-09-09): **rewrite as a pure climb loop.**
- **No mechanical-only rule.** Economy, crop mix, field allocation, herd sizing,
  hire cadence, market timing, endgame — all in scope.
- **Bundled changes allowed.** A candidate may combine several related hunks if
  they form one coherent strategy idea. Still put each behind its own
  `ENABLE_*` flag so a partial revert is possible, but you do **not** have to
  ship them one-at-a-time.
- **Batch-build.** Each iteration builds the top **2–3** ideas as separate
  `agents/main_v<NN>_<name>.py` files and gates them in parallel, then submits
  the best one. The rest stay queued as ready-to-submit.
- **No STALL-COUNT stop.** A run of flat reads means *change strategy family*,
  not halt. See "Rotate the strategy family" below.
- **Pipeline audit is advisory, not a gate.** Do it once, opportunistically,
  when a read looks impossible to explain; never block agent work on it.

### Hard limits that remain (these are not loop discipline — they protect the
### thing you are trying to climb)

1. **Never raise.** `agent()` has a top-level try/except → all-PASS fallback; a
   silent raise looks exactly like a bad strategy. Every candidate must survive
   `compete.py` with `debug=False` with **0 `agent()` errors** before it can be
   submitted, and the **first** thing to check on any flat/losing ladder read
   is a silent raise (grep the logs).
2. **≤ 5 Kaggle submissions per calendar day** across all slugs/models, **≤ 2 of
   which may be experiment agents** (anything that is not the promoted `main.py`
   on the real `kaggriculture` slug). Only the promoted `main.py` is ever
   submitted to the real `kaggriculture` slug.
3. **Every Kaggle submission needs explicit user approval.** This loop builds,
   gates, queues, and *proposes* autonomously, but it **pauses at the submit
   step** and asks. Prepare the submission fully (flag ON, message written,
   file staged) so approval is one word.
4. **Rating-floor guard.** Kaggle tracks only your latest 2 submissions. Do not
   submit a candidate if it would leave *both* tracked slots holding a sub known
   to score below your current live-best — you would drop rank for a guess. If
   both slots have already drifted below the peak and no candidate has proven
   better, the recommended submission is a bytes-identical resubmit of the peak.
5. **New file per change** (`agents/main_v<NN>_<name>.py`); never edit a prior
   snapshot in place. Commit messages end
   `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` with **no** "Claude"
   author attribution.
6. `ml/` stays frozen until after 2026-09-30. No new bots. New *analysis*
   scripts are fine if they earn their place.

## The gate metric

**Win-rate (score-rate) vs `animal_factory`.** It is ~56% of ladder games and
the worst matchup, and rating is Bradley-Terry over win/loss/tie so margin is
discarded. Local proxy: `bot_animalfactory_v2` weighted heavily in the
`compete.py` diverse pool. A candidate is *submittable* when its paired local
A/B vs the current `main.py` shows the score-rate delta trending positive
(ideally CI above 0, but a strong point estimate + a clear behavioural
improvement is enough now — we are trying to climb, not to prove theorems) and
it does not tank vs `starter`/`random`.

## State files this loop owns

- `docs/LADDER_RUNBOOK.md` **State table** — keep current: `PEAK_SUB`,
  `PEAK_SCORE`, tracked pair, pending sub(s), board-best, last judged. Drop the
  `STALL COUNT` / `PIPELINE AUDIT` rows or leave them as historical notes; they
  no longer gate anything.
- `experiments/LEDGER.md` — one row per candidate version
  (change → local A/B → ladder read → status). Authoritative history.
- `experiments/AUTO_IDEAS.md` — the ranked forward queue. Format:
  `| id | idea | family | evidence it moves win-rate vs animal_factory |
  local A/B (delta + CI) | status | flag(s) |`.
  Status vocab: `queued` / `built` / `submitted` / `promoted` / `gated-flat` /
  `reverted` / `parked`. Keep 6–12 live rows; re-rank every iteration.

Re-read every shared file immediately before writing to it (Codex may share the
tree).

## Idea sources — where climb comes from

Every iteration refreshes `AUTO_IDEAS.md` from **all** of these, not just loss
buckets:

1. **Top-of-board structural teardown.** `download_top_replays.py --top 10` then
   `tools/analyze_top.py --detail`. Go past stat gaps: reconstruct *what the top
   3 agents actually do* — field tiles planted per day and crop mix, herd size
   curve, hire cadence, cash trajectory day-by-day, when they start selling and
   into which products, endgame liquidation. Diff our `main.py` behaviour
   against that. The biggest unexplained divergence is the #1 idea candidate.
   Re-derive each mechanism from engine rules + our own replay data — never
   copy competitor source (`PUBLIC_AGENT_STRATEGY_CATALOG.md` is ideas-only).
2. **Our loss teardown.** `tools/ladder_analyze.py <BOARD_BEST>` for loss
   buckets + lead-flip day; `tools/trace_crater.py` and
   `tools/trace_cashflow.py --arch animal_factory` for the mid-game cash crater
   (the long-standing loss mechanism: our cash sits flat ~$900 through d10–15
   while the top-10 climb from ~$2100; the close losses trace to that window).
3. **Engine economics.** `knowledge-base/` + the engine source
   (`kaggle_environments/envs/kaggriculture/kaggriculture.py`). Under-exploited
   scarcity ceilings (TOMATO / STRAWBERRY / MILK runaway prices), free town/shop
   consumption, animals producing without feed, free daily fertilizer.
4. **Class-1 bugs** — always top priority when found: dropped/overflowed market
   orders on lumpy turns, wrong reserve/feed/hire accounting, a mechanic modeled
   differently than the engine computes it, a dead code path. A bug fix ships on
   correctness grounds regardless of EV estimate.

## Rotate the strategy family when reads go flat

Track a `FAMILY` label on each idea: `crater-timing`, `field-allocation`,
`herd-economy`, `market-timing`, `movement-routing`, `endgame`, `bug`. If the
**last 2 judged submissions from the same family** did not beat the live-best,
**stop drawing from that family** for the next 3 iterations and build from a
different one. This replaces the old circuit-breaker: the loop keeps going, it
just changes where it digs. Only genuinely stop (`ScheduleWakeup({stop:true})` +
LEDGER handback) when the promoted agent hits the target rank, or the user says
stop, or **every** family has had 2 flat judged reads with nothing new to try.

## One iteration

### 0. Orient (always)

- Read the State table, `experiments/LEDGER.md`, `experiments/AUTO_IDEAS.md`,
  `CLAUDE.md` § "Workflow rules" (for the hard caps only — the loop-discipline
  parts are superseded here).
- `kaggle competitions submissions kaggriculture | head -15` — record the
  tracked-2 pair, each sub's score + episode count, the last 2 submit
  timestamps. Cross-check `experiments/LEDGER.md` + `commands.txt` for same-day
  subs on other slugs.
- Compute the **submission budget**: subs today (of 5), experiment-agent subs
  today (of 2), next slot availability. Compute the **rating-floor check**: does
  the tracked pair include a peak-or-better sub?

### 1. Stop check

```bash
python download_top_replays.py --top 10
kaggle competitions leaderboard kaggriculture --show | head -5
```
- Promoted-agent rank ≤ target → **STOP** (final LEDGER note; under `/loop` call
  `ScheduleWakeup({stop:true})`).
- Every strategy family exhausted (see "Rotate the strategy family") → STOP with
  a handback note.
- Otherwise continue.

### 2. Judge the pending sub(s)

For each pending sub, follow `docs/LADDER_RUNBOOK.md` Phase A → B:
```bash
python download_episodes.py --submissions <PENDING> --refresh
python tools/ladder_analyze.py <PENDING>
grep -rlE "Traceback|\"PASS\"[^,]*fallback|agent\(\) raised" logs/ | head
```
- **Silent raise** → RETIRE-RAISING: flag OFF, LEDGER note "silent raise, not a
  strategy read", go build. (Not a strategy signal — do not count it against
  the family.)
- **< 15 eps** → HOLD, note direction only, never revert.
- **≥ 15 eps** → judge on **win-rate vs `animal_factory`** vs the current
  live-best baseline:
  - Beats the live-best on overall ladder score **and** af win-rate ≥ baseline →
    **PROMOTE**: mirror the candidate into `main.py` verbatim (keep its flag
    ON), commit, State: Pending → Board-best, update `PEAK_SUB`/`PEAK_SCORE` if
    it is a new all-time high. `AUTO_IDEAS.md` → `promoted`.
  - af win-rate ≥ baseline **+10pp** at ≥ 20 eps (above the ±15pp identical-code
    noise band) but ladder score not yet a new peak → **PROMOTE as board-best**,
    do not move `PEAK_SUB` yet.
  - Flat / within noise / regression → **RETIRE** (flag OFF, candidate stays in
    `agents/`), record the family read as flat.
- Update the idea's `AUTO_IDEAS.md` row.

### 3. Learn — refresh the idea queue

Route the replay mining and `compete.py` runs through **one** `Explore` /
`general-purpose` subagent to keep the main thread lean. It returns only:
- the **top-of-board structural diff** (source 1 above): our per-day behaviour
  vs the top 3, biggest divergences ranked;
- the **cash-crater turn-by-turn** vs `animal_factory` (source 2);
- any **Class-1 bug** it can substantiate in real data (source 4);
- for step 2's judged sub: the W/T/L line, `agent()` error count, OFF-path
  zero-diff result, paired-A/B score-rate delta with CI.

No raw per-game dumps in the main thread. Fold everything into `AUTO_IDEAS.md`
and re-rank by attributable EV against the af win-rate. Assign each idea a
`FAMILY` label. Respect the family-rotation rule from above.

### 4. Batch-build the top candidates (Phase C)

Take the top **2–3** `queued` ideas that (a) are not on the LEDGER reverted list
with the same mechanism, and (b) are not in a currently-benched family. For
each:

- Implement behind `ENABLE_<NAME>` (default OFF) + a named config block, in a
  **new** `agents/main_v<NN>_<name>.py`. A bundled idea gets one flag per
  independent hunk but lives in one file.
- Gate via the subagent:
  ```bash
  python compete.py --agent agents/main_v<NN>_<name>.py --games 120
  python tools/analyze_runs.py
  # paired A/B vs current main.py, ≥120 games, report delta + CI
  ```
  Submittable requires: OFF-path zero-diff vs current `main.py`; **0 `agent()`
  errors**; no tank vs `starter`/`random`; and the paired A/B score-rate delta
  positive (CI above 0 preferred; strong point estimate + a clear intended
  behavioural move — move% down, d10 cash up, planted-tile count up, first
  market slot a premium SELL — acceptable). Guard economy changes against the
  field-starve failure mode (P2k: planted-tile count and productive actions
  must **not** drop vs baseline).
- Commit each (`v<NN> <name> — <one-line mechanism>`, co-author trailer, no
  Claude attribution). `AUTO_IDEAS.md` → `built` (submittable) or `gated-flat`.
- Rank the built candidates by A/B delta. The best becomes the submit proposal;
  the rest stay `built` and ready for the next slot.

### 5. Propose the submission (Phase D — user approves)

If a slot is open (budget in step 0) and at least one `built` submittable
candidate exists, and submitting it keeps a peak-or-better sub in the tracked
pair (rating-floor guard):

- Flip that candidate's `ENABLE_*` ON, mirror the hunk(s) into `main.py`
  (multi-file → note the tar.gz bundling), write the submit message
  (`<flag(s)> — <mechanism / expected win-rate move>`).
- **Present to the user for approval**, one line: the candidate, its local A/B
  delta, which tracked slot it evicts, and the exact command:
  ```bash
  kaggle competitions submit kaggriculture -f main.py -m "<message>"
  ```
- On approval: run it, State → "Pending sub", revert the flag OFF on `main.py`
  (keep the dormant hunk committed), log sub id + timestamp in
  `experiments/LEDGER.md` + `commands.txt`, `AUTO_IDEAS.md` → `submitted`.
- On no reply / decline: leave everything staged, note it, continue the loop —
  next iteration re-proposes or supersedes.

If no submittable candidate exists this iteration, that is fine — you built and
gated some; say which are `built` and ready, and continue. Do **not** treat an
idle slot as a goal, but also do not manufacture a weak submission to fill it.

### 6. Update shared state & schedule next wake

- Apply State-table + `LEDGER.md` + `AUTO_IDEAS.md` edits (re-read first).
- Under `/loop`, `ScheduleWakeup`, passing the same `/loop /ladder-auto` prompt
  back:
  - Submission proposed, awaiting user → `1800` s, `noop:false`, reason
    "submission proposed, awaiting approval".
  - Just submitted, or a sub mid-accumulation (< 15 eps) → `3600` s,
    `noop:true` unless something changed, reason "sub <id> at K/15 eps".
  - Building / gating candidates → `1800` s, `noop:false`.
  - Queue dry, mining a new family → `1800` s, `noop:false`.
  - Stop condition → `ScheduleWakeup({stop:true})`.

## Output (end every iteration with)

1. **Score line** — `PEAK_SCORE` (peak sub) vs current live-best tracked score
   vs target rank. Lead with this. If it is not moving, say so and name the
   strategy family being rotated to next.
2. **Iteration verdict** — `PROMOTED (peak updated)` / `PROMOTED (board-best)` /
   `RETIRED <id>` / `HOLD <id> (K eps)` / `BUILT <files> (N submittable)` /
   `PROPOSED <file> for submit` / `SUBMITTED <id>` / `STOP <why>`.
3. **Submission budget** — subs today (of 5), experiment subs today (of 2), next
   slot, tracked-2 pair + which slot the proposed sub evicts.
4. **Idea queue** — top 3–5 `AUTO_IDEAS.md` rows: idea, family, status, the
   win-rate mechanism each targets. Note any benched family.
5. **Shared-file edits applied.**
6. **Next wake** — delay + concrete reason (or `STOP`).
