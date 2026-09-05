"""Top-10-caliber opponent, config mined directly from real 2850-3010-rated
play (``top10_ladder/replays/*.json``, 22 games / 44 farm-samples), not a
guess. This is Lever 1 of ``docs/PLAN_TOP10.md``: local testing has
repeatedly diverged from ladder reads (see ``CLAUDE.md`` Benchmarking notes)
because nothing in the local pool actually plays like a top-tier agent --
`bot_animalfactory_v2` etc. are strong *ladder* archetypes but nowhere near
2850-rated. This bot is meant to close that gap so a change that beats it
locally has real odds of moving the real ladder, without spending a
submission slot to find out.

Numbers below are straight from ``python tools/analyze_top.py`` (rerun it if
``top10_ladder/`` gets refreshed -- the config here should be re-derived,
not hand-adjusted):

* land: 2nd quadrant by day 7 (median), 3rd by day 12, **4th quadrant: 0/44
  farms ever buy it** -- field plateaus at 75 tiles. This directly encodes
  `TOP10_TEARDOWN.md` Finding 1 (`quadrant_target` hard-caps at 3, forever).
* hands: median 5 @day5, 11 @day10-15, 12 @day20, easing to 11 @day29.
* crops @day20 tile-share: STRAWBERRY 58.0%, WHEAT 39.8%, TOMATO 1.3%,
  MELON 0.7%, CARROT 0.1% -- Finding 3, inverted from `main.py`'s own
  (pre-fix) target shares.
* animals @day20: COW 50.2% / SHEEP 45.9% / GOOSE 3.9% of an observed
  ~15-head average herd (667 animals / 44 farm-samples).
* money: brutal early squeeze (day2 median $85 -- nearly the whole $3000
  start spent turn 1 on land+seeds+animals) that recovers hard once the
  field and herd are both running (day10 median $2.2k, day15 $20.7k, day20
  $43.8k, final median $86.3k, max $175.4k seen). Confirms
  `TOP10_TEARDOWN.md`'s note that even top players crater mid-game --
  recovering fast matters more than avoiding the dip.
* movement share 47-48% of hand-actions (Finding 2) -- not reproducible via
  this config DSL (that's an execution/routing property, not a decision
  knob); this bot will still walk however `_kagri_botlib`'s engine walks.
  It's here to be hard on land/crop/animal/cash-timing decisions, not to
  benchmark routing.

    python compete.py --opponent bots/bot_top10clone.py --games 20
    python compete.py --agent main.py --opponent bots/bot_top10clone.py --games 40
"""
from _kagri_botlib import make_agent


def _crop_mix(day):
    # The 58/40 STRAWBERRY/WHEAT split is the observed day-20 *steady
    # state*, not what a real player plants on day 0 -- strawberry takes
    # 10 days to first yield and costs 10x a wheat seed, so front-loading it
    # from turn one just starves early cash (this was bot_top10clone's v1
    # bug: 20-0-0 *loss* to main.py, opponent final money in the hundreds
    # vs the real top10 curve's $86k median). v2 ramped toward the literal
    # 39.8% wheat floor and starved the herd's feed supply instead (animals
    # cycling escape->rebuy every few days -- 2 consecutive missed FEEDs is
    # a permanent escape, `kaggriculture.py:_daily_refresh_animals`). This
    # config keeps wheat >=50% for the whole game as a feed-security floor;
    # it undershoots the literal day-20 tile-share finding but stays a
    # stable, hard-to-beat opponent, which is the actual point of this bot
    # (see docs/PLAN_TOP10.md Lever 1) -- exact tile-mix fidelity is
    # secondary to "does it actually play like a strong economy."
    # Tried dropping the real mix's TOMATO/MELON/CARROT slivers (1.3/0.7/
    # 0.1% of tiles) and tightening the land gate to animalfactory_v2's pace
    # (day5/fill0.40) in the same pass -- both regressed the read against
    # main.py specifically (opp final money ~6.7k vs this config's ~9.9k
    # over 15 games each), so reverted both. Keep the slivers; they're
    # cheap and match the real mix, whatever inefficiency they cost isn't
    # what's limiting this bot against main.py.
    if day < 8:
        return {"WHEAT": 0.85, "STRAWBERRY": 0.15}
    if day < 16:
        return {"WHEAT": 0.65, "STRAWBERRY": 0.32, "TOMATO": 0.02, "MELON": 0.01}
    return {
        "WHEAT": 0.52,
        "STRAWBERRY": 0.44,
        "TOMATO": 0.02,
        "MELON": 0.015,
        "CARROT": 0.005,
    }


agent = make_agent({
    "name": "top10clone",
    # --- land: 2nd by ~day7, 3rd by ~day12, NEVER a 4th quadrant ---
    "quadrant_target": lambda day: 3,
    "land_fill_gate": 0.45,
    "land_day_gate": 7,
    # --- labour: ramp to ~11-12 by day10, hold through the season ---
    "hire_target": lambda day, nq, n: (
        5 if day < 3 else (11 if day < 27 else (9 if day < 29 else 0))),
    # --- crops: wheat-first for cash flow, converging to the real day-20 mix ---
    "crops": _crop_mix,
    # --- herd: 10 head, COW/SHEEP-roughly-even, GOOSE a sliver. Tried both
    # smaller (this) and the real ~15-head scale head-to-head against
    # main.py specifically (not just a soft/neutral opponent): the 15-head
    # config actually did *worse* here (opp final money ~4.1k vs this
    # config's ~9.9k over 15 games) even though it wins more often in a
    # neutral top10clone-vs-animalfactory_v2 match -- against a crew this
    # size (~11 hands) contesting a strong opponent for the same board, a
    # bigger herd is more feed-logistics load than it's worth. Keep it
    # smaller here; revisit once Lever 2's crew is actually big/efficient
    # enough to carry more animals. One buy/turn avoids an overshoot spike.
    "animals": {"COW": 5, "SHEEP": 4, "GOOSE": 1},
    "animals_per_turn": 1,
    "animal_buffer_base": 250,
    "animal_buffer_per_head": 60,
    "animal_min_quadrants": 1,
    # --- selling: steady volume, sized for a much bigger field than the other bots ---
    "sell_cap": 20,
    "premium_sell_cap": 12,
    "sell_floor_frac": 0.0,
    "plant_fill": True,
    "reserve": 150,
})
