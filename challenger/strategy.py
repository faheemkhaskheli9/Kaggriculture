"""Strategic controller for the replacement-policy challenger (IMPACT plan §8).

This is layer 1 of the three-layer challenger: it emits *targets* (herd size and
species split, quadrant allowance, hand ceiling) that the shared safety/execution
machinery in ``main.py`` then realises. It does NOT touch routing, maintenance,
market cadence, or endgame liquidation -- those stay byte-identical to the
promoted incumbent.

Every constant here is derived from real top-10 ladder replays, not hand-tuned:
``ml/artifacts/top_policy_rules.json`` (produced by ``tools/mine_top_policy_rules.py``
over 18 verified top-10 farms / 12,960 turns). The relevant mined facts:

* ``day_trajectory`` herd_median by day:
    d0=0 d1=4 d2=4 d3=5 d4..6=6 d7=8 d8=10 d9=12 d10..11=13 d12=14 d13=14.5
    d14..21=15  (late dips to ~14 are culling/escape noise -- we hold 15).
* ``day_trajectory`` quadrants_median: 1 through day 6, 2 on days 7-11,
    3 from day 12; the 4th quadrant is NEVER bought (0/17 farms that reach 3).
* ``buy_land`` transitions: 1->2 at day 5-6 (median plants 19); 2->3 at day
    8-11 (median plants 34).
* ``buy_animal`` species totals across the sample: COW 80u, SHEEP 101u,
    GOOSE 29u  ->  ~ 6 / 6 / 3 at a 15-head plateau. GOOSE first appears
    ~day 6-7 (never day 0); COW/SHEEP start day 0.
* ``buy_animal`` batch_qty median 1 (never a multi-head single-turn binge).

v0 deliberately does not override crop mix: the held-out imitation benchmark
(``ml/artifacts/top_policy_benchmark.json``) shows BUY_SEED family F1 is only
~0.50 and per-crop far worse, so seed choice is left to the incumbent's tuned
``choose_crops`` until a value-based crop rule replaces it.
"""

# herd_median by day index (0..29), clamped/held per the docstring.
_HERD_BY_DAY = [
    0, 4, 4, 5, 6, 6, 6, 8, 10, 12,      # d0-d9
    13, 13, 14, 15, 15, 15, 15, 15, 15, 15,  # d10-d19
    15, 15, 15, 15, 15, 15, 15, 15, 15, 15,  # d20-d29
]

# Herd may not outrun the field it has to live on: reserving N animal tiles
# while only one 5x5 quadrant is open deadlocks planting (the LIVESTOCK_ENGINE
# bug that HERD_CAP_BY_QUADRANTS fixed). Caps chosen so d0-6 (nq==1) can still
# reach the mined herd of 6.
_HERD_CAP_BY_QUADRANTS = {1: 6, 2: 13, 3: 15, 4: 15}

# Species split at the 15-head plateau, from mined BUY_ANIMAL unit totals
# (COW 80 : SHEEP 101 : GOOSE 29).
_HERD_SPLIT = (("COW", 6), ("SHEEP", 6), ("GOOSE", 3))
_GOOSE_FIRST_DAY = 6

# Quadrant allowance by day, from mined quadrants_median + buy_land transitions.
_MAX_QUADRANTS_BY_DAY = (
    (12, 3),   # day >= 12  -> allow 3
    (5, 2),    # day >= 5   -> allow 2
    (0, 1),    # otherwise  -> 1
)

# Mined hands_at_buy tops out at 12 across the whole top-10 sample.
_MAX_HANDS = 12
_FEED_STOCK_DAYS = 2

# --- bisection toggles (v0 Gate-B was -10.4%; isolate which knob regresses) ---
# ENABLE_HERD_SCHEDULE: layer-1 herd target from the mined day/quadrant curve.
#   OFF -> defer to main.animal_targets (incumbent herd logic).
# ENABLE_QUADRANT_GATE: day-gated max_quadrants (1/2/3 by day).
#   OFF -> keep the incumbent's max_quadrants (4) so land timing is unchanged.
# ENABLE_HAND_CAP: max_hands=12 instead of the incumbent's 13.
import os as _os

# v0 bisection (2026-09-06, compete_runs/20260906-01*, 64 paired vs main.py):
#   HERD only  -> -10.2%  CI[-16.4,-3.9]  (THE v0 regression: -413 productive
#                 actions, -361 day10 cash, loses 16/18 h2h to the incumbent)
#   QUAD only  -> +5.5%   CI[-3.1,+13.3]  (neutral, mildly positive h2h)
#   HANDS only -> +13.3%  CI[+6.2,+20.3]  (beats incumbent 10/7/1; but the whole
#                 signal is in the main self-play bucket -- core bots flat --
#                 the pattern the repo's history says does not convert on ladder)
# Defaults ALL OFF: challenger/agent.py is then a verified exact no-op vs main.py
# (variant A: +0.0% in all 64 pairs). The mined-schedule strategic controller is
# REJECTED as-is; the package stands as scaffolding for a behavior-cloning
# cadence controller (IMPACT plan Sec.8 Workstream A).
ENABLE_HERD_SCHEDULE = _os.environ.get("CHAL_HERD", "0") == "1"
ENABLE_QUADRANT_GATE = _os.environ.get("CHAL_QUAD", "0") == "1"
ENABLE_HAND_CAP = _os.environ.get("CHAL_HANDS", "0") == "1"


def _placed_counts(me):
    have = {"COW": 0, "SHEEP": 0, "GOOSE": 0}
    for row in me.get("tiles", []):
        for t in row:
            if isinstance(t, dict) and t.get("animal"):
                a = t["animal"]
                sp = a.get("kind") if isinstance(a, dict) else a
                if sp in have:
                    have[sp] += 1
    return have


def max_quadrants_for_day(day):
    for threshold, allowed in _MAX_QUADRANTS_BY_DAY:
        if day >= threshold:
            return allowed
    return 1


def herd_target(obs, me):
    """Species dict the challenger wants placed *now*, per the mined schedule.

    Never below what is already placed (can't un-buy an animal); capped by the
    day schedule, the open-quadrant schedule, and -- like the incumbent -- frozen
    after day 17 (a fresh cow needs ~10 days to break even)."""
    day = int(obs.get("day", 0))
    have = _placed_counts(me)
    placed_total = sum(have.values())
    if day > 17:
        return {k: v for k, v in have.items() if v}

    nq = len(me.get("unlocked_quadrants", []) or [1])
    day_cap = _HERD_BY_DAY[min(day, len(_HERD_BY_DAY) - 1)]
    quad_cap = _HERD_CAP_BY_QUADRANTS.get(nq, 15)
    cap = max(placed_total, min(day_cap, quad_cap))

    out, total = {}, 0
    for species, weight in _HERD_SPLIT:
        if species == "GOOSE" and day < _GOOSE_FIRST_DAY and have["GOOSE"] == 0:
            continue
        want = max(have[species], min(weight, cap - total))
        if want:
            out[species] = want
            total += want
    # Distribute any remaining cap headroom to whichever species is furthest
    # from its weight (keeps the ratio close as the herd fills).
    while total < cap:
        species = min(
            (s for s, _ in _HERD_SPLIT
             if not (s == "GOOSE" and day < _GOOSE_FIRST_DAY and have["GOOSE"] == 0)),
            key=lambda s: out.get(s, 0),
            default=None,
        )
        if species is None:
            break
        out[species] = out.get(species, 0) + 1
        total += 1
    return out


def strategic_intent(obs, me):
    """The knob object consumed by main.py's shared logic (same shape as
    main.strategy_intent), with the replay-derived land/hand ceilings applied.

    mode stays ADAPTIVE_ECONOMY so the incumbent's tuned crop-mix and
    market-cadence branches remain active; only max_quadrants / max_hands differ.
    """
    import main

    base = main.strategy_intent("ADAPTIVE_ECONOMY")
    day = int(obs.get("day", 0))
    if ENABLE_QUADRANT_GATE:
        base["max_quadrants"] = max_quadrants_for_day(day)
    if ENABLE_HAND_CAP:
        base["max_hands"] = _MAX_HANDS
    base["feed_stock_days"] = _FEED_STOCK_DAYS
    return base
