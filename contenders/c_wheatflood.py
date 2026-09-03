"""C1 -- wheat-flood contender (PLAN_CONTENDERS.md section 4).

Mirrors the ladder archetype that scored 35k-111k coins: grab all four
quadrants fast, plant ~85-90% WHEAT (with a little CARROT for week-1 liquidity),
run a full ~12-hand crew, and SELL WHEAT to the 10-order cap on every single
turn, with a terminal spike on days 28-29. No animals -- pure throughput.

Wheat's glut side of the price curve is a `log` shape with a low amplitude
(`06 section 5`: end-price 33-56 across 30 games, never crashes), so dumping
large batches barely moves the price. The whole bet is production + sell
throughput, not price.

Known risk (`06 section 2`): a monoculture collapses against a diversified
animal+premium agent. C1 is a *better-built* wheat-flood than the throwaway probe
that lost 12k vs 63k (real 4-quadrant scale, full hand count, aggressive land
gate) -- the round-robin tells us whether scale alone closes that gap.

    python test.py --games 30 --candidate contenders/c_wheatflood.py \
        --incumbent main.py --opponents starter main_v5.py bots/bot_animalfarm.py
"""
from _engine import make_agent


def _hire_fn(day, nq):
    # $3000 start cannot carry a big crew on day 2 (fib HIRE cost + no income
    # until the first wheat matures ~day 4). Ramp 6 -> 9 -> 12 over week 1, then
    # hold a full crew, then taper.
    if day < 3:
        return 6
    if day < 6:
        return 9
    if day < 27:
        return 12                    # 13 units for the back-half wheat rotation
    if day < 29:
        return 7
    return 0


def _land_ok_fn(nth, day, fill, money, cost):
    # more aggressive than v5's default (fill .55/.62, day gates) but with a real
    # cash cushion so the buy does not bankrupt the hire budget.
    if nth < 2:                       # quadrants 2 & 3
        return day <= 20 and fill >= 0.48 and money >= cost + 800 + 300 * nth
    return 6 <= day <= 20 and fill >= 0.55 and money >= cost + 2000   # the $4k one


agent = make_agent({
    "name": "wheatflood",
    "use_animals": False,
    "hire_fn": _hire_fn,
    "land_ok_fn": _land_ok_fn,
    "crop_cfg": {
        # only these two crops are ever planted
        "WHEAT":  {"early": 0.90, "main": 0.88},
        "CARROT": {"early": 0.10, "main_demand": 0.05, "late": (22, 0.20)},
    },
    "crop_caps_fn": lambda day, early: {},          # no per-crop caps
    "plant_water_slack": 24,                        # keep the field a bit fuller
    # one-time crops need a fresh seed per harvested tile; a ~70-tile wheat field
    # on a 3-day cycle burns ~25 seeds/day, so the default seed_cap=12 starves it.
    "seed_cap": 110,
    "seed_lookahead": 8,
    "sell_cap_override": {"WHEAT": 45, "CARROT": 30},
    # sell wheat hard but stop feeding the order once its own dumping has walked
    # the marginal price below ~0.6x base -- keep=0.0 just crashes our own line.
    "sell_keep_override": {"WHEAT": 0.60, "CARROT": 0.30},
})
