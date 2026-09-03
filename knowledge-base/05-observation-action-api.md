# 05 — Observation & action API

## The observation passed to `agent(obs)`

```py
{
  "player": int,            # 0 or 1 — your index
  "step":   int,            # framework-supplied turn counter; MAY be absent — see below
  "day":    int,            # 0-indexed in-game day (0..29)
  "hour":   int,            # 0-indexed turn within the day (0..23)
  "farms":  [farm, farm],   # BOTH players' public state, indexed by player id (shared)
  "market": {               # shared
    "inventory": { "WHEAT": int, ... },   # current market supply per product
    "prices":    { "WHEAT": int, ... },   # current sell price per product (rounded, floor 1)
  },
  "town": {                 # shared
    "unlocked_shops": ["BAKERY", "PIZZA_SHOP", ...],  # UPPER_SNAKE; may repeat
  },
  "private": {              # THIS player only; opponent's private state is hidden
    "shed":        { "WHEAT": int, "GOOSE": int, "FERTILIZER": int, ... },
    "seeds":       { "WHEAT": int, ... },
    "inventories": [farmer_inv, hand1_inv, ...],  # [0] = main farmer, then hands in order
  },
}
```

### `farm` dict (public — both are visible)

```py
{
  "money":              float,
  "tiles":              [[tile, ...], ...],   # tiles[y][x];  x = column, y = row, y grows DOWN
  "farmer":             [x, y],
  "hands":              [[x, y], ...],        # this day's hired hands
  "unlocked_quadrants": ["NW", ...],          # subset of NW/NE/SW/SE
  "hires_today":        int,                  # prices the NEXT HIRE: cost = fib(hires_today)
}
```

### `tile` is one of

- `None` — empty, unlocked.
- `"LOCKED"` — quadrant not bought. Passable, but every tile op no-ops here.
- **plant dict:**
  ```py
  {"kind": "PLANT",
   "crop": "WHEAT"|"CARROT"|"TOMATO"|"STRAWBERRY"|"MELON",
   "planted_day": int,
   "watered_today": bool,              # reset False each end-of-day
   "consecutive_unwatered": int,       # 2+ at end-of-day -> WEED;  fresh plant starts at 1
   "yield_units": int,                 # currently harvestable
   "max_lifespan_step": int,           # step decay begins; -1 for ongoing crops
   "fertilized_until_day": int}        # last day the fert bonus applies; -1 if none
  ```
- **weed dict:** `{"kind": "WEED"}`
- **structure dict** (coop/pasture, maybe occupied):
  ```py
  {"kind": "COOP"|"PASTURE",
   "animal": "GOOSE"|"COW"|"SHEEP",   # key ABSENT until an animal is PLACEd
   "placed_day": int,
   "yield_units": int,                # unharvested product on the tile (cap = max_held)
   "fed_today": bool,
   "consecutive_unfed": int,          # 2+ at end-of-day -> animal escapes (permanent)
   "cared_today": bool,
   "fertilizer_available": bool,      # set True each end-of-day; cleared by COLLECT_FERTILIZER
   "pending_care_bonus": int}         # banked CARE bonus, paid on the next fed production tick
  ```
  A freshly `BUILD`'d structure is just `{"kind": "COOP"/"PASTURE"}` — no other
  keys. Check `"animal" in tile`, not `tile.get("animal")` alone (both work, but
  the key is genuinely absent when empty).

## The action dict you return

```py
{
  "farmer": [op, *args],           # exactly one op for the main farmer
  "hands":  [[op, *args], ...],    # one op per hired hand, in hands order
  "market": [[op, *args], ...],    # ordered; only the first 10 are processed
}
```

### Farmer / hand ops
`NORTH` `SOUTH` `EAST` `WEST` `PASS`
`PICKUP <item> [n]` · `DROP` · `PLACE <item> [n]`
`PLANT <crop>` · `WATER` · `HARVEST` · `FERTILIZE`
`BUILD_COOP` · `BUILD_PASTURE` · `FEED` · `CARE` · `COLLECT_FERTILIZER` · `DIG`

### Market ops
`["BUY_SEED", crop, n]` · `["BUY_PRODUCT", "WHEAT"|"FERTILIZER", n]` ·
`["BUY_ANIMAL", animal, n]` · `["SELL", item, n]` · `["HIRE"]` · `["BUY_LAND"]`

Invalid / illegal ops are **silent no-ops** (the turn is spent, nothing else
happens).

## Traps and conventions

- **`obs["step"]` may not be present.** The env interpreter reads it, and the
  quick-start example uses `obs.get("step", 0)`, but a prior debugging note found
  it absent in the agent-facing observation. **Use `day` and `hour`**; derive
  `step = day*24 + hour` only if you truly need a global counter.
- **Shop names are `UPPER_SNAKE`** (`PIZZA_SHOP`, `FARMERS_MARKET`, `PET_CAFE`,
  `BRUNCH_SPOT`, `YARN_STORE`, `ICE_CREAM_SHOP`, `SMOOTHIE_SHOP`, `BAKERY`).
  Normalise before lookup: `str(s).strip().upper().replace(" ", "_").replace("-", "_")`.
  A title-case demand table silently returns zero for every shop — this was the
  `main_600.py` bug.
- `unlocked_shops` **can list the same shop multiple times** (drawn with
  replacement). Count each entry independently for demand.
- **`tiles[y][x]`**, not `[x][y]`. `farmer` and `hands` are `[x, y]`. y grows
  downward (`NORTH` = y−1).
- **Atomic PLANT:** if your units' total `PLANT <crop>` requests this turn exceed
  `seeds[crop]`, *all* of them become PASS. Never emit more PLANT ops for a crop
  than you hold seeds for.
- **10-order market cap.** Order the list so time-critical items come first:
  dawn `HIRE`s → highest-value `SELL`s → `BUY_LAND`/`BUY_ANIMAL`/feed `BUY_PRODUCT`
  → `BUY_SEED` → remaining sells. Slots 11+ are dropped silently.
- **Money is shared across the whole market list.** A queued buy can silently
  fail if an earlier order in the same turn spent the cash — keep a shadow
  budget when assembling orders.
- **Only shed items sell.** Field/unit inventory must be `DROP`'d first (end-of-
  day auto-drop handles this on days 0–28; day 29 you must do it explicitly).
- **`hires_today`** on the farm dict tells you the cost of your *next* `HIRE`
  (`fib(hires_today)`), and also lets you see how aggressively the opponent
  hired.
- Opponent's `farm` (tiles, money, farmer, hands, quadrants) is **fully
  visible** — use it to estimate their upcoming supply per product. Their
  `private` (shed, seeds, inventories) is **not**.
