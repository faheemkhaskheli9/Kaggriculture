# 04 — Engine internals (authoritative)

Transcribed from `kaggle_environments/envs/kaggriculture/kaggriculture.py`
(installed package; ~1090 lines). When prose anywhere disagrees with this file,
this file wins — and when this file disagrees with the installed source, re-read
the source and fix this file.

---

## Constants

```
MARKET_I0   = 10000        PRICE_FLOOR = 1        HINGE_GAIN = 8.0
LAND_ORDER  = ["NE", "SW", "SE"]      LAND_PRICES = [1000, 2000, 4000]
FARM_HAND_COST_MULT = 1              MAX_SHOP_INSTANCES = 8
PRODUCTS = [WHEAT, CARROT, TOMATO, STRAWBERRY, MELON, EGG, MILK, WOOL, FERTILIZER]
TOWN_CENTER_PRODUCTS = PRODUCTS without FERTILIZER
```

`CROPS[c]` = `{seed, first_yield_day, max_yield_day, interval, max_yield, ongoing}`

| crop | seed | first_yield_day | max_yield_day | interval | max_yield | ongoing |
|---|---|---|---|---|---|---|
| WHEAT | 10 | 2 | 4 | 0 | 6 | False |
| CARROT | 20 | 2 | 3 | 0 | 4 | False |
| TOMATO | 50 | 8 | 8 | 1 | 4 | True |
| STRAWBERRY | 100 | 10 | 10 | 2 | 4 | True |
| MELON | 80 | 10 | 12 | 0 | 6 | False |

`ANIMALS[a]` = `{cost, structure, first_yield_day, interval, max_held, product}`

| animal | cost | structure | first_yield_day | interval | max_held | product |
|---|---|---|---|---|---|---|
| GOOSE | 300 | COOP | 4 | 1 | 4 | EGG |
| COW | 400 | PASTURE | 8 | 2 | 6 | MILK |
| SHEEP | 500 | PASTURE | 6 | 3 | 6 | WOOL |

---

## Per-step sequence — `interpreter(state, env)`

```
step = obs.step              # framework counter; day = step // 24
if no farms:  _initialize();  return
if env.done:  return

for each agent:
    parse action.farmer (default ["PASS"]) and action.hands (list)
    ATOMIC PLANT CHECK: sum PLANT<crop> requests over farmer+hands;
        if count > private.seeds[crop]  ->  every PLANT<crop> this turn -> ["PASS"]
    _apply_unit_action(farm, private, idx=0, farmer_action, ...)
    for h_idx, hand_action:  _apply_unit_action(farm, private, h_idx+1, hand_action, ...)

_process_market(state, env)          # both queues, slot by slot
_town_consume(env, state, step)      # shops if step%4==0; center if step%24==0
for farm: _decay_plants(farm, step)  # EVERY step, not just end-of-day
if (step + 1) % 24 == 0:  _end_of_day(state, env, day)

next_step = step + 1;  obs.day = next_step // 24;  obs.hour = next_step % 24
if step >= episodeSteps - 2:          # step 718 for the default 720
    every agent: status = DONE;  reward = float(farm["money"])
```

### Key timing consequences

- **Reward locks at step 718 = day 29, hour 22.** Before the increment, step 718
  is day 29 hour 22 (the last actionable turn is hour 22, not 23).
- `(718 + 1) % 24 = 23 ≠ 0`, so **`_end_of_day` for day 29 never runs.** There
  are 29 end-of-day refreshes (transitions day 0→1 … 28→29), none for day 29.
- Therefore on day 29: **no ongoing-crop tick, no animal production tick, no CARE
  payout, no weed spawn, and no auto-drop of unit inventories to the shed.**
- Only shed items can be `SELL`'d, and reward is money only. So the endgame is:
  get produce into the shed via explicit `DROP` and `SELL` it to $0 **before
  step 718**. Anything still on a unit or unsold in the shed at 718 = $0.
- `_decay_plants` runs **every step**, so a plant past `max_lifespan_step` loses
  `yield_units` mid-day, not just overnight.

---

## `_apply_unit_action` — one unit's op (invalid = silent no-op)

Order of checks:
1. `op` in `{NORTH,SOUTH,EAST,WEST}` → move if in-bounds (locked tiles allowed);
   return.
2. `op == "PASS"` → return.
3. `DROP` / `PICKUP` / `PLACE` — resolved **before** the LOCKED guard (they only
   need a standing position):
   - `DROP`: if shed-adjacent, move the unit's whole inventory to shed, item by
     item, each capped by `shed_capacity - sum(shed.values())`; overflow
     discarded.
   - `PICKUP <item> [n=1]`: if shed-adjacent and `n>0`, move
     `min(n, shed[item])` from shed to inventory. Seeds are not in the shed.
   - `PLACE <item> [n=1]`:
     - **animal placement** if `item in ANIMALS` and the current tile is a dict
       with `kind == ANIMALS[item].structure` and no `"animal"` key → consume 1
       from inventory, `tile = _new_animal(item, day)`.
     - else if shed-adjacent → shed drop of `min(n, inv[item], room)`.
4. **LOCKED guard:** if `tile == "LOCKED"`, everything below returns immediately.
5. `PLANT <crop>`: needs `crop in CROPS`, `tile is None`, `seeds[crop] > 0` →
   `seeds[crop] -= 1`, `tile = _new_plant(crop, day, 24)`.
6. `WATER`: tile must be a `PLANT`, not already `watered_today` →
   `watered_today = True`; **if not ongoing** and
   `(max_yield_day+1)//2 <= age <= max_yield_day` →
   `yield_units = min(max_yield, yield_units + (2 if fertilized_until_day >= day else 1))`.
7. `HARVEST`: tile is a dict with `yield_units > 0`.
   - PLANT: if `age < first_yield_day` → return (with a WARNING print for ongoing
     crops — "should never happen"). Else add `yield_units` of the crop to
     inventory, set `yield_units = 0`; if **not ongoing** → `tile = None`.
   - animal: add `yield_units` of `product` to inventory, `yield_units = 0`;
     tile stays.
8. `FERTILIZE`: tile is a PLANT; consume 1 `FERTILIZER` from inventory;
   `fertilized_until_day = max(current, day + 2)` (active day, day+1, day+2).
9. `DIG`: tile not `None`; **not** a placed animal → `tile = None`. Removes
   plant, weed, or empty structure.
10. `BUILD_COOP` / `BUILD_PASTURE`: `tile is None` → set the structure dict
    (`{"kind": "COOP"/"PASTURE"}`, no other fields yet).
11. `FEED`: tile has `"animal"`, not `fed_today`, consume 1 `WHEAT` from
    inventory → `fed_today = True`.
12. `COLLECT_FERTILIZER`: tile has `"animal"`, `fertilizer_available` is True →
    set it False, `inv += 1 FERTILIZER`.
13. `CARE`: tile has `"animal"`, not `cared_today` → `cared_today = True`.

`_new_plant(crop, day, 24)`:
```
kind="PLANT", crop, planted_day=day, watered_today=False,
consecutive_unwatered=1,                       # planting day counts as missed
yield_units = 0 if ongoing else 1,
max_lifespan_step = -1 if ongoing else (day + max_yield_day + 1) * 24,
fertilized_until_day = -1
```

`_new_animal(animal, day)`:
```
kind=structure, animal, placed_day=day, yield_units=0, consecutive_unfed=0,
fed_today=False, cared_today=False, fertilizer_available=False, pending_care_bonus=0
```

---

## `_process_market`

- `queues[p] = action["market"][:max_orders]` (10).
- For each order-slot `i` up to the longest queue:
  - Parse both players' slot-`i` order.
  - `HIRE` → `_do_hire`; `BUY_LAND` → `_do_buy_land`; each handled once, in
    player order, then cleared.
  - Per-unit lockstep `while True` (100k safety break):
    - For each player with an order still `remaining > 0`, quote its current unit:
      - `SELL item` (item in PRODUCTS): `market_price(item, inventory[item])`.
      - `BUY_PRODUCT item` (WHEAT/FERTILIZER): `market_price(item, inventory[item] - 1)`.
      - `BUY_SEED item` (item in CROPS): `CROPS[item].seed`.
      - `BUY_ANIMAL item` (item in ANIMALS): `ANIMALS[item].cost`.
      - anything else → order aborted (`None`).
    - Both quotes use the **same pre-commit inventory**.
    - `_commit_unit` each; on success `remaining -= 1`; on failure the order is
      aborted.
    - Break when nothing quoted or nothing committed.
  - `_refresh_prices(market)` after the slot.

`_commit_unit`:
- `SELL`: need `shed[item] > 0` → `shed[item] -= 1`, `money += price`,
  **`inventory[item] += 1` only if `price > 1`**.
- `BUY_PRODUCT`: need `money >= price` and `sum(shed.values()) < capacity` →
  `money -= price`, `shed[item] += 1`, `inventory[item] -= 1`.
- `BUY_SEED`: need `money >= price` → `money -= price`, `seeds[item] += 1`.
- `BUY_ANIMAL`: need `money >= price` and shed not full → `money -= price`,
  `shed[item] += 1`.

`_do_hire`: `cost = mult * fib(hires_today)` where `fib(0)=1, fib(1)=1, fib(2)=2,
fib(3)=3, fib(4)=5, …`. If `money >= cost` → `money -= cost`, `hires_today += 1`,
append `_spawn_hand(...)` to `hands` and `{}` to `inventories`.

`_spawn_hand`: least-occupied of the 4 shed-access tiles, tie-break by NWSE
order. With the farmer on (4,4), the first hire of the day → **(5,4)**.

`_do_buy_land`: `n = len(unlocked_quadrants) - 1` (0/1/2); if `n < 3` and
`money >= LAND_PRICES[n]` → pay, append `LAND_ORDER[n]`, flip that quadrant's
`"LOCKED"` tiles to `None`.

---

## `_town_consume(env, state, step)`

- `if step % townShopSellInterval (4) == 0`: for each entry in
  `town.unlocked_shops` (duplicates count), `multiplier = 2 if len(products)==1
  else 1`, `inventory[item] -= multiplier` for each demanded item.
- `if step % townCenterSellInterval (24) == 0`: `inventory[item] -= 1` for each
  `TOWN_CENTER_PRODUCTS` (all but FERTILIZER).
- `_refresh_prices`. Inventory can go arbitrarily low; price just floors at $1.

---

## `_decay_plants(farm, step)` — every step

For each PLANT tile with `max_lifespan_step >= 0` and `step >= max_lifespan_step`
and `(step - max_lifespan_step) % 2 == 0`: `yield_units -= 1`; if `<= 0` →
`tile = {"kind": "WEED"}`.

---

## `_end_of_day(state, env, day)` — only when `(step+1) % 24 == 0`

Per farm, in this order:

### `_daily_refresh_plants(farm, day, 24)` — `next_day = day + 1`
For each PLANT:
- `was_watered = watered_today`; `consecutive_unwatered = 0 if was_watered else +1`;
  `watered_today = False`.
- if `consecutive_unwatered >= 2` → `tile = {"kind":"WEED"}`; continue.
- if not ongoing → continue.
- `days_since_first = next_day - planted_day - first_yield_day`; if `< 0` continue.
- if `days_since_first % interval != 0` → continue.
- `production_count = days_since_first // interval + 1`; if `> max_yield` continue.
- `fertilized = was_watered and fertilized_until_day >= day`.
- `yield_units = min(max_yield, yield_units + (2 if fertilized else 1))`.
- if `production_count == max_yield` → `max_lifespan_step = (next_day + 1) * 24`
  (decay starts the day after the last tick).

TOMATO (first 8, interval 1): ticks at ages 8, 9, 10, 11.
STRAWBERRY (first 10, interval 2): ticks at ages 10, 12, 14, 16.

### `_daily_refresh_animals(farm, day)` — `next_day = day + 1`
For each animal tile:
- `consecutive_unfed = 0 if fed_today else +1`; if `>= 2` →
  `tile = {"kind": structure}` (animal escapes, structure stays); continue.
- `days_since_first = next_day - placed_day - first_yield_day`.
- if `days_since_first >= 0 and days_since_first % interval == 0`:
  `base = 1`; `bonus = pending_care_bonus if fed_today else 0`;
  `yield_units = min(max_held, yield_units + base + bonus)`;
  `pending_care_bonus = 0`.
- if `cared_today and fed_today` → `pending_care_bonus += 1`.
- `fertilizer_available = True` (always, every surviving animal).
- `fed_today = False`; `cared_today = False`.

Note the care-bonus subtlety: production tick and the "bank +1" both happen in
the same refresh; a fed+cared animal on a production day pays out the *previous*
bank and then banks +1 for next time.

### then, per farm
- `_spawn_weeds`: each `None` tile → WEED with prob `weedSpawnChance = 0.005`
  (RNG seeded from `env.info["seed"] * 1_000_003 ^ day`, so replays reproduce).
- `_drop_inventories_to_shed`: every unit inventory emptied into the shed up to
  capacity 100; overflow discarded. Seeds untouched.
- `farm["farmer"] = (4,4)`; `farm["hands"] = []`; `hires_today = 0`;
  `private["inventories"] = [{}]`.

### then, once
- `next_day = day + 1`; if `next_day > 0 and next_day % townShopUnlockInterval
  (3) == 0` and `len(unlocked_shops) < 8` → append
  `rng.choice(sorted(SHOPS))`. Fires at next_day = 3, 6, 9, 12, 15, 18, 21, 24 →
  **8 unlocks, at the end of days 2, 5, 8, 11, 14, 17, 20, 23.**
  `sorted(SHOPS)` = BAKERY, BRUNCH_SPOT, FARMERS_MARKET, ICE_CREAM_SHOP,
  PET_CAFE, PIZZA_SHOP, SMOOTHIE_SHOP, YARN_STORE — uniform, with replacement.

---

## `market_price(item, inventory, params)`

```
p = MARKET_PARAMS[item]
if inventory < I0:
    amp = below_target * base / _shape(below_func, T, T)
    price = base + amp * _shape(below_func, I0 - inventory, T)
else:
    amp = above_target * base / _shape(above_func, T, T)
    price = base - amp * _shape(above_func, inventory - I0, T)
return max(1, round(price))
```

`_shape(func, x, T)` with `x = max(0, x)`:
`linear→x`, `sq→x²`, `sqrt→√x`, `log→ln(1+x)`, `log10→log10(1+x)`,
`hinge→ u + 8·max(0, u−1)²` where `u = x/T` (degrades to linear if `T<=0`).

---

## Built-in opponents (`agents` dict)

- `"pass"` — always PASS, empty market.
- `"random"` — random unit ops, occasional random seed buy / plant.
- `"starter"` — **carrot loop**: buy 1 carrot seed when out, plant on the current
  tile, water, harvest at `age >= max_yield_day (3)`, sell all shed carrot.
  Single unit, never moves, never hires, never expands. A weak baseline —
  beating it decisively means little for ladder standing.

---

## Gotchas checklist

- Fresh plant `consecutive_unwatered = 1` → **water it the day you plant it.**
- `HARVEST` before `first_yield_day` is a no-op (and prints a warning for ongoing
  crops).
- One-time-crop watering **adds yield at WATER time**, in-window only; ongoing
  crops gain nothing from extra watering beyond survival + the fertilized tick.
- Atomic PLANT: two units both planting the same crop with only 1 seed →
  **neither** plants.
- `BUY_PRODUCT` only WHEAT / FERTILIZER. Everything can be `SELL`'d.
- Market lines cap at 10/turn; no quantity cap per line. Selling walks its own
  price down.
- Shed cap 100 applies to `BUY_PRODUCT`/`BUY_ANIMAL` too — a full shed silently
  fails those buys.
- Day-29 has no end-of-day: no tick, no auto-drop. Liquidate by hand.
- `reward` is money only; ties possible; rating cares only about the sign.
