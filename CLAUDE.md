# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-agent entry for the **Kaggriculture** Kaggle Simulations competition — a
2-player, 720-turn (30 days × 24 turns) farming/economy game run on
`kaggle-environments`. The whole submission is `main.py`, which must expose
`agent(obs) -> {"farmer": [...], "hands": [[...], ...], "market": [[...], ...]}`.
Goal: end the season with more coins than the opponent. Reward is
`farm["money"]` only; the coin margin never affects rating, just win/loss/tie.

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

Local single game (edit the file to change opponents / config):

```bash
python local.py
```

Paired benchmark — the real regression gate. Alternates seats, reports W/T/L,
mean/median/p10 coins, and error count:

```bash
python test.py --games 20
python test.py --games 40 --candidate main.py --incumbent main_v1.py
python test.py --games 20 --opponents starter random main_v1.py --save-worst 5
```

Built-in opponents available by name: `pass`, `random`, `starter`.

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

## Agent architecture (`main.py`, "v3/v4")

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

Real ladder is **not** self-play. `test.py` vs `starter`/`main_v1`/`main_600`
shows large wins (48–0–0, ~28k+ coins) but the Kaggle score was 600 — local
opponents don't model competitive market contention. Collect real ladder
replays/logs and reason about opponent archetypes before large strategy changes.

## File map

- `main.py` — current agent (v3 core + v4 animal module). The submission.
- `main_v1.py`, `main_600.py` — older versions kept as benchmark opponents
  (`main_600.py` scored 600 on the ladder; both have the shop-name lookup bug).
- `main_600.py` also = the "v2" baseline the improvement plans dissect.
- `local.py` — one-off local game runner. `test.py` — paired benchmark harness.
- `AGENTS.md` — getting-started + full Kaggle CLI workflow.
- `README_2.md` — full game rules, crop/animal/shop tables, price function,
  turn-processing order. `readme.md` — competition blurb. `how to play.md` —
  rules narrative.
- `PLAN_3000.md`, `SCORE_IMPROVEMENT_PLAN.md`, `STRATEGY.md`, `WINNING_PLAN.md` —
  strategy analysis and roadmap (read `PLAN_3000.md` first for current thinking).
- `replays/`, `logs/`, `benchmark_replays/` — downloaded/generated episode data.
