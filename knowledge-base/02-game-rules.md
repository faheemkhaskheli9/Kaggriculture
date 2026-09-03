# 02 — Game rules (complete)

Everything a player needs. Exact engine formulas and edge cases are in
`04-engine-internals.md`; market curve detail is in `03-market-and-economy.md`.

---

## 1. Board, quadrants, land

- Each player has a private `boardSize × boardSize` grid, default **10×10**,
  split into four **5×5 quadrants**: `NW`, `NE`, `SW`, `SE`. `tiles[y][x]`,
  x = column, y = row, **y grows downward**.
- Only **NW** starts unlocked (25 tiles). `BUY_LAND` unlocks the rest **in a
  fixed order — NE, then SW, then SE** — for **$1000, $2000, $4000**.
- A tile is one of: `None` (empty, unlocked), `"LOCKED"` (unbought quadrant),
  a plant dict, a weed dict `{"kind":"WEED"}`, or a structure dict
  (`COOP`/`PASTURE`, optionally holding an animal).
- **Locked tiles are passable.** Units may walk onto/through locked quadrants,
  but every tile op (`PLANT`, `WATER`, `BUILD_*`, `DIG`, `HARVEST`, …) is a
  no-op on a locked tile. Exception: shed ops (`PICKUP`, `DROP`, `PLACE`-to-shed)
  work from a locked shed-access tile because they only use it as a standing
  position.
- **Weeds** spawn on any empty unlocked tile at end-of-day with probability
  `weedSpawnChance = 0.005` per tile. A weed blocks the tile until cleared with
  `DIG`.

## 2. The shed (inventory)

- Sits at the board centre. **Not a tile** — never appears in `tiles`.
- "Shed-adjacent" = standing on one of the four centre tiles: for `half = 5`
  those are **(4,4), (5,4), (4,5), (5,5)** — one per quadrant. Three of them
  start locked, but the shed is reachable from all four regardless.
- Holds harvested produce, bought products, animals-in-transit, and fertilizer.
  **Capacity 100 non-seed items.** Overflow on any deposit (mid-day `PLACE`,
  end-of-day auto-drop, `BUY_PRODUCT`, `BUY_ANIMAL`) is **discarded** — you
  cannot stockpile on unit inventories to dodge the cap.
- **Seeds** live in a separate `private["seeds"]` slot with no cap. They are
  **never** picked up; `PLANT` consumes them directly.
- Only items **in the shed** can be `SELL`'d. Produce sitting in a unit's
  field inventory is not market-accessible.

## 3. Farmer and farm hands

- One **main farmer** per player, permanent. Plus **hired hands** for the
  current day only.
- All units start each day at the shed: farmer at **(4,4)**; the day's first
  hand at **(5,4)** (least-occupied shed tile, NWSE tie-break), etc. Spawn
  ignores locked status.
- Units may share a tile. Each unit takes **exactly one op per turn**.
- **Hiring** is a market order (`HIRE`). Cost of the *n*-th hire of the day is
  `farmHandCostMult · fib(n)` with `fib` = 1, 1, 2, 3, 5, 8, 13, 21, 34, …
  (`fib(0)=1`). Default mult = 1. Resets to 0 each day. Rough running totals:
  6 hands ≈ $20, 10 hands ≈ $143, 12 hands ≈ $376, 13 ≈ $609, 14 ≈ $986.
  There is **no hard cap** — the practical ceiling is the 10-orders/turn limit
  (split hires across hours 0–1) and the fib cost curve (~13–14 is the knee).
- At end of day every hand drops its inventory into the shed and **disappears**;
  re-hire next day.

## 4. Farmer / hand operations

One per unit per turn.

### Movement
`NORTH` `SOUTH` `EAST` `WEST` — one cell (N = y−1). Off-board = no-op.
`PASS` — do nothing.

### Shed
- `PICKUP <item> [n]` — move up to `n` (default 1) of `<item>` from shed to the
  acting unit's inventory. Must be shed-adjacent.
- `DROP` — shed-adjacent: dump the unit's **entire** inventory into the shed
  (overflow discarded). No-op otherwise.
- `PLACE <item> [n]` — dual purpose:
  - **Animal placement:** standing on a matching **empty** structure
    (`GOOSE` on `COOP`; `COW`/`SHEEP` on `PASTURE`), moves one animal from
    inventory onto the tile. `n` ignored.
  - **Shed drop:** shed-adjacent, moves up to `n` of `<item>` into the shed
    (obeys capacity).

### Plants
- `PLANT <crop>` — plant a seed on the current empty unlocked tile. Consumes one
  seed from `private["seeds"]`. **Atomic rule:** if the total `PLANT <crop>`
  requests from all your units this turn exceed your seed count for that crop,
  **all of them** are dropped to PASS.
- `WATER` — water the plant here. Once/day; repeats are no-ops. For one-time
  crops inside the yield window it also **immediately adds yield** (see §6).
- `HARVEST` — collect produce into inventory. One-time crop → tile becomes
  `None`. Ongoing crop / animal → tile stays. No-op if `yield_units == 0` or
  (crop) age < `first_yield_day`.
- `FERTILIZE` — consumes 1 `FERTILIZER` from the acting unit's inventory.
  Sets the fertilizer bonus active for **today, +1, +2** (3 days). Bonus only
  pays out on days the plant is also watered.

### Animals / terrain
- `BUILD_COOP` / `BUILD_PASTURE` — turn the current empty tile into that
  structure.
- `FEED` — feed the animal here; consumes 1 `WHEAT` from the acting unit's
  inventory. Once/day.
- `CARE` — care for the animal here. Once/day. Banks a yield bonus (see §7).
- `COLLECT_FERTILIZER` — take the 1 fertilizer this animal made at end of last
  day. Does **not** accumulate — an animal left 5 days still only has 1 to give.
- `DIG` — remove a plant, a weed, or an **empty** coop/pasture from the current
  tile (no produce). A structure with an animal on it **cannot** be dug.

## 5. Market operations

Ordered list, **≤ 10 processed/turn**, extras dropped. Both players' lists are
processed together, order-slot by order-slot, one unit at a time (see
`03` / `04`).

- `["BUY_SEED", crop, n]` — fixed price = seed cost. Unlimited supply.
- `["BUY_ANIMAL", animal, n]` — fixed price = animal cost. Lands in shed.
- `["BUY_PRODUCT", item, n]` — **only `WHEAT` or `FERTILIZER`.** Priced at
  post-buy inventory. Lands in shed. Stops if you run out of money mid-order.
- `["SELL", item, n]` — sell from the **shed**. Any product (incl. fertilizer).
  Priced at pre-sell inventory, re-quoted per unit as inventory moves.
- `["HIRE"]` — hire one hand (see §3).
- `["BUY_LAND"]` — unlock the next quadrant (§1).

## 6. Watering, decay, and one-time-crop yield

- **Every plant must be watered every day.** `consecutive_unwatered` starts at
  **1 for a fresh plant** (planting day counts as missed) → a seed not watered
  on its planting day weeds that night. An established plant (watered yesterday,
  counter 0) can miss exactly one day. **2 consecutive missed days → WEED.**
- **One-time crops** (WHEAT, CARROT, MELON): a `WATER` on an age in
  `[ceil(maxYieldDay/2), maxYieldDay]` immediately adds **+1** to
  `yield_units` (**+2** if fertilized that day), capped at `max_yield`.
  Windows: WHEAT ages **2–4**, CARROT ages **2–3**, MELON ages **6–12**.
  Base `yield_units` is 1 at plant time, so an unwatered wheat still harvests 1.
- **Decay:** a one-time crop's `max_lifespan_step` is
  `(planted_day + maxYieldDay + 1) · 24` — decay begins the day after the max
  window. From then, `yield_units` drops by 1 **every 2 turns**; at 0 the tile
  becomes a WEED.

## 7. Ongoing crops and animals

### Ongoing crops (TOMATO, STRAWBERRY)
- Produce on a fixed schedule, not by watering. Base **+1** per scheduled tick,
  **+2** if the plant is **both fertilized and watered** that day. Cap 4 held.
- Schedule (age = day − planted_day): **TOMATO** ticks at ages 8, 9, 10, 11
  (interval 1). **STRAWBERRY** at ages 10, 12, 14, 16 (interval 2).
- Exactly **4 scheduled ticks per plant lifetime.** One day after the 4th tick,
  the plant starts decaying (−1 yield every 2 turns) and eventually weeds.
- Still needs daily watering for survival like any plant.

### Animals (GOOSE / COW / SHEEP)
- Need a built structure, then `PLACE`. `first_yield_day` counts from
  `placed_day`. Then produce **+1** product every `interval` days
  **indefinitely**, capped at `max_held` unharvested on the tile.
- **Production does not require feeding.** Feeding (1 wheat/day) does two things:
  1. Survival — `consecutive_unfed` starts at 0 (survives day 1 unfed);
     **2 consecutive unfed days → the animal escapes permanently** (structure
     stays, empty).
  2. `CARE` bonus — on a day the animal is **fed AND cared for**,
     `pending_care_bonus += 1`. On the next scheduled production day, **if fed**,
     the whole banked bonus is added on top of the base +1 (capped at
     `max_held`) and the bank resets. If unfed on the production day, base +1
     still happens but the bonus is lost.
- **Every surviving animal makes 1 `FERTILIZER` available at end of each day**,
  fed or not, cared or not. `COLLECT_FERTILIZER` grabs it; it does not stack.

## 8. Town demand

- **Town center:** consumes 1 of **every non-fertilizer product** every
  `townCenterSellInterval = 24` turns → once/day, flat all season (30 total per
  product).
- **Shops:** unlock one at a time at the end of days 2, 5, 8, …, 23 →
  **8 instances total** (`MAX_SHOP_INSTANCES`), drawn **uniformly at random with
  replacement** from the 8 shop types, so duplicates happen (three bakeries and
  no yarn store is possible). Once unlocked, permanent.
- Each shop **instance** consumes one of every product on its demand list every
  `townShopSellInterval = 4` turns → **6×/day**. A **single-product** shop
  consumes **2×** (so a yarn store removes 24 wool/day; a pet cafe 24 carrot/day).

| Shop | Demands |
|---|---|
| BAKERY | EGG, WHEAT |
| PIZZA_SHOP | MILK, TOMATO, WHEAT |
| BRUNCH_SPOT | EGG, WHEAT, STRAWBERRY |
| YARN_STORE | WOOL (2×) |
| ICE_CREAM_SHOP | STRAWBERRY, MILK, WHEAT |
| PET_CAFE | CARROT (2×) |
| SMOOTHIE_SHOP | STRAWBERRY, MILK |
| FARMERS_MARKET | WHEAT, CARROT, TOMATO, STRAWBERRY |

Total town demand grows monotonically and, in practice, **exceeds what one farm
produces** for most products — so prices drift up all season unless a player
gluts a line.

## 9. Turn processing order

Per step, the engine does:

1. **Validate + apply unit actions** — farmer then each hand, in order, for both
   players "simultaneously" (state is read then written). Atomic-PLANT check.
2. **Process the market queues** — slot by slot; `HIRE`/`BUY_LAND` first
   (player order), then `SELL`/`BUY_*` one unit at a time in lockstep across
   both players; prices refresh after each slot.
3. **Town consumption** — shops (if `step % 4 == 0`), town center
   (if `step % 24 == 0`); prices refresh.
4. **Decay pass** — `yield_units` decrement on plants past `max_lifespan_step`.
5. **End of day** (only when `(step+1) % 24 == 0`): daily plant refresh
   (watering counters, ongoing-crop ticks), daily animal refresh (feed counters,
   production ticks, care bonus, fertilizer flag), weed spawn, **auto-drop all
   unit inventories to the shed**, reset units to the shed, clear hands, then
   maybe unlock a shop.
6. Advance `day`/`hour`. If `step >= episodeSteps - 2` (i.e. **step 718**), mark
   every agent `DONE` and set `reward = farm["money"]`.

## 10. Win condition & reward

Most coins at the end wins; ties possible. `reward = farm["money"]` at step 718.
**Inventory — in the shed or on a unit — is worth $0.** The day-29 end-of-day
never runs (see `04`), so anything not *sold* by step 718 is lost.

## 11. Configuration defaults

| Param | Default | Meaning |
|---|---|---|
| `episodeSteps` | 720 | total turns |
| `boardSize` | 10 | grid W/H (four 5×5 quadrants) |
| `startingMoney` | 3000 | starting coins |
| `maxMarketOrdersPerTurn` | 10 | market orders processed/player/turn |
| `turnsPerDay` | 24 | |
| `shedCapacity` | 100 | non-seed shed items |
| `weedSpawnChance` | 0.005 | per empty tile, end-of-day |
| `townShopUnlockInterval` | 3 | days between shop unlocks (cap 8) |
| `townShopSellInterval` | 4 | turns between shop consumption ticks |
| `townCenterSellInterval` | 24 | turns between town-center ticks |
| `farmHandCostMult` | 1 | hire cost multiplier |
| `seed` | null | deterministic episode seed (stripped from obs) |
| `marketParams` | – | sparse per-resource price-curve overrides |

Seed costs and base prices are **not** configurable.
