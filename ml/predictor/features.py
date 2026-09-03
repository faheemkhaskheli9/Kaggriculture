"""Shared feature extraction for the opponent-production predictor.

Used by both ``build_dataset.py`` (offline, over replays) and, at inference
time, by ``main.py`` via ``infer.py`` -- so the exact same function must run in
both places. Pure Python, stdlib only.
"""
from __future__ import annotations

PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
            "EGG", "MILK", "WOOL", "FERTILIZER"]
CROPS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"]
ANIMALS = ["GOOSE", "COW", "SHEEP"]

# shop -> demanded products (from main.py SHOPS; UPPER_SNAKE keys)
SHOPS = {
    "BAKERY": ["EGG", "WHEAT"], "PIZZA_SHOP": ["MILK", "TOMATO", "WHEAT"],
    "BRUNCH_SPOT": ["EGG", "WHEAT", "STRAWBERRY"], "YARN_STORE": ["WOOL"],
    "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"], "PET_CAFE": ["CARROT"],
    "SMOOTHIE_SHOP": ["STRAWBERRY", "MILK"],
    "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"],
}

FEATURE_NAMES = (
    ["day", "opp_money", "opp_money_d2",
     "opp_weeds", "opp_empty", "opp_quadrants", "n_shops"]
    + [f"opp_plant_{c}" for c in CROPS]
    + [f"opp_plantage_{c}" for c in CROPS]
    + [f"opp_animal_{a}" for a in ANIMALS]
    + [f"mkt_price_{p}" for p in PRODUCTS]
    + [f"mkt_inv_{p}" for p in PRODUCTS]
    + [f"shop_demand_{p}" for p in PRODUCTS]
)


def extract(opp_farm: dict, market: dict, town: dict, day: int,
            opp_money_2days_ago: float | None) -> dict:
    tiles = opp_farm.get("tiles") or []
    plant = {c: 0 for c in CROPS}
    plantage = {c: 0.0 for c in CROPS}
    animal = {a: 0 for a in ANIMALS}
    weeds = empty = 0
    for row in tiles:
        for t in row:
            if t is None:
                empty += 1
            elif t == "LOCKED":
                pass
            elif isinstance(t, dict):
                k = t.get("kind")
                if k == "PLANT" and t.get("crop") in plant:
                    plant[t["crop"]] += 1
                    plantage[t["crop"]] += max(0, day - t.get("planted_day", day))
                elif k == "WEED":
                    weeds += 1
                elif t.get("animal") in animal:
                    animal[t["animal"]] += 1
    for c in CROPS:
        if plant[c]:
            plantage[c] /= plant[c]

    prices = (market or {}).get("prices") or {}
    inv = (market or {}).get("inventory") or {}
    shops = (town or {}).get("unlocked_shops") or []
    demand = {p: 0 for p in PRODUCTS}
    for s in shops:
        for p in SHOPS.get(s, []):
            demand[p] += 1

    money = float(opp_farm.get("money", 0))
    feat = {
        "day": float(day),
        "opp_money": money,
        "opp_money_d2": money - opp_money_2days_ago if opp_money_2days_ago is not None else 0.0,
        "opp_weeds": float(weeds),
        "opp_empty": float(empty),
        "opp_quadrants": float(len(opp_farm.get("unlocked_quadrants", []))),
        "n_shops": float(len(shops)),
    }
    for c in CROPS:
        feat[f"opp_plant_{c}"] = float(plant[c])
        feat[f"opp_plantage_{c}"] = float(plantage[c])
    for a in ANIMALS:
        feat[f"opp_animal_{a}"] = float(animal[a])
    for p in PRODUCTS:
        feat[f"mkt_price_{p}"] = float(prices.get(p, 0))
        feat[f"mkt_inv_{p}"] = float(inv.get(p, 0))
        feat[f"shop_demand_{p}"] = float(demand[p])
    return feat


def to_row(feat: dict) -> list[float]:
    return [float(feat.get(k, 0.0)) for k in FEATURE_NAMES]
