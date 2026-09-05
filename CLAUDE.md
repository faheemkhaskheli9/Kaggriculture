# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-agent entry for the **Kaggriculture** Kaggle Simulations competition — a
2-player, 720-turn (30 days × 24 turns) farming/economy game run on
`kaggle-environments`. The whole submission is `main.py`, which must expose
`agent(obs) -> {"farmer": [...], "hands": [[...], ...], "market": [[...], ...]}`.
Goal: end the season with more coins than the opponent. Reward is
`farm["money"]` only; the coin margin never affects rating, just win/loss/tie.

## Task list — read first, keep updated

`TASKS.md` (repo root) is the canonical, living checklist toward the top of
the leaderboard: current submission-slot state, the ranked submission queue,
the standing one-change-per-slot loop, and what's explicitly shelved. Check
it at the start of every session and **update it in the same sitting** as any
action it lists (submission made, ladder read back, item reprioritized) —
don't let it go stale the way `experiments/LEDGER.md`'s narrative once did.

## Knowledge base — read first

`knowledge-base/` is the consolidated reference for this game: rules, exact
engine math, market economics, the observation/action API, the strategy record
(archetypes + what was tried and reverted), and the codebase/workflow map.
Start at `knowledge-base/INDEX.md` (it has a one-screen cheat sheet), then open
the file that matches the task. `knowledge-base/04-engine-internals.md` is
authoritative for any ambiguous mechanic. Keep it in sync when the env,
`main.py`, or the strategy understanding changes.

## Environment setup

`kaggle-environments` bundles `pygame`, which does not build on Python 3.14, so
install without deps:

```bash
pip install --no-deps kaggle-environments jsonschema kaggle
```

The env source (authoritative for all game math) lives at
`kaggle_environments/envs/kaggriculture/kaggriculture.py` in the installed
package — read it directly when a mechanic is unclear.

## Commands

**`compete.py` — the ladder-like gate (use this by default).** One match =
random opponent from the pool (`bots/` archetypes + `contenders/` + every
`agents/*.py` snapshot + `starter`), random 9-digit seed, random seat, stock
competition config (`startingMoney=3000`, `actTimeout=1`, `debug=False` so a
raised exception silently falls back to all-PASS exactly like Kaggle). Every run
archives `manifest.json` + per-game `*.replay.json.gz` + `*.logs.json` under
`compete_runs/<stamp>/`.

```bash
python compete.py --games 120                       # full pool, fresh opp+seed each
python compete.py --agent main_herdbatch.py --games 120 --pick-seed 4242
python compete.py --opponent bots/bot_animalfactory_v2.py --games 20
python compete.py --pool bots/bot_wheatflood.py starter --games 10
```

**`tools/analyze_runs.py` — the results / replay / log analysis pipeline.**
Reduces a `compete_runs/` archive to overall W/T/L + score-rate, per-opponent
and per-archetype breakdowns, movement / plant / weed / animal / sell
diagnostics, surfaced agent exceptions, and a worst-games loss diagnosis with
the day the coin lead flips. Same archetype buckets as `tools/ladder_analyze.py`.

```bash
python tools/analyze_runs.py                        # newest run
python tools/analyze_runs.py --last 3               # merge 3 newest runs
python tools/analyze_runs.py --compare <stampA> <stampB>
python tools/analyze_runs.py --last 2 --json summary.json --csv games.csv
```

`test.py` — older paired seat-alternating benchmark (fixed opponent list, shared
per-pair seeds). Still useful for a tight A/B on one hypothesis; `compete.py` is
the ladder model. Built-in opponents by name: `pass`, `random`, `starter`.

```bash
python test.py --games 40 --candidate main.py --incumbent agents/main_v10.py
```

Local single game (edit the file to change opponents / config): `python local.py`

Kaggle CLI (full workflow in `AGENTS.md`; `commands.txt` has recent ad-hoc
invocations):

```bash
kaggle competitions submit kaggriculture -f main.py -m "message"
kaggle competitions submissions kaggriculture
kaggle competitions episodes <SUBMISSION_ID> -v
kaggle competitions replay <EPISODE_ID> -p ./replays
kaggle competitions logs <EPISODE_ID> <0|1> -p ./logs
```

Multi-file agents must be bundled as a tar.gz with `main.py` at the root.

## Constraints the agent must respect

- **~1s wall-clock per `agent()` call.** `main.py` runs ~4ms/step; keep it there.
- **Never raise.** `agent()` has a top-level try/except that falls back to all
  `PASS`. A silent exception looks identical to a bad strategy in the replay —
  when debugging a flat/losing episode, first rule out an exception.
- **≤10 market orders/turn** (`maxMarketOrdersPerTurn`); extras are dropped
  silently, so order assembly is priority-sorted.
- Observation has `day`/`hour`, **not** `step`. Shop names in
  `town.unlocked_shops` are `UPPER_SNAKE` (`PIZZA_SHOP`) — the old title-case
  lookup bug in `main_600.py`/`main_v1.py` zeroed every shop-demand signal.

## Agent lineage

`main.py` is the promoted agent. Snapshots live in `agents/main_v*.py` (v1→v11)
plus `agents/main_p2.py` / `main_p3.py` forks; the newest snapshot is the
`test.py` incumbent and every snapshot is a `compete.py` pool opponent. Ladder
history: v1 **333** → v2/main_600 **477** (the ML probe sub 55960518 scored
202.5 and is not an agent). Committed `main.py` @ `45ce7bd` = **v10** (v7 zoned
core + P1 day-scaled reserve + F1 herd-match + P2 fertilizer staple + P4
coverage cap). `agents/main_v11.py` and `main_herdbatch.py` are in-flight
candidates — see `experiments/LEDGER.md` for the per-version record and
`knowledge-base/07-codebase-and-workflow.md` for the authoritative file map and
pipeline walkthrough.

## Agent architecture

Turn-by-turn stateless recompute, but structured so labour isn't wasted on
movement (the failure mode of the 600-score agent, which spent ~76% of
unit-actions moving). Pipeline inside `agent()`:

1. `unlocked_cells` + `make_zones` — split the swept tile list into **persistent
   contiguous per-unit zones**. Units act within their zone; they only leave for
   a survival deadline (task priority ≥ 9000).
2. `animal_targets` / `animal_tiles` / `animal_crew_actions` — a dedicated crew
   (last 1–4 hands) handles what a generic task can't: `FEED` (consumes wheat
   from the acting unit's own inventory), `CARE`, `PLACE`, `BUILD_*`, hauling
   wheat from the shed. Gated by `USE_ANIMALS`.
3. `build_tasks` + `add_plant_tasks` — emit `(priority, (x,y), action)` tuples
   over the whole farm: watering (dying-plant vs bonus-window vs comfort),
   harvest, `COLLECT_FERTILIZER` (priority 2700, any unit), weeds, and
   fill-every-tile planting. `choose_crops` picks the crop mix.
4. `assign` — priority-sorted greedy assignment with an act-on-current-tile
   bias, zone restriction (except survival), critical-work global pass, and idle
   repositioning toward pending work.
5. `market_orders` — `price_at` is a local reimplementation of the env price
   curve; each `SELL` is sized against it rather than a fixed batch. Slots are
   filled by priority: dawn `HIRE` → top-3 `SELL` → land/animal/feed buys →
   seeds → remaining sells.

Crop / market / shop constants (`CROPS`, `BASE`, `MKT`, `SHOPS`, `ANIMALS`) are
tuned to this env's economics — see below before changing them.

## Env economics that drive strategy

Distilled from replay analysis (`PLAN_3000.md`, `SCORE_IMPROVEMENT_PLAN.md`, and
the memory notes):

- **The market barely moves.** Both players combined dent inventory by only
  ~100–450 units/product/season (I0 = 10,000). Town center + shops consume for
  free, faster than typical production, so premium/ongoing prices climb well
  above base (observed end prices: STRAWBERRY ~297, MILK ~328, TOMATO 107–564).
  Produce far more high-value goods than feels safe.
- **CARROT** crashes easily (few consumers); grow little. **MELON** crashes hard
  on glut (sq curve); hard-cap ~5 tiles. TOMATO/STRAWBERRY are ongoing with
  runaway scarcity ceilings — lean the field into them.
- **Don't over-crash MILK/WOOL/FERTILIZER** — when both players dump, WOOL→1,
  MILK→28. Spread sales.
- **End-of-day auto-drops every unit inventory to the shed**, so no `DROP`
  round-trips are needed except final-day liquidation. Anything unsold at
  ~step 718 is worthless.
- Fresh plant starts `consecutive_unwatered=1` → must be watered its planting
  day or it dies that night. Two consecutive missed waters → weed; two missed
  feeds → animal escapes (permanent).
- Animals produce milk/wool/egg indefinitely **without** feeding; feeding only
  unlocks the `CARE` bonus. Every surviving animal drops 1 fertilizer/day free.
- No hard farm-hand cap; ~12 hires/day is just the 10-order/turn limit split
  across two hours. Hiring is cheap (`fib(n)`, resets daily).

## Benchmarking notes

Real ladder is **not** self-play, and **the local harness cannot gate a `main.py`
economy change** — repeatedly confirmed (v6, v8, v8b, PLAN_300K s1–2): a change
can be neutral/positive vs `starter` and every isolated probe yet net-negative
vs the active bots, or vice-versa. What local *can* catch: a large regression vs
a trivial bot (`starter`/`random`) is a real bug signal, not noise
(`docs/PLAN_LADDER_V10.md` §3). Workflow: one attributable change per submission
→ `compete.py --games 120` for a sanity read + `tools/analyze_runs.py` for the
per-archetype diagnosis → submit → after ~15–20 episodes
`download_episodes.py` + `tools/ladder_analyze.py <sub>` → compare the
`vs animal_factory` row to the prior baseline. `animal_factory` is ~56% of
ladder games and the worst matchup (`docs/PLAN_LADDER_ECON.md`), so
`bots/bot_animalfactory_v2.py` carries extra weight in the pool.

**Submission discipline (2026-09-04, see `PLAN_RATING_IMPROVEMENT.md`).** Only
your **latest 2** Kaggle submissions are tracked/active — every submission
either fills an empty tracked slot or evicts one of the current two. Never
submit anything but the promoted `main.py` to the real `kaggriculture` slug
(no `agents/main_v*.py`, no `main_auto.py`, no ML probes) — a broken/abandoned
file submitted "just to check" occupies a live rating slot exactly as long as
a good one would. One attributable change per submission, and submit nothing
else that day so it gets a clean window before being displaced. Judge
promote/revert decisions by **win-rate** (score-rate), not mean/margin —
rating is Bradley-Terry over win/loss/tie only, margin is discarded.

## File map

- `main.py` — the submission (promoted agent). `main_herdbatch.py`, `main_ml.py`,
  `main_ai.py` — candidate forks at repo root.
- `agents/main_v*.py`, `agents/main_p*.py` — the version lineage; `compete.py`
  pool opponents + `test.py` incumbents.
- `bots/` — hand-written opponent archetypes on `bots/_kagri_botlib.py`
  (`bot_animalfactory_v2`, `bot_animalfarm`, `bot_wheatflood`, `bot_premium`,
  `bot_melonmono`). `contenders/` — a second archetype set on `contenders/_engine.py`.
- `compete.py` — ladder-like match harness → `compete_runs/<stamp>/`.
  `tools/analyze_runs.py` — analysis pipeline over those archives.
  `tools/ladder_analyze.py` / `classify_ladder.py` / `probe_game.py` /
  `early_probe.py` — real-ladder replay analysis. `test.py` — paired A/B.
  `local.py` — one-off game.
- `download_episodes.py` — bulk pull of ladder replays+logs → `replays/`,
  `logs/`, `episodes/` (run with Python 3.13). `download_top_replays.py` —
  top-of-leaderboard replays.
- `experiments/LEDGER.md` — one row per agent version (change → local → ladder →
  status). `experiments/TOKENS.md` — per-session token spend.
- `ml/` — Optuna / CMA-ES engine-config search + IL/self-play scaffolding
  (`ml/loop.py` supervisor never submits or overwrites `main.py`).
- `docs/` — strategy plans and roadmaps. Read `docs/PLAN_LADDER_NEXT.md`
  (**current plan** — corrected ladder facts + routing/top-10-teardown
  sequence) first, then `docs/PLAN_LADDER_ECON.md` (the 75-replay archetype
  sweep). `docs/PLAN_LADDER_V10.md` is the prior plan, kept as history/
  rollback reference. `docs/PLAN_3000.md` / `PLAN_300K.md` = coin-ceiling
  analysis.
- `knowledge-base/` — the consolidated game/strategy/workflow reference (start at
  `INDEX.md`). `AGENTS.md` — Kaggle CLI workflow. `README_2.md` / `how to play.md`
  — full rules.
- `replays/`, `logs/`, `episodes/`, `compete_runs/`, `benchmark_replays/` —
  episode data (downloaded + generated).
