"""Stable, dependency-free observation encoding for the hybrid policy."""
from __future__ import annotations

import math

CROPS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"]
ANIMALS = ["GOOSE", "COW", "SHEEP"]
PRODUCTS = CROPS + ["EGG", "MILK", "WOOL", "FERTILIZER"]

GLOBAL_NAMES = (
    ["day", "hour_sin", "hour_cos", "my_money", "opp_money", "hands", "opp_hands",
     "quadrants", "opp_quadrants", "shops"]
    + [f"price_{p}" for p in PRODUCTS]
    + [f"market_{p}" for p in PRODUCTS]
    + [f"shed_{p}" for p in PRODUCTS]
    + [f"seed_{c}" for c in CROPS]
    + [f"my_crop_{c}" for c in CROPS]
    + [f"opp_crop_{c}" for c in CROPS]
    + [f"my_animal_{a}" for a in ANIMALS]
    + [f"opp_animal_{a}" for a in ANIMALS]
    + ["my_weeds", "opp_weeds", "my_urgent_plants", "my_hungry_animals"]
)

UNIT_NAMES = ["x", "y", "to_shed", "load"] + [f"carry_{p}" for p in PRODUCTS]


def _farm_counts(farm):
    crops = {c: 0 for c in CROPS}
    animals = {a: 0 for a in ANIMALS}
    weeds = urgent = hungry = 0
    for row in farm.get("tiles", []) or []:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT":
                crop = tile.get("crop")
                if crop in crops:
                    crops[crop] += 1
                if not tile.get("watered_today") and tile.get("consecutive_unwatered", 0) >= 1:
                    urgent += 1
            elif tile.get("kind") == "WEED":
                weeds += 1
            animal = tile.get("animal")
            if animal in animals:
                animals[animal] += 1
                if not tile.get("fed_today") and tile.get("consecutive_unfed", 0) >= 1:
                    hungry += 1
    return crops, animals, weeds, urgent, hungry


def encode_global(obs: dict) -> list[float]:
    player = int(obs.get("player", 0))
    farms = obs.get("farms") or [{}, {}]
    me, opp = farms[player], farms[1 - player]
    private = obs.get("private") or {}
    market = obs.get("market") or {}
    prices, inventory = market.get("prices") or {}, market.get("inventory") or {}
    shed, seeds = private.get("shed") or {}, private.get("seeds") or {}
    mc, ma, mw, mu, mh = _farm_counts(me)
    oc, oa, ow, _, _ = _farm_counts(opp)
    hour = float(obs.get("hour", 0))
    vals = [
        float(obs.get("day", 0)) / 29.0,
        math.sin(2.0 * math.pi * hour / 24.0),
        math.cos(2.0 * math.pi * hour / 24.0),
        min(5.0, float(me.get("money", 0)) / 10000.0),
        min(5.0, float(opp.get("money", 0)) / 10000.0),
        len(me.get("hands", [])) / 16.0,
        len(opp.get("hands", [])) / 16.0,
        len(me.get("unlocked_quadrants", [])) / 4.0,
        len(opp.get("unlocked_quadrants", [])) / 4.0,
        len((obs.get("town") or {}).get("unlocked_shops", [])) / 8.0,
    ]
    vals += [min(5.0, float(prices.get(p, 0)) / 250.0) for p in PRODUCTS]
    vals += [min(5.0, float(inventory.get(p, 10000)) / 10000.0) for p in PRODUCTS]
    vals += [min(5.0, float(shed.get(p, 0)) / 25.0) for p in PRODUCTS]
    vals += [min(5.0, float(seeds.get(c, 0)) / 12.0) for c in CROPS]
    vals += [mc[c] / 100.0 for c in CROPS] + [oc[c] / 100.0 for c in CROPS]
    vals += [ma[a] / 16.0 for a in ANIMALS] + [oa[a] / 16.0 for a in ANIMALS]
    vals += [mw / 100.0, ow / 100.0, mu / 100.0, mh / 16.0]
    assert len(vals) == len(GLOBAL_NAMES)
    return vals


def encode_units(obs: dict) -> list[list[float]]:
    player = int(obs.get("player", 0))
    me = obs["farms"][player]
    positions = [me.get("farmer", [4, 4])] + list(me.get("hands", []))
    inventories = list((obs.get("private") or {}).get("inventories", []))
    out = []
    for i, pos in enumerate(positions):
        inv = inventories[i] if i < len(inventories) else {}
        x, y = float(pos[0]), float(pos[1])
        carried = [max(0.0, float(inv.get(p, 0))) for p in PRODUCTS]
        out.append([x / 9.0, y / 9.0,
                    (abs(x - 4.5) + abs(y - 4.5)) / 9.0,
                    min(5.0, sum(carried) / 25.0)]
                   + [min(5.0, v / 10.0) for v in carried])
    return out


def encode_policy_rows(obs: dict) -> list[list[float]]:
    g = encode_global(obs)
    return [g + unit for unit in encode_units(obs)]

