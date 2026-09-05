"""Workstream B candidate (docs/IMPACT_RANKED_LEADERBOARD_PLAN.md): top-10
replay-derived land/animal thresholds, replacing two hand-tuned constants in
the Lever 2 `main.py` this forks from. NOT a rewrite of the strategic
controller -- the existing engine (routing/safety/crop-value logic) is kept
as-is per the plan's "do not rewrite main.py in place" guidance; only the two
constants below are evidence-backed replacements. Built from
`tools/mine_top_policy_rules.py` (`experiments/LEDGER.md`'s "Top-policy
land/animal mining" row) over 18 top-farm-episodes / 10 real players.

  R1 (land)   Raised the quad-2/3 fill-ratio gate 0.55 -> 0.75. Mined evidence:
              top players buy NE only once the NW field is at 18-20/25 plants
              (fill ~0.72-0.80) and SW only once 2-quadrant plants hit 30-41/50
              (fill ~0.60-0.82) -- a field-saturation gate stricter than 0.55,
              which lets `main.py` split its crew across quadrants too early.
  R2 (land)   Hard-disabled the quadrant-4 (SE, $4000) buy outright (nth==2
              branch now always `ok=False`) instead of relying on the computed
              ROI check to keep returning false. Mined evidence: 0/17 farm-
              episodes that reach 3 quadrants ever buy the 4th, including ones
              sitting on $15k-$17k cash -- this is a real behavioral cap in
              top play, not merely a capacity-math coincidence, so encode it
              directly rather than trust an ROI formula to keep failing.
  R3 (animal) Raised the nq==3 herd cap 13 -> 15 in `animal_targets`. Mined
              evidence: herd size plateaus at 14-15 by day ~12 across the
              sample (day trajectory: 8/10/12/13/14-15 on days 7/8/9/10/12)
              and holds flat afterward -- `main.py`'s existing "buy one per
              turn" pacing already matches the mined qty-1, day-0-to-15
              trickle shape, so only the ceiling needed correcting.

Status: screened once with all three bundled (100-pair Gate B vs `main.py` on
`experiments/adversarial_league_v1.json`) -- INCONCLUSIVE (headline +3.5% but
90% CI [-0.5%, +8.0%] crosses zero; the two target archetypes,
`bot_animalfactory_v2` and `bot_top10clone`, read flat-to-negative on their
own). Full numbers: `experiments/LEDGER.md`'s "Workstream B candidate" row.
NOT promoted to `main.py`.

Each rule is now an independent toggle (config block just above `USE_ANIMALS`
below) so the bundle can be bisected without maintaining three separate
files: `ENABLE_R1_LAND_FILL_GATE`, `ENABLE_R2_DISABLE_Q4`,
`ENABLE_R3_HERD_CAP`. Every flag set to False reproduces `main.py`'s exact
original numbers (byte-behavior-equivalent, verified via a zero-delta paired
self-test against `main.py`) -- flip exactly one flag on at a time to isolate
which rule, if any, is carrying or hurting the bundled result.

--- Forked from v14 (main.py @ commit at fork time): v11 + P4b/cropflip +
Lever 2 (a146a5e/c9ab4ff). Full version history/rationale: agents/main_v14.py
(this file's frozen snapshot) and experiments/LEDGER.md's "Lever 2" row.
Lever 2 summary: docs/PLAN_TOP10.md's computed marginal-value estimator --
`_crop_tile_value()` (real engine growth constants + price_at) drives
choose_crops' day>=7 crop picks and the quadrant-4 land-buy ROI gate,
replacing hand-tuned shares/thresholds. Bug-check clean (95.0%/0 err, ~230
games) but targeted hard-bot reads (bot_top10clone, bot_animalfactory_v2)
show no measurable local gain over baseline -- verdict needs a real ladder
read. Not submitted as of 2026-09-05 (see TASKS.md).

--- v11 (parent): agents/main_v10.py + 3 stacked, independently-revertible hunks.

Built off the committed v10 snapshot (NOT the live main.py, which had unproven
WIP + a concurrent edit at authoring time). A/B target: agents/main_v10.py.

  P2k  REVERTED. A marginal-value crop prune (drop a crop whose glut-discounted
       price no longer clears seed break-even) was tried and pulled -- 40-game
       pinned ablation on the diverse pool: with the prune 42.5% win / -$3.5k
       margin, without it 57.5% / +$10k. The prune starved the field. Kept out.
  P3f  market_orders -- cash-flow-aware reserve: the P1 day-scaled ramp becomes
       an upper bound; relax it toward HARD_FLOOR (120) once unsold shed value +
       ~2 days of herd produce already cover the cushion, so land/animal/seed
       buys fire sooner when the money is visibly in the pipe. Never below
       HARD_FLOOR, never above the ramp -- the poverty trap was a blindly-LOW
       reserve; this only frees value already landing.
  P1w  build_tasks -- evening water top-off: in the last few turns of the day an
       unwatered live plant at consecutive_unwatered == 0 gets priority 3000
       (> plant 2400, weed 2500, comfort-water 2600) so it does not enter the
       night dry and become tomorrow's 10000 survival water + 2-miss weed risk.
  P4r  assign -- walk-aware: out-of-zone tasks in the global pass cost 40/step
       (was 25) so cross-farm pickups need a real priority gap, and idle units
       drift toward their own zone instead of the globally-nearest transient tile.

Ablation (40 games, --pick-seed 7, diverse pool): v10 base 45.0% / +$2.9k margin;
this build (P3f+P1w+P4r) 57.5% / +$10.0k; -P3f 30.0% (P3f carries it); P1w/P4r
individually inert on this pool but harmless and plausibly help under lineage
mirror-matches. Rollback: drop any hunk independently; full = agents/main_v10.py.

--- v10: v7 + P1 (branch ladder-v9-p1-cashfloor) + PLAN_LADDER_V10
F1/P2/P4. See docs/PLAN_LADDER_V10.md.

Bundle on top of P1 (day-scaled working-capital `reserve` + per-turn seed-spend
cap, already committed):
  F1 -- vs an animal-heavy opponent, MATCH the herd (COW5/GOOSE5/SHEEP1) instead
        of crouching to 6 -- the FREE fertilizer line (1/animal/day) is the
        animal factory's real income, and EGG/FERTILIZER never crash under a
        dump. (v8's other two hunks -- the "subtract wheat the hands carry"
        feed-accounting change -- were tested and DROPPED: private.inventories
        sums every unit and is dominated by crop-sale wheat in transit, so it
        zeroed the feed reserve, the herd went underfed, and coins vs starter
        fell ~45%. So this is F1 only, not the whole v8 fold-in.)
  P2 -- FERTILIZER is a staple sell, not a "contested" thin-slice: its price
        curve is near-flat linear with a high floor, town drains it for free, and
        we were letting ~half the herd's free daily drop rot unsold.
  P4 -- stop planting tiles we cannot farm: gate the Q4 ($4k) land unlock on
        crew >= 12, cap total plants at crop_units*8 in add_plant_tasks, and
        clear late weeds (day>=18) at 2500 -- still below comfort-water 2600.
Rollback chain: v10 -> (v10 - P4) -> (P1 only) -> agents/main_v7.py.

--- v7 (parent): v5 + A3 field-fill (PLAN_V6.md Track A). PROMOTED.

v6 (angular-wedge zones + PLANT/DIG above comfort-water + stale-water skip) was a
regression -- it lost to agents/main_v4.py 3-0-9 where v5 wins 12-0-0, isolated to
the wedge-zone rewrite. v7 drops the wedge zones entirely and keeps only a
retuned field-fill: PLANT 1800->2400 and DIG 1500->2200, both held strictly below
comfort-water (2600) so a live plant is never starved to plant/dig; DIG is
zone-only. Seed-7, 12 games/opp: v4 12-0-0 (+13.3k, = v5), starter 70.6k (> v5),
wheatflood +2.5k/+6.7k p10 vs v5, premium identical to v5, animalfarm ~neutral,
v5 h2h 4-4-4. move% 64-65% (v6 was 68%), 0 err.

--- v5 (parent) ---
zoned multi-unit agent, market-aware selling, sharp endgame.

v5 = the former main_p2 endgame work folded in (pre-v5 snapshot = main_v5.py),
plus the PLAN_300K session-1 throughput bundle: a week-1 WHEAT/CARROT crop
front-load for early liquidity (choose_crops `early` branch), land expansion to
all 4 quadrants, a full 13-hand crew held through day 26, and an animal_tiles
fix so only empty tiles are reserved for animals. See PLAN_300K.md sections 2
and 8.

Endgame (the reward is locked at day 29 / hour 22 = step 718 and the day-29
_end_of_day never runs, so day-29 yield/animal ticks bank nothing and any
inventory not in the shed by hour 22 is lost): `liquidate` from day 29 hour 0;
the animal crew is disbanded on day 29 so all hands harvest-and-drop; idle
carriers drop to the shed from day 29 hour 7 (and day 28 evening) and idle
empty-handed units pre-position at the shed; `market_orders` puts every SELL
first on day 29.

Design notes (see SCORE_IMPROVEMENT_PLAN.md for the full rationale):

* The 600-score agent spent ~76% of all unit-actions on movement because it
  re-derived a global nearest-task assignment every turn, so hands oscillated
  across the whole farm. v3 gives every unit a fixed, contiguous zone and only
  lets it leave that zone for a genuine survival deadline.
* Replay 104595643 showed market inventory barely moves all season while town
  shops drain it hard, so premium/ongoing prices climb well above base
  (strawberry 297, milk 328, tomato 107). v3 keeps every serviceable tile
  planted, leans into tomato/strawberry/carrot, and sizes each SELL against a
  local copy of the price curve instead of a fixed 3-unit batch.
* End-of-day auto-drops inventory to the shed, so v3 never spends actions on
  shed round-trips except during final-day liquidation.
"""
import math
from collections import Counter

# seed cost, first_yield_day, max_yield_day, ongoing, plant-by day
CROPS = {
    "WHEAT":      (10, 2, 4, False, 26),
    "CARROT":     (20, 2, 3, False, 26),
    "TOMATO":     (50, 8, 8, True, 20),
    "STRAWBERRY": (100, 10, 10, True, 13),
    "MELON":      (80, 10, 12, False, 18),
}
ONE_TIME = {"WHEAT", "CARROT", "MELON"}

BASE = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250,
        "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}

# base, I0, T, below_func, below_target, above_func, above_target
MKT = {
    "WHEAT":      (25, 10000, 400, "sqrt", 0.80, "log", 0.20),
    "CARROT":     (35, 10000, 450, "hinge", 1.00, "sqrt", 0.70),
    "TOMATO":     (60, 10000, 200, "hinge", 0.40, "sqrt", 0.60),
    "STRAWBERRY": (120, 10000, 100, "sqrt", 0.70, "linear", 1.60),
    "MELON":      (250, 10000, 300, "log", 0.20, "sq", 3.60),
    "EGG":        (50, 10000, 332, "hinge", 0.40, "log", 0.20),
    "MILK":       (160, 10000, 122, "sqrt", 0.60, "linear", 1.60),
    "WOOL":       (200, 10000, 105, "log", 0.20, "sq", 3.20),
    "FERTILIZER": (100, 10000, 200, "linear", 0.40, "linear", 0.40),
}

SHOPS = {
    "BAKERY": ["EGG", "WHEAT"], "PIZZA_SHOP": ["MILK", "TOMATO", "WHEAT"],
    "BRUNCH_SPOT": ["EGG", "WHEAT", "STRAWBERRY"], "YARN_STORE": ["WOOL"],
    "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"], "PET_CAFE": ["CARROT"],
    "SMOOTHIE_SHOP": ["STRAWBERRY", "MILK"],
    "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"],
}

SHED_TILES = {(4, 4), (5, 4), (4, 5), (5, 5)}
SHED_CENTER = (4.5, 4.5)
PREMIUM = {"STRAWBERRY", "MELON", "MILK", "WOOL"}

USE_ANIMALS = True
# cost, structure, build_op, first_yield_day, interval, product
ANIMALS = {
    "COW":   (400, "PASTURE", "BUILD_PASTURE", 8, 2, "MILK"),
    "SHEEP": (500, "PASTURE", "BUILD_PASTURE", 6, 3, "WOOL"),
    "GOOSE": (300, "COOP",    "BUILD_COOP",    4, 1, "EGG"),
}

# ---------------------------------------------------------------------------
# Workstream B toggles (docs/IMPACT_RANKED_LEADERBOARD_PLAN.md).
#
# Each flag below replaces exactly one main.py constant with a value mined
# from real top-10 replays (tools/mine_top_policy_rules.py; the evidence is
# in experiments/LEDGER.md's "Top-policy land/animal mining" row). Setting a
# flag to False restores the exact main.py behavior it replaces -- byte-
# identical, not just "similar" -- so all-False is a self-test (it must play
# identically to main.py) and any single flag can be flipped on alone to
# bisect the bundled 100-pair Gate-B screen (LEDGER's "Workstream B
# candidate" row, INCONCLUSIVE: headline +3.5% but CI crosses zero, and the
# two archetypes the rules target -- bot_animalfactory_v2, bot_top10clone --
# read flat-to-negative on their own). Run bisection with:
#   python compete.py --agent experiments/candidate_top10rules.py \
#       --baseline main.py --league experiments/adversarial_league_v1.json \
#       --games 100 --pick-seed 2026
# after editing exactly one flag, to isolate which rule (if any) is actually
# carrying or hurting the bundle.

ENABLE_R1_LAND_FILL_GATE = False
# R1 -- how full the *current* land must be before buying the next quadrant.
# Mined: top players buy NE only once NW is 18-20/25 plants (fill ~0.72-0.80)
# and SW only once the 2-quadrant field hits 30-41/50 (fill ~0.60-0.82) -- a
# field-saturation gate stricter than main.py's 0.55, which was letting the
# crew split across quadrants before the first one was mostly worked.
R1_FILL_THRESHOLD = 0.75                     # main.py value when this flag is False: 0.55

ENABLE_R2_DISABLE_Q4 = False
# R2 -- whether the 4th quadrant (SE, $4000) can ever be bought. Mined: 0/17
# farm-episodes that reach 3 quadrants ever buy the 4th, including several
# sitting on $15k-$17k cash when the window passes -- a real behavioral cap
# in top play, not a coincidence of capacity math. main.py (this flag False)
# instead trusts a computed ROI check that happens to usually evaluate false;
# True hard-disables the buy outright so the cap doesn't depend on that
# formula continuing to fail. Pure on/off -- no separate numeric config.

ENABLE_R3_HERD_CAP = True
# R3 -- the herd-size ceiling per quadrants-owned, and the per-species targets
# used to reach it. Mined: the day-by-day trajectory (median over 18 top
# farm-episodes) shows herd size already at 4-6 on 1 quadrant (days 0-6),
# 8-13 through the 2-quadrant window (days 7-11), then plateauing 14-15 once
# the 3rd quadrant lands (day 12+) -- main.py's {1:3, 2:8}/13 caps undershoot
# all three tiers, not just the last one. `main.py`'s existing "buy one per
# turn" pacing (see market_orders' animal-buy loop) already matches the
# mined qty-1, day-0-to-15 trickle shape and is untouched by this flag.
R3_HERD_CAP = {1: 6, 2: 13}                  # main.py value when False: {1: 3, 2: 8}
R3_HERD_CAP_DEFAULT = 15                     # main.py value when False: 13 (nq==3+)
R3_WANT_NORMAL = {"COW": 10, "GOOSE": 3}     # main.py value when False: {"COW": 9, "GOOSE": 2}
R3_WANT_MATCHED = {"COW": 6, "GOOSE": 6, "SHEEP": 2}   # main.py value when False: {"COW": 5, "GOOSE": 5, "SHEEP": 1}

ENABLE_R3_CREW_FIX = True
# R3 fix -- root-caused this session: the crew-size formula
# `1 + max(n_animals, len(reserved))//5` sizes the animal crew off the
# *reservation target* (len(reserved), set to the full R3_HERD_CAP the day a
# quadrant opens), not the actual current herd. R3's 13->15 cap bump crosses
# the //5 boundary (13->3 crew, 15->4 crew) immediately, pulling a 4th crop
# hand off the field from day 1 even though the herd hasn't grown yet -- the
# same mechanism the rejected E2-candidate-4 fixed-crew test showed costs
# crop margin. This flag drops len(reserved) from the crew-size formula so
# crew scales with animals actually owned. False restores the exact
# max(n_animals, len(reserved)) formula (main.py's current behavior).
# ---------------------------------------------------------------------------


def _shape(func, x, T):
    x = max(0.0, x)
    if func == "linear":
        return x
    if func == "sq":
        return x * x
    if func == "sqrt":
        return math.sqrt(x)
    if func == "log":
        return math.log(1.0 + x)
    if func == "hinge":
        if not T or T <= 0:
            return x
        u = x / T
        return u + 8.0 * max(0.0, u - 1.0) ** 2
    return x


def price_at(item, inv):
    p = MKT.get(item)
    if not p:
        return BASE.get(item, 1)
    base, I0, T, bf, bt, af, at = p
    if inv < I0:
        amp = bt * base / _shape(bf, T, T)
        val = base + amp * _shape(bf, I0 - inv, T)
    else:
        amp = at * base / _shape(af, T, T)
        val = base - amp * _shape(af, inv - I0, T)
    return max(1, int(round(val)))


# ---- Lever 2 (docs/PLAN_TOP10.md): a computed marginal-value estimator,
# instead of the hand-tuned priority/share constants TOP10_TEARDOWN kept
# needing a fresh replay teardown to re-derive (finding 1: the land gate;
# finding 3: the crop-mix shares). MAX_YIELD/INTERVAL are the real engine
# constants (kaggle_environments/envs/kaggriculture/kaggriculture.py's own
# CROPS table), not a guess -- CROPS above only carries what the rest of
# main.py already needed (cost/first_yield/max_yield_day/ongoing/plant_by).
MAX_YIELD = {"WHEAT": 6, "CARROT": 4, "TOMATO": 4, "STRAWBERRY": 4, "MELON": 6}
INTERVAL = {"TOMATO": 1, "STRAWBERRY": 2}          # ongoing crops only
# Per-tile yield used to discount a crop's *projected* market inventory as
# more of it gets committed within one choose_crops call / by the opponent's
# existing field -- a rough one-harvest-cycle magnitude, not the full-season
# total (that would overstate near-term price impact for a slow ongoing crop
# harvested gradually over many days).
_PICK_DECAY = {"WHEAT": 3, "CARROT": 2, "TOMATO": 1, "STRAWBERRY": 1, "MELON": 4}


def _crop_tile_value(crop, cost, fy, my, ongoing, remaining, price):
    """Expected ($ per tile per remaining season-day, realistic total yield)
    for planting `crop` right now, given `remaining` days left before
    liquidation and a representative sale `price`. Replaces a hand-set
    target share with the engine's actual growth math:

    * one-time crops accrue +1 yield/watered day (unfertilized) across the
      [(max_yield_day+1)//2, max_yield_day] window, capped at MAX_YIELD, and
      occupy the tile through ~max_yield_day+1 days (main.py lets it "fatten"
      one extra day before harvesting, see build_tasks);
    * ongoing crops accrue +1 yield unit every `interval` days once past
      first_yield_day, harvested every tick so it never decays into a weed.

    Returns (value, expected_total_yield); value <= 0 means "don't plant
    this," e.g. too little season left to reach first_yield_day.
    """
    if remaining < fy:
        return -1.0, 0
    if not ongoing:
        window_start = (my + 1) // 2
        yield_est = min(MAX_YIELD[crop], my - window_start + 1)
        occupancy = min(remaining, my + 1)
        return (price * yield_est - cost) / max(1, occupancy), yield_est
    interval = INTERVAL[crop]
    n_ticks = max(0, remaining - fy) // interval + 1
    yield_est = n_ticks
    return (price * yield_est - cost) / remaining, yield_est


def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def step_toward(a, b):
    x, y = a
    X, Y = b
    if x < X:
        return ["EAST"]
    if x > X:
        return ["WEST"]
    if y < Y:
        return ["SOUTH"]
    if y > Y:
        return ["NORTH"]
    return ["PASS"]


def inv_total(inv):
    return sum(max(0, int(v)) for v in (inv or {}).values())


def unlocked_cells(me):
    """All non-locked (x, y) tiles, in a boustrophedon sweep order."""
    tiles = me.get("tiles", [])
    cells = []
    for y, row in enumerate(tiles):
        xs = range(len(row)) if y % 2 == 0 else range(len(row) - 1, -1, -1)
        for x in xs:
            if row[x] != "LOCKED":
                cells.append((x, y))
    return cells


def make_zones(cells, n_units):
    """Split the swept cell list into n_units contiguous, near-equal slices."""
    n_units = max(1, n_units)
    if not cells:
        return [set() for _ in range(n_units)]
    per = len(cells) / n_units
    zones = []
    for i in range(n_units):
        lo = int(round(i * per))
        hi = int(round((i + 1) * per))
        zones.append(set(cells[lo:hi]))
    # guarantee every unit owns at least one cell if there are enough
    for i in range(n_units):
        if not zones[i] and cells:
            zones[i].add(cells[min(i, len(cells) - 1)])
    return zones


def field_counts(farm):
    c = Counter()
    for row in farm.get("tiles", []):
        for t in row:
            if isinstance(t, dict) and t.get("kind") == "PLANT":
                c[t.get("crop")] += 1
    return c


def demand_counts(obs):
    d = Counter()
    for shop in (obs.get("town") or {}).get("unlocked_shops", []):
        for item in SHOPS.get(str(shop).strip().upper().replace(" ", "_").replace("-", "_"), []):
            d[item] += 1
    return d


def _placed_animal_counts(me):
    c = Counter()
    for row in me["tiles"]:
        for t in row:
            if isinstance(t, dict) and t.get("animal"):
                c[t["animal"]] += 1
    return c


def animal_targets(obs, me):
    """How many of each animal we want. Replay 104701051: both top agents ran
    12-15 animals (mostly COW) and by the back half of the season their farms are
    animal-dominated. Animals produce milk/wool/egg indefinitely with no replant
    labour AND drop 1 fertilizer/day each for free (even unfed) -- that fertilizer
    line alone was ~23k coins for one of the winners. A fresh cow still needs ~10
    days to break even, so we stop adding animals after day 17 and just hold."""
    if not USE_ANIMALS:
        return {}
    day = obs.get("day", 0)
    have = _placed_animal_counts(me)
    if day > 17:
        return dict(have)                       # freeze; no new reservations
    nq = len(me.get("unlocked_quadrants", []))
    # R3 toggle (see the config block above `USE_ANIMALS`): the old
    # {1:3, 2:8}/13 caps and 9/2/1-ish want shares were themselves
    # hand-tuned; ENABLE_R3_HERD_CAP swaps in the mined replacements
    # (or reproduces the exact main.py numbers when False).
    if ENABLE_R3_HERD_CAP:
        cap = R3_HERD_CAP.get(nq, R3_HERD_CAP_DEFAULT)
    else:
        cap = {1: 3, 2: 8}.get(nq, 13)
    dem = demand_counts(obs)
    # opponent-conditional scale (PLAN_LADDER_V10 F1). MILK/WOOL floor to single digits
    # when both players dump them, but FERTILIZER (free, 1/animal/day, even
    # unfed) and EGG do not, and 105 ladder episodes show the animal factories
    # win on that fertilizer line while our old crouch (cap 6) forfeited it. So
    # vs an animal-heavy opponent we now MATCH the herd, weighted GOOSE/COW over
    # SHEEP (WOOL is the line that floors under a dump).
    opp_farm = obs["farms"][1 - obs["player"]]
    opp_animals = sum(1 for row in opp_farm.get("tiles", []) for t in row
                      if isinstance(t, dict) and t.get("animal"))
    if day >= 7 and opp_animals >= 4:
        want = dict(R3_WANT_MATCHED) if ENABLE_R3_HERD_CAP else {"COW": 5, "GOOSE": 5, "SHEEP": 1}
    else:
        base_want = R3_WANT_NORMAL if ENABLE_R3_HERD_CAP else {"COW": 9, "GOOSE": 2}
        want = {**base_want, "SHEEP": 2 if dem["WOOL"] else 1}
    out, tot = {}, 0
    for a in ("COW", "GOOSE", "SHEEP"):
        take = max(have[a], min(want[a], cap - tot))
        if take:
            out[a] = take
            tot += take
    return out


def animal_tiles(me, targets):
    """Tiles devoted to animals: every tile that already holds one of our
    coops/pastures, plus fresh reservations near the shed while still expanding."""
    tiles = me["tiles"]
    existing = [
        (x, y)
        for y, row in enumerate(tiles) for x, t in enumerate(row)
        if isinstance(t, dict) and t.get("kind") in ("COOP", "PASTURE")
    ]
    k = sum(targets.values())
    if k <= len(existing):
        return existing
    taken = set(existing)
    # Only reserve genuinely empty tiles. Reserving a planted tile deadlocks the
    # animal crew (BUILD_* no-ops on a non-empty tile and the crew has no DIG
    # step), which stranded bought animals in the shed in the old probe.
    free = sorted(
        ((x, y) for y, row in enumerate(tiles) for x, t in enumerate(row)
         if t is None and (x, y) not in SHED_TILES and (x, y) not in taken),
        key=lambda c: (abs(c[0] - 4.5) + abs(c[1] - 4.5), c),
    )
    return existing + free[: k - len(existing)]


def animal_crew_actions(obs, me, private, reserved, crew_idx, positions, invs):
    """Forced actions {unit_idx: action} for the dedicated animal crew.

    The crew handles the parts a generic task can't express: FEED (consumes wheat
    from the acting unit's own inventory), CARE, placing bought animals, building
    coops/pastures, and hauling wheat out of the shed. Fertilizer collection and
    produce harvest are emitted as ordinary tasks in build_tasks so any of the
    ~13 units can grab them opportunistically -- the crew just guarantees nothing
    starves (2 unfed days => the animal escapes for good)."""
    if not reserved or not crew_idx:
        return {}
    tiles = me["tiles"]
    shed = private.get("shed", {}) or {}

    placed, empty_struct, build_spots = [], [], []
    for (x, y) in reserved:
        t = tiles[y][x]
        if isinstance(t, dict) and t.get("animal"):
            placed.append(((x, y), t))
        elif isinstance(t, dict) and t.get("kind") in ("COOP", "PASTURE"):
            empty_struct.append(((x, y), t.get("kind")))
        elif t is None:
            build_spots.append((x, y))

    feedable = {p for p, t in placed if not t.get("fed_today", False)}
    care_spots = {p for p, t in placed
                  if t.get("fed_today", False) and not t.get("cared_today", False)}
    yield_or_fert = {p for p, t in placed
                     if t.get("yield_units", 0) > 0 or t.get("fertilizer_available", False)}
    in_shed_animals = [a for a in ANIMALS if int(shed.get(a, 0)) > 0]
    shed_wheat = int(shed.get("WHEAT", 0))
    by_pos = {p: t for p, t in placed}

    out, claimed = {}, set()
    for idx in crew_idx:
        if idx >= len(positions):
            continue
        pos = tuple(positions[idx])
        inv = invs[idx] if idx < len(invs) else {}
        wheat = int(inv.get("WHEAT", 0))
        shed_adj = pos in SHED_TILES
        to_shed = lambda p=pos: step_toward(p, min(SHED_TILES, key=lambda q: dist(p, q)))

        # 1. standing on one of our animals -> do the highest-value thing here
        here = by_pos.get(pos)
        if here is not None and pos not in claimed:
            if pos in feedable and wheat > 0:
                out[idx] = ["FEED"]; claimed.add(pos); continue
            if here.get("yield_units", 0) > 0:
                out[idx] = ["HARVEST"]; claimed.add(pos); continue
            if here.get("fertilizer_available", False):
                out[idx] = ["COLLECT_FERTILIZER"]; claimed.add(pos); continue
            if pos in care_spots:
                out[idx] = ["CARE"]; claimed.add(pos); continue

        pending_feed = [p for p in feedable if p not in claimed]
        # 2. out of wheat with animals still to feed -> resupply from the shed
        if pending_feed and wheat == 0 and shed_wheat > 0:
            if shed_adj:
                take = min(8, shed_wheat)
                shed_wheat -= take
                out[idx] = ["PICKUP", "WHEAT", take]
            else:
                out[idx] = to_shed()
            continue

        # 3. walk to the nearest animal that needs service
        goals = [p for p in pending_feed if wheat > 0]
        goals += [p for p in yield_or_fert if p not in claimed]
        goals += [p for p in care_spots if p not in claimed]
        if goals:
            tgt = min(goals, key=lambda p: dist(pos, p))
            claimed.add(tgt)
            out[idx] = step_toward(pos, tgt) if tgt != pos else ["PASS"]
            continue

        # 4. place a bought animal onto a matching empty structure
        if in_shed_animals and empty_struct:
            a = in_shed_animals[0]
            spot = next((p for p, k in empty_struct
                         if k == ANIMALS[a][1] and p not in claimed), None)
            if spot:
                if int(inv.get(a, 0)) > 0:
                    if pos == spot:
                        out[idx] = ["PLACE", a]; claimed.add(spot)
                    else:
                        out[idx] = step_toward(pos, spot)
                elif shed_adj:
                    out[idx] = ["PICKUP", a, 1]
                else:
                    out[idx] = to_shed()
                continue

        # 5. build a structure on a reserved empty tile
        if in_shed_animals and build_spots:
            spot = min((s for s in build_spots if s not in claimed),
                       key=lambda p: dist(pos, p), default=None)
            if spot is not None:
                claimed.add(spot)
                out[idx] = [ANIMALS[in_shed_animals[0]][2]] if pos == spot \
                    else step_toward(pos, spot)
                continue

        # 6. nothing pressing -> keep the crew near the herd
        if placed:
            tgt = min((p for p, _ in placed), key=lambda p: dist(pos, p))
            if tgt != pos:
                out[idx] = step_toward(pos, tgt)
    return out


def choose_crops(obs, me, private, counts, plant_slots):
    """Return a list of crop names (length == plant_slots) to plant this turn."""
    day = obs.get("day", 0)
    prices = (obs.get("market") or {}).get("prices", {})
    mkt_inv = (obs.get("market") or {}).get("inventory", {})
    opp = field_counts(obs["farms"][1 - obs["player"]])
    total = max(1, sum(counts.values()) + plant_slots)

    # Week 1 is a liquidity race, not a value race. Probe of the old mix: the
    # field sat at 1 quadrant and $206 cash until ~day 15 because week-1 plantings
    # were tomato/strawberry/melon (first yield day 8-10+), so nothing was
    # harvestable to fund the 2nd quadrant. Front-load WHEAT + CARROT (first yield
    # day 2) so cash flows from ~day 4 and the land/hands snowball can start. This
    # is a cash-flow-*timing* rule (raise money soon vs. raise the most money
    # eventually), a dimension the Lever 2 value calc below doesn't model --
    # keep it as a fixed bootstrap rather than folding it into the calc.
    early = day < 7
    if early:
        targets = {}
        for crop, (cost, fy, my, ongoing, plant_by) in CROPS.items():
            if day > plant_by:
                continue
            pr = prices.get(crop, BASE[crop])
            val = pr / BASE[crop]
            if crop == "WHEAT":
                share = 0.50
            elif crop == "CARROT":
                share = 0.28
            elif crop == "TOMATO":
                share = 0.08
            elif crop == "STRAWBERRY":
                share = 0.0 if day < 4 else 0.16
            else:  # MELON: no week-1 case for it
                share = 0.0
            share *= max(0.30, min(2.0, val))
            share *= max(0.35, 1.0 - 0.18 * opp[crop])
            if share > 0:
                targets[crop] = share
        if not targets:
            return []
        ssum = sum(targets.values())
        want = {c: s / ssum * total for c, s in targets.items()}
        caps = {"MELON": 5, "CARROT": 18}
        picks = []
        cur = Counter(counts)
        for _ in range(plant_slots):
            best, bestgap = None, -1e9
            for c, w in want.items():
                if c in caps and cur[c] >= caps[c]:
                    continue
                gap = w - cur[c]
                if gap > bestgap:
                    best, bestgap = c, gap
            if best is None:
                break
            picks.append(best)
            cur[best] += 1
        return picks

    # ---- Lever 2 (docs/PLAN_TOP10.md): computed marginal value, not a
    # hand-tuned share. TOP10_TEARDOWN finding 3 was "the STRAWBERRY/TOMATO
    # shares are set backwards"; rather than re-guess the right numbers (and
    # need a fresh replay teardown the next time the meta shifts), compute
    # $-per-tile-per-remaining-day from the real engine growth/price
    # constants (_crop_tile_value) and greedily fill slots by marginal
    # value. Each pick discounts that crop's *projected* market inventory
    # (via price_at, the same price-clearing curve a real sale would hit),
    # which replaces the old fixed opp[]-count / self-share discounts with
    # an actual market-crowding calculation instead of a guessed coefficient.
    remaining = max(1, 29 - day)
    caps = {"MELON": 5, "CARROT": 10 if day <= 22 else 999}
    cur = Counter(counts)
    proj_inv = {c: mkt_inv.get(c, 0) + opp[c] * _PICK_DECAY[c] for c in CROPS}
    picks = []
    for _ in range(plant_slots):
        best, best_val = None, 0.0
        for crop, (cost, fy, my, ongoing, plant_by) in CROPS.items():
            if day > plant_by or cur[crop] >= caps.get(crop, 10**9):
                continue
            price = price_at(crop, proj_inv[crop])
            val, _ = _crop_tile_value(crop, cost, fy, my, ongoing, remaining, price)
            if val > best_val:
                best, best_val = crop, val
        if best is None:
            break
        picks.append(best)
        cur[best] += 1
        proj_inv[best] += _PICK_DECAY[best]
    return picks


def build_tasks(obs, me, private):
    """Generate (priority, (x, y), action) tuples over the whole farm."""
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    tiles = me["tiles"]
    tasks = []
    counts = Counter()
    # day 29's end-of-day never runs, so no day-29 yield tick is ever banked:
    # from hour 0 there is nothing left to grow -- only harvest + liquidate.
    liquidate = day >= 29
    for y, row in enumerate(tiles):
        for x, t in enumerate(row):
            if not isinstance(t, dict):
                continue
            pos = (x, y)
            kind = t.get("kind")
            if kind == "PLANT":
                crop = t.get("crop")
                counts[crop] += 1
                if liquidate:
                    if t.get("yield_units", 0) > 0:
                        tasks.append((5000, pos, ["HARVEST"]))
                    continue
                fy, my, ongoing = CROPS[crop][1], CROPS[crop][2], CROPS[crop][3]
                age = day - t.get("planted_day", day)
                yu = t.get("yield_units", 0)
                cu = t.get("consecutive_unwatered", 0)
                watered = t.get("watered_today", False)
                # ---- watering ----
                if not watered:
                    if cu >= 1:            # dies tonight
                        tasks.append((10000 + 5 * hour, pos, ["WATER"]))
                    elif not ongoing and (my + 1) // 2 <= age <= my:
                        tasks.append((6200 + age, pos, ["WATER"]))   # yield-window growth
                    else:
                        # P1w: in the last few turns of the day, top off an
                        # otherwise-dry plant ahead of planting (2400) and weeds
                        # (2500) so it does not enter the night unwatered and
                        # become tomorrow's 10000 survival water (and a 2-miss
                        # weed if a hand can't reach it in time).
                        tasks.append((3000 if hour >= 20 else 2600, pos, ["WATER"]))
                # ---- harvesting ----
                if yu > 0 and age >= fy:
                    if not ongoing:
                        # one-time: harvest once it stops gaining (past max window)
                        pr = 5200 if age > my else 3500 + age
                        tasks.append((pr, pos, ["HARVEST"]))
                    else:
                        mls = t.get("max_lifespan_step", -1)
                        decaying = mls >= 0 and (day + 1) * 24 >= mls
                        near_cap = yu >= 4
                        tasks.append((5000 if (decaying or near_cap) else 3200, pos, ["HARVEST"]))
            elif kind in {"COOP", "PASTURE"} and t.get("animal"):
                # FEED needs wheat in the acting unit's inventory so it stays with
                # the dedicated crew; HARVEST, COLLECT_FERTILIZER and CARE have no
                # inventory cost, so emit them as ordinary tasks any idle unit can
                # grab. CARE is a big multiplier -- a fed+cared animal banks +1
                # that is paid out (capped at max_held) on its next produce tick,
                # so on premium milk/wool that is ~+$200-300 for one action.
                if t.get("yield_units", 0) > 0:
                    tasks.append((5000 if liquidate else 4800, pos, ["HARVEST"]))
                if not liquidate and t.get("fertilizer_available", False):
                    tasks.append((2700, pos, ["COLLECT_FERTILIZER"]))
            elif kind == "WEED":
                # 2200 (>the old 1500) so the field is reclaimed faster, still
                # strictly below comfort-water (2600) -- a live plant is never
                # left dry to clear a weed. DIG is also zone-only (see assign).
                # P4c: from day 18 bump to 2500 -- late field turns fallow->weed
                # and every reclaimed tile is a replant slot, but still < 2600.
                if liquidate:
                    weed_pri = 0
                elif day >= 18:
                    weed_pri = 2500
                else:
                    weed_pri = 2200
                tasks.append((weed_pri, pos, ["DIG"]))
    return tasks, counts


def add_plant_tasks(obs, me, private, counts, tasks, n_units, reserved=()):
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    if day >= 27 or hour >= 22:
        return
    reserved = set(reserved)
    tiles = me["tiles"]
    planted = sum(counts.values())
    # fill every serviceable tile; only throttle if watering is falling behind
    capacity = len(unlocked_cells(me))
    unwatered = sum(
        1 for row in tiles for t in row
        if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today")
    )
    # P4b: hard coverage cap. Only the units NOT on the animal crew farm crops
    # (mirror agent()'s upper-bound crew sizing), and each can keep ~8 tiles
    # watered+harvested daily. Planting past that just seeds weeds29 (17-34 in
    # the loss games) -- the furthest tiles are better left fallow (0.5%/day
    # weed risk) than planted to die (~100% in 2 unwatered days).
    crop_units = max(1, n_units - min(4, max(0, n_units - 6)))
    coverage_cap = crop_units * 8
    room = min(capacity - planted,
               max(0, n_units * 22 - unwatered),
               coverage_cap - planted)
    if room <= 0:
        return
    empty = sorted(
        ((dist((x, y), (4, 4)), x, y)
         for y, row in enumerate(tiles) for x, t in enumerate(row)
         if t is None and (x, y) not in reserved),
        key=lambda e: e[0],
    )
    if not empty:
        return
    seeds = private.get("seeds", {})
    picks = choose_crops(obs, me, private, counts, min(room, len(empty), n_units * 2))
    # only expose as many PLANT tasks per crop as we have seeds (atomic-plant rule)
    seed_budget = Counter({c: int(seeds.get(c, 0)) for c in CROPS})
    pi = 0
    for _, x, y in empty:
        if pi >= len(picks):
            break
        crop = picks[pi]
        pi += 1
        if seed_budget[crop] <= 0:
            continue
        seed_budget[crop] -= 1
        # 2400: fills empty tiles faster than v5's 1800 (leaving a third of the
        # field fallow was L2/L4), but below comfort-water 2600 so a unit will
        # never walk past a dry plant to plant a new one -- the v6 regression
        # was PLANT 3200 doing exactly that.
        tasks.append((2400, (x, y), ["PLANT", crop]))


def assign(obs, me, private, tasks, zones, forced=None):
    pos = [tuple(me["farmer"])] + [tuple(p) for p in me.get("hands", [])]
    n = len(pos)
    invs = list(private.get("inventories", []))
    while len(invs) < n:
        invs.append({})
    actions = [["PASS"] for _ in range(n)]
    busy = [False] * n
    claimed = set()
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)

    # units reserved for the animal crew this turn
    for idx, act in (forced or {}).items():
        if 0 <= idx < n and act:
            actions[idx] = act
            busy[idx] = True

    # final-day: once fields are drained, march everyone to the shed to drop
    if day >= 29 and hour >= 15:
        for i, p in enumerate(pos):
            if inv_total(invs[i]) > 0:
                if p in SHED_TILES:
                    actions[i] = ["DROP"]
                else:
                    actions[i] = step_toward(p, min(SHED_TILES, key=lambda q: dist(p, q)))
                busy[i] = True

    ordered = sorted(tasks, key=lambda t: -t[0])

    def do(i, tgt, act):
        actions[i] = act if pos[i] == tgt else step_toward(pos[i], tgt)
        claimed.add(tgt)
        busy[i] = True

    # pass 0: critical work (dying plants / hungry animals) -> globally nearest unit
    for pr, tgt, act in ordered:
        if pr < 9000 or tgt in claimed:
            continue
        cand = [(dist(pos[i], tgt), i) for i in range(n) if not busy[i]]
        if cand:
            do(min(cand)[1], tgt, act)

    def try_assign(i, allow_global):
        best = None
        for pr, tgt, act in ordered:
            if tgt in claimed:
                continue
            in_zone = tgt in zones[i]
            if not allow_global and not in_zone:
                continue
            # weeds are never a survival deadline -- only clear one that falls in
            # your own zone, never walk cross-farm for it (v6's DIG 2800 pulled
            # units off crops in other zones).
            if act == ["DIG"] and not in_zone:
                continue
            d = dist(pos[i], tgt)
            # act on the tile you already stand on before walking anywhere;
            # otherwise prefer nearer work and stay in your own zone.
            # P4r: charge out-of-zone walking more (40/step vs 25) so a unit only
            # treks across the farm for a global-pass task when the priority gap
            # is real -- otherwise a nearer hand reaches it next turn anyway.
            step_cost = 25 if in_zone else 40
            eff = pr + (2000 if d == 0 else 0) + (150 if in_zone else 0) - step_cost * d
            if best is None or eff > best[0]:
                best = (eff, tgt, act)
        if best is None:
            return False
        do(i, best[1], best[2])
        return True

    for i in range(n):
        if not busy[i]:
            try_assign(i, allow_global=False)
    for i in range(n):
        if not busy[i]:
            try_assign(i, allow_global=True)

    # endgame: units keep harvesting (assigned above) but anyone now idle heads
    # to the shed -- carrying a load to DROP, or empty-handed to pre-position so
    # the next harvest->drop round-trip is short. Getting produce into the shed
    # early lets market_orders dump it over many turns before hour 22 locks in.
    endgame_drop = (day >= 29 and hour >= 7) or (day >= 28 and hour >= 19)
    if endgame_drop:
        for i in range(n):
            if busy[i]:
                continue
            sp = min(SHED_TILES, key=lambda q: dist(pos[i], q))
            if inv_total(invs[i]) > 0:
                actions[i] = ["DROP"] if pos[i] in SHED_TILES else step_toward(pos[i], sp)
                busy[i] = True
            elif day >= 29:
                if pos[i] != sp:
                    actions[i] = step_toward(pos[i], sp)
                busy[i] = True

    # idle units: creep toward the nearest tile that will need service, so the
    # morning walk out of the shed is not wasted.
    # P4r: prefer pending work inside the unit's own zone (then its zone cells)
    # before chasing a globally-nearest transient task -- an idle hand drifting
    # to whatever task tile is closest pulls itself out of position and pays two
    # walks once real work lands back in its zone.
    if not (day >= 29 and hour >= 15):
        task_tiles = [t[1] for t in ordered]
        all_pend = task_tiles + [c for z in zones for c in z]
        for i in range(n):
            if busy[i]:
                continue
            own = [t for t in task_tiles if t in zones[i]] or list(zones[i])
            pend = own or all_pend
            if not pend:
                continue
            tgt = min(pend, key=lambda c: dist(pos[i], c))
            if tgt != pos[i]:
                actions[i] = step_toward(pos[i], tgt)
    return actions


def market_orders(obs, me, private, counts, n_units):
    """Assemble up to 10 orders. Time-critical items (hiring at dawn, selling
    perishable high-value produce) go first so they are never truncated."""
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    money = float(me.get("money", 0))
    shed = private.get("shed", {}) or {}
    seeds = private.get("seeds", {}) or {}
    mkt_inv = ((obs.get("market") or {}).get("inventory", {})) or {}
    # PLAN_LADDER_V9 P1 -- break the $200 cash-floor poverty trap. The old flat
    # reserve let the hour-2 seed/wheat buy drain the farm to ~$200 for the first
    # two weeks, so the land ($1k-$4k) and animal gates never fired on schedule
    # and we stayed at 2-3 quadrants / a herd of 4-8 while animal_factory
    # opponents compounded to $10k-45k by day 15. Hold a growing working-capital
    # cushion through the build-out phase instead; drop it once the farm is
    # established and again for the terminal dump.
    if day >= 25:
        base_reserve = 60
    elif day < 16:
        # ramp a cushion that tracks a *producing* farm's float, not the whole
        # opening bankroll -- caps near the quad-2 gate ($1.4k) so land/animals
        # fire on schedule while seeds still get funded from sale income.
        base_reserve = min(1400, 200 + 150 * day)   # d1=350 ... d8+=1400 (capped)
    else:
        base_reserve = 200
    # P3f: cash-flow-aware relax. The P1 ramp above is a blind day-scaled cushion.
    # Once the shed already holds sellable value and the herd banks produce every
    # day, that money IS working capital and holding the full ramp just delays the
    # next land/animal/seed buy. Count near-term income already in the pipe --
    # unsold shed goods at their curve price + ~2 days of herd produce -- and step
    # the reserve down toward HARD_FLOOR as it covers the cushion. Never below
    # HARD_FLOOR, never above the ramp: the poverty trap was a reserve set blindly
    # LOW; this only frees value we can already see landing.
    HARD_FLOOR = 120
    n_placed_now = sum(1 for row in me["tiles"] for t in row
                       if isinstance(t, dict) and t.get("animal"))
    shed_value = sum(int(q) * price_at(it, mkt_inv.get(it, 10000))
                     for it, q in shed.items() if it in BASE and int(q) > 0)
    near_income = shed_value + n_placed_now * 90    # ~1 premium unit/animal/2days
    if near_income >= 1.5 * base_reserve:
        reserve = max(HARD_FLOOR, int(base_reserve * 0.55))
    elif near_income >= 0.75 * base_reserve:
        reserve = max(HARD_FLOOR, int(base_reserve * 0.8))
    else:
        reserve = base_reserve
    # spread seed top-ups across turns so a single call can't re-crater the farm
    seed_spend_cap = 400 if day < 10 else 800

    hires, sells, buys_hi, buys_lo = [], [], [], []

    # ---- hiring: all at the start of the day ----
    # Ladder replay 104701051: both top agents (82k / 111k coins) run 12 hands/day
    # -> 13 units -- from ~day 7 onward. Hiring 12 costs only ~375 coins (fib sum)
    # and roughly doubles labour throughput, which is the real ceiling once tiles
    # and animals scale. Ramp with unlocked area so we don't overspend on 25 tiles.
    if hour <= 1:
        nq = len(me.get("unlocked_quadrants", []))
        if day < 3:
            desired = 6
        elif day < 27:
            # hold a full crew through the whole productive season -- the old
            # probe dropped to 8 hands at day 25 while sitting on $40k, leaving
            # a third of the field as weeds. Labour is the throughput ceiling.
            desired = {1: 7, 2: 10}.get(nq, 13)
        elif day < 29:
            desired = 8
        else:
            desired = 0
        for _ in range(max(0, desired - int(me.get("hires_today", 0)))):
            hires.append(["HIRE"])

    # ---- selling: size each order against the local price curve ----
    n_placed = sum(1 for row in me["tiles"] for t in row
                   if isinstance(t, dict) and t.get("animal"))
    # keep two days of feed wheat back from the sell pile. (v8's "subtract the
    # wheat hands already carry" variant was DROPPED -- private.inventories sums
    # every unit, and it is dominated by crop-sale wheat in transit on the crop
    # hands, not feed wheat on the animal crew; it zeroed the floor, the herd
    # went underfed, and coins vs starter fell ~45%. See docs/PLAN_LADDER_V10.md.)
    wheat_floor = (2 * n_placed + 4) if (USE_ANIMALS and n_placed and day < 28) else 0
    for item, qty in list(shed.items()):
        qty = int(qty)
        if item == "WHEAT":
            qty -= wheat_floor
        if qty <= 0 or item not in BASE:
            continue
        inv0 = mkt_inv.get(item, 10000)
        base = BASE[item]
        p0 = price_at(item, inv0)
        # contested animal products (30 ladder games: prices collapse to <10 when
        # both farms dump) -- sell only a thin slice per turn and never into a
        # real dip; the day-28 full-dump branch still clears the shed.
        contested = item in ("MILK", "WOOL")
        staple_fert = item == "FERTILIZER"
        if day >= 28:
            amount = qty
        elif staple_fert:
            # PLAN_LADDER_V10 P2. FERTILIZER is a free by-product (1/animal/day,
            # even unfed) on a near-flat linear price curve with a high floor,
            # and the town drains it faster than production so it sits above
            # base most of the season. The old "contested" treatment (cap 8,
            # keep 0.72*base) left ~half the herd's daily drop rotting unsold.
            # Move a big slice every turn; only sit out a genuine deep dip.
            keep = 0.45 * base
            cap = 25
            amount = 0
            while amount < min(qty, cap) and price_at(item, inv0 + 2 * amount) >= keep:
                amount += 1
            if amount == 0 and p0 >= 0.30 * base:
                amount = min(qty, 5)
        elif contested and p0 < 0.5 * base:
            amount = 0
        else:
            prem = item in PREMIUM
            keep = (0.80 if prem else 0.72) * base
            cap = 6 if prem else 16
            if contested:
                cap = 8
            if p0 >= 1.4 * base:            # far from a glut -> move more
                cap = int(cap * min(4.0, p0 / base))
            amount = 0
            while amount < min(qty, cap) and price_at(item, inv0 + 2 * amount) >= keep:
                amount += 1
            if amount == 0 and p0 >= 0.55 * base and not contested:
                amount = 1
        if amount > 0:
            sells.append((p0 * amount, ["SELL", item, amount]))
    sells.sort(key=lambda s: -s[0])         # highest-value produce first
    sells = [s[1] for s in sells]

    # ---- land: quadrants 2 & 3 as soon as the current fill and cash allow;
    # quadrant 4 ($4k) later and only when genuinely rich, since it is only worth
    # it with the hands to work it and a back-half long enough to pay it back.
    unlocked = list(me.get("unlocked_quadrants", []))
    open_tiles = len(unlocked_cells(me))
    if hour <= 3 and len(unlocked) < 4:
        nth = len(unlocked) - 1                       # 0/1 -> quad 2/3, 2 -> quad 4
        cost = (1000, 2000, 4000)[nth]
        fill = sum(counts.values()) / max(1, open_tiles)
        if nth < 2:
            # R1 toggle: mined top-10 land buys only happen once the
            # *current* land is near-fully planted (NE bought at 18-20/25
            # plants, SW at 30-41/50) -- fill ~0.72-0.82, stricter than
            # main.py's 0.55, which split the crew across quadrants before
            # the first one was even mostly worked. False reproduces 0.55.
            fill_threshold = R1_FILL_THRESHOLD if ENABLE_R1_LAND_FILL_GATE else 0.55
            ok = day <= 18 and fill >= fill_threshold and money >= cost + 400 + 200 * nth
        elif ENABLE_R2_DISABLE_Q4:
            # R2 toggle, on: 0/17 real top-10 farm-episodes that reach 3
            # quadrants ever buy the 4th (SE, $4000) -- not because they
            # couldn't afford it (several sit on $15k-$17k when the window
            # passes), but because it is a real behavioral cap, not merely a
            # capacity-math coincidence. Encode the cap directly rather than
            # trust the ROI formula below to keep failing.
            ok = False
        else:
            # R2 toggle, off: main.py's original computed ROI gate (Lever 2,
            # docs/PLAN_TOP10.md) -- crew capacity via add_plant_tasks' own
            # coverage_cap formula, and whether the best crop's computed
            # $/tile/remaining-day value clears the $4000 cost with margin.
            remaining = max(1, 29 - day)
            quadrant_tiles = 25
            crop_units = max(1, n_units - min(4, max(0, n_units - 6)))
            coverage_cap = crop_units * 8
            has_slack = (open_tiles + quadrant_tiles) <= coverage_cap
            best_val = 0.0
            for crop, (c_cost, fy, my, ongoing, plant_by) in CROPS.items():
                if day > plant_by:
                    continue
                price = price_at(crop, mkt_inv.get(crop, 0))
                val, _ = _crop_tile_value(crop, c_cost, fy, my, ongoing, remaining, price)
                best_val = max(best_val, val)
            expected_revenue = best_val * quadrant_tiles * remaining
            ok = (has_slack and expected_revenue >= cost * 1.5
                  and money >= cost + 2500)
        if ok:
            buys_hi.append(["BUY_LAND"])

    # ---- animals ----
    if USE_ANIMALS:
        have = Counter()
        for row in me["tiles"]:
            for t in row:
                if isinstance(t, dict) and t.get("animal"):
                    have[t["animal"]] += 1
        placed_total = sum(have.values())
        pending = int(sum(v for k, v in shed.items() if k in ANIMALS))
        if hour <= 6:
            for a, want in animal_targets(obs, me).items():
                cur = have[a] + int(shed.get(a, 0))
                # buy one per turn; keep enough cash for the season's running costs
                if cur < want and money >= ANIMALS[a][0] + 300 + 150 * placed_total:
                    buys_hi.append(["BUY_ANIMAL", a, 1])
                    money -= ANIMALS[a][0]
                    break
        if (placed_total or pending) and hour <= 4:
            need_w = 2 * (placed_total + pending) + 4
            have_w = int(shed.get("WHEAT", 0))
            if have_w < need_w:
                wp = max(1, price_at("WHEAT", mkt_inv.get("WHEAT", 10000)))
                # P?f2: feed is a survival buy, not a discretionary one. Every
                # other reserve-gated purchase (land/seeds/new animals) just
                # gets *delayed* by a tight cushion; missing feed for 2
                # consecutive days permanently loses the animal -- its full
                # sunk cost and every future day's produce/fertilizer, forever.
                # That's a strictly worse outcome than dipping the working
                # capital cushion by a few coins, so once the shed is fully
                # out of feed wheat with animals actually needing it, cap the
                # buy against a much smaller emergency float instead of the
                # full day-scaled `reserve`. Restocking while some feed is
                # still on hand (have_w>0) stays reserve-gated as before --
                # only a genuine zero-wheat emergency bypasses the cushion.
                FEED_EMERGENCY_FLOOR = 30
                if have_w == 0:
                    # P3f self-play trace (seed 151042320 vs agents/main_v11.py):
                    # this branch was firing almost every day (near-max WHEAT
                    # buys 11 of 14 opening days) because the *normal* reserve
                    # gate below routinely blocks restocking while cash is
                    # tight, so the shed empties out and the floor fires again
                    # tomorrow. Each trigger was funding the full 2-day
                    # `need_w` buffer against the tiny floor, bleeding cash
                    # that the reserve gate would otherwise have banked toward
                    # the next land buy -- main.py ended that game with MORE
                    # animals than v11 (8 vs 6) but far less money (6.6k vs
                    # 15.3k). Only the true emergency ration (today's feed, no
                    # forward buffer) needs the cushion bypass; the 2-day
                    # buffer is a discretionary top-up and stays reserve-gated.
                    feed_reserve = FEED_EMERGENCY_FLOOR
                    emerg_need = placed_total + pending
                    b = min(emerg_need - have_w, 10, int(max(0, money - feed_reserve) // wp))
                else:
                    feed_reserve = reserve
                    b = min(need_w - have_w, 10, int(max(0, money - feed_reserve) // wp))
                if b > 0:
                    buys_hi.append(["BUY_PRODUCT", "WHEAT", b])
                    money -= b * wp

    # ---- seeds: keep a small buffer for the crops we mean to plant ----
    if day < 27:
        need = Counter(choose_crops(obs, me, private, counts, n_units * 2))
        buf = 3 if n_units <= 4 else 4
        spent = 0
        for crop in sorted(need, key=lambda c: -need[c]):
            have = int(seeds.get(crop, 0))
            target = min(need[crop] + buf, 12)
            cost = CROPS[crop][0]
            budget = min(max(0, money - reserve), max(0, seed_spend_cap - spent))
            b = min(max(0, target - have), int(budget // max(1, cost)))
            if b > 0:
                buys_lo.append(["BUY_SEED", crop, b])
                money -= b * cost
                spent += b * cost

    # assemble: hires -> top 3 sells -> land/animal/feed -> seeds -> rest of sells
    if day >= 29:
        # nothing left to invest in; every order slot goes to the terminal dump
        out = sells + hires + buys_hi + buys_lo
    else:
        out = hires + sells[:3] + buys_hi + buys_lo + sells[3:]
    return out[:10]


def agent(obs):
    try:
        player = int(obs.get("player", 0))
        farms = obs.get("farms", [])
        if len(farms) < 2:
            return {"farmer": ["PASS"], "hands": [], "market": []}
        me = farms[player]
        private = obs.get("private") or {}
        n_units = 1 + len(me.get("hands", []))

        cells = unlocked_cells(me)

        reserved = animal_tiles(me, animal_targets(obs, me)) if USE_ANIMALS else []
        forced = {}
        n_crew = 0
        # day 29: FEED/CARE bank nothing (their tick never resolves); disband the
        # crew so every hand joins the harvest-and-drop liquidation.
        if reserved and obs.get("day", 0) < 29:
            n_animals = sum(1 for row in me["tiles"] for t in row
                            if isinstance(t, dict) and t.get("animal"))
            # size the crew to the herd, but always leave >=6 units on crops
            crew_basis = n_animals if ENABLE_R3_CREW_FIX else max(n_animals, len(reserved))
            n_crew = min(4, max(0, n_units - 6), 1 + crew_basis // 5)
            if n_crew > 0:
                crew_idx = list(range(n_units - n_crew, n_units))   # the last hands
                positions = [tuple(me["farmer"])] + [tuple(p) for p in me.get("hands", [])]
                invs = private.get("inventories", []) or []
                forced = animal_crew_actions(obs, me, private, reserved,
                                             crew_idx, positions, invs)

        # crop zones cover only the non-crew units; crew units get an empty zone
        zones = make_zones(cells, max(1, n_units - n_crew))
        zones += [set() for _ in range(n_units - len(zones))]

        tasks, counts = build_tasks(obs, me, private)
        add_plant_tasks(obs, me, private, counts, tasks, n_units, reserved)
        actions = assign(obs, me, private, tasks, zones, forced=forced)

        market = market_orders(obs, me, private, counts, n_units)
        return {"farmer": actions[0], "hands": actions[1:], "market": market}
    except Exception:
        try:
            n = len(obs["farms"][obs["player"]].get("hands", []))
        except Exception:
            n = 0
        return {"farmer": ["PASS"], "hands": [["PASS"] for _ in range(n)], "market": []}


if __name__ == "__main__":
    print("Kaggriculture Agent v11 (v10 + P3f cash-flow reserve + P1w evening water "
          "+ P4r walk-aware assign; P2k crop-prune tried & reverted)")
