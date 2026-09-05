# `challenger/` — replacement-policy program (IMPACT plan §8, Workstream B)

A **new** agent built around observed top-10 ladder behaviour, kept
independently runnable alongside the promoted incumbent `main.py`. Not a
`main.py` edit; not in the `agents/main_v*.py` lineage; never submitted until it
clears the §8 adversarial-league bar.

## Architecture (three layers)

| Layer | Source | Role |
|---|---|---|
| 1. Strategic controller | `challenger/strategy.py` (**new**) | Sets herd size + species split, quadrant allowance, hand ceiling from a replay-derived day/quadrant schedule. |
| 2. Safety controller | `main.build_tasks`, `main.animal_crew_actions`, endgame overrides in `main.assign` (**verbatim**) | Prevents crop death, animal escape, feed shortage, invalid orders, terminal unsold value. |
| 3. Execution controller | `main.assign` Hungarian routing (**verbatim**) | Minimises travel while meeting layer-1/2 targets. |

`challenger/agent.py` is a fork of `main.agent()`'s ~40-line body: same helper
calls, but (a) herd target comes from `strategy.herd_target()` instead of
`main.animal_targets()`, and (b) a replay-derived `intent` (day-gated
`max_quadrants`, `max_hands=12`) is threaded into `add_plant_tasks` /
`market_orders`. Everything else is the incumbent.

## Provenance of every constant in `strategy.py`

All from `ml/artifacts/top_policy_rules.json` (`tools/mine_top_policy_rules.py`
over 18 verified top-10 farms / 12,960 turns):

- **Herd by day** — `day_trajectory` herd_median: 0,4,4,5,6,6,6,8,10,12,13,13,14,15 then hold 15.
- **Herd cap by open quadrants** `{1:6, 2:13, 3:15}` — so the reservation can't
  deadlock planting while only the opening 5×5 is usable (the old
  `LIVESTOCK_ENGINE` bug), while still allowing the mined herd-of-6 at nq==1.
- **Species split COW6 / SHEEP6 / GOOSE3** — mined BUY_ANIMAL unit totals
  (COW 80 : SHEEP 101 : GOOSE 29). GOOSE not before day 6 (never seen day 0).
- **Quadrants by day** `{≥12:3, ≥5:2, else:1}` — `quadrants_median` + `buy_land`
  transitions (1→2 day 5-6, 2→3 day 8-11, 4th never bought: 0/17).
- **`max_hands=12`** — mined `hands_at_buy` max across the whole sample.
- Herd frozen after day 17 — same as the incumbent (cow break-even ~10 days).

**Not overridden in v0:** crop mix. Held-out imitation benchmark
(`ml/artifacts/top_policy_benchmark.json`) puts BUY_SEED family F1 at ~0.50 and
per-crop far lower, so seed choice stays with the incumbent's tuned
`choose_crops` until a value-based crop rule replaces it.

## Status

- **v0 (2026-09-06) — Gate-B FAILED.** Scaffolded, full 720-step season with
  **0 agent errors**. Paired vs `main.py` baseline (96 pairs, pool =
  animalfactory_v2 / top10clone / wheatflood / full lineage): **paired score
  delta −10.4%, 90% CI [−17.2%, −3.6%]**; improved/same/regressed 4/76/16;
  productive actions **−385**, day10 cash **−356**, movement **+1.8%**. Against
  the actual incumbent `main`: **0/0/4, −75%**. Against the target
  `bot_animalfactory_v2`: score flat (both win all 3) but margin **−24.9k**
  (wins by less). `bot_top10clone` margin +17.2k was the only positive.
  Run: `compete_runs/20260906-002448-419010/`.
  → Conclusion: imposing the mined day/quadrant/herd *shape* on top of the
  incumbent's tuned economy loses productive actions and early cash and does
  not convert to wins. IMPACT plan §8 kill-rule triggered ("imitation improves
  shape but win-rate does not").

- **v0 bisection (2026-09-06)** — each knob isolated, 64 paired vs `main.py`
  (`compete_runs/20260906-01*`; variant A all-off = verified exact no-op,
  +0.0% in all 64 pairs):

  | Knob | Paired score Δ | 90% CI | vs incumbent h2h | Note |
  |---|---|---|---|---|
  | **HERD schedule** | **−10.2%** | [−16.4, −3.9] | 2/0/16 | **the entire v0 regression** — −413 productive actions, −361 day10 cash |
  | QUAD day-gate | +5.5% | [−3.1, +13.3] | 12/0/6 | neutral, CI crosses 0 |
  | HAND cap (12 vs 13) | +13.3% | [+6.2, +20.3] | 10/7/1 | clean +, but 100% of the signal is `main` self-play — core bots all flat — the pattern the repo says doesn't convert on ladder |

  Root cause of HERD: the mined "herd 15 by day 12" shape was achieved by
  top-10 farms at ~47% movement with better feed logistics; main's executor
  can't sustain herd-15 without pulling crew off crops. Confirms the repo's
  standing finding that herd/economy *shape* changes lose head-to-head.

  **Decision:** mined-schedule strategic controller **rejected**. All three
  toggles default OFF (package == incumbent, exact no-op). `max_hands=12` noted
  as a possible standalone `main.py` §1 candidate, not a challenger result.
  Next: pivot to a behavior-cloning cadence controller (Workstream A) — the
  hand-coded schedule route is a dead end for the strategic layer.

## Run it

```bash
python compete.py --agent challenger/agent.py --opponent bots/bot_animalfactory_v2.py --games 20
python compete.py --agent challenger/agent.py --baseline main.py \
    --pool bots/bot_animalfactory_v2.py bots/bot_top10clone.py bots/bot_wheatflood.py main.py \
    --games 96 --pick-seed 260906
python test.py --games 40 --candidate challenger/agent.py --incumbent main.py
```

## Promotion bar (from `docs/IMPACT_RANKED_LEADERBOARD_PLAN.md` §8)

≥65% overall validation score-rate in the adversarial league; ≥55% vs every
major archetype; ≥60% vs animal factories; positive head-to-head vs the
incumbent on held-out seeds; zero runtime failures / policy-caused escapes /
packaging mismatches; same direction in two independent seed blocks. Only then
does it get a real submission slot.
