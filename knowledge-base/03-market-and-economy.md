# 03 — Market and economy

## The price function

For each product the sell price is a function of the market's current
**inventory** for that product:

```
price(inv) = base + sign · amp · f(|inv − I0|)
  sign = +1   if inv < I0     (scarcity → price above base)
  sign = −1   if inv > I0      (glut     → price below base)
  amp  = target · base / f(T)  (derived, per side)
  f ∈ { linear, sq, sqrt, log, log10, hinge }   (log = ln(1+x), so f(0)=0)
price is floored at $1 and rounded to the nearest dollar.
```

- **`I0 = 10000`** for every product — the shared starting inventory. Price = `base`
  there.
- **`T`** = the production capacity of one 5×5 field over a **24-day** window at
  optimal watering, no fertilizer (animal `T` pre-discounted 30% for feed
  overhead). It is the natural "one field's output" unit of throughput.
- **`target`** means: *moving `T` units past `I0` shifts the price by
  `target × base`.* Each side of `I0` has its **own** shape `f` and `target`, so
  a product can be, e.g., panicky on scarcity and calm on glut.
- **`hinge`**: with `u = x/T`, `f = u + 8·max(0, u−1)²`. Linear in `u` below `T`,
  quadratic runaway above `T`. Used on the **scarcity side** of CARROT, TOMATO,
  EGG — price stays near `base` under ordinary demand, then spikes hard once
  demand runs past one field's worth. `f(T)=1` so `target` keeps its meaning.
- `sq` on the **glut side** (MELON, WOOL) → even a modest oversupply craters the
  price. `linear` glut side with `target > 1` (STRAWBERRY, MILK) → same effect,
  slightly gentler. `log` glut side (WHEAT, EGG) → oversupply barely moves the
  price.

### Per-resource parameters (`MARKET_PARAMS`)

| Resource | base | T | below f / target | above f / target | P(I0−T) | P(I0+T) | P(I0+2T) |
|---|---|---|---|---|---|---|---|
| WHEAT | 25 | 400 | sqrt / 0.80 | log / 0.20 | $45 | $20 | $19 |
| CARROT | 35 | 450 | **hinge** / 1.00 | sqrt / 0.70 | $70 | $10 | $1 |
| TOMATO | 60 | 200 | **hinge** / 0.40 | sqrt / 0.60 | $84 | $24 | $9 |
| STRAWBERRY | 120 | 100 | sqrt / 0.70 | linear / 1.60 | $204 | $1 | $1 |
| MELON | 250 | 300 | log / 0.20 | **sq** / 3.60 | $300 | $1 | $1 |
| EGG | 50 | 332 | **hinge** / 0.40 | log / 0.20 | $70 | $40 | $39 |
| MILK | 160 | 122 | sqrt / 0.60 | linear / 1.60 | $256 | $1 | $1 |
| WOOL | 200 | 105 | log / 0.20 | **sq** / 3.20 | $240 | $1 | $1 |
| FERTILIZER | 100 | 200 | linear / 0.40 | linear / 0.40 | $140 | $60 | $20 |

Read the last three columns as: sell one field's worth (`T`) into a market that
was `T` short and you still get a good price; sell `T` into an at-equilibrium
market and premium lines are already at the **$1 floor**. Premium goods
(`base > 100`: STRAWBERRY, MELON, MILK, WOOL) all have `above_target > 1` — they
punish gluts brutally, so bundle and time those sales.

A local reimplementation of this curve is `price_at()` in `main.py` (and
`_shape` / `market_price` in the env source). Use it to size each `SELL`.

### Overrides

`env.configuration["marketParams"]` can sparsely override any of
`base, I0, T, below_func, below_target, above_func, above_target` per resource,
e.g. `{"WOOL": {"above_target": 0.95}}`. The ladder uses defaults; only relevant
if an episode's config exposes an override (it generally won't).

## How orders execute

- Each turn both players' market lists are processed **slot by slot** (order 0
  of P0 with order 0 of P1, then order 1s, …).
- `HIRE` and `BUY_LAND` are **atomic**, handled once per slot in player order.
- `SELL` / `BUY_SEED` / `BUY_PRODUCT` / `BUY_ANIMAL` run a **per-unit lockstep**:
  quote both players' current unit at the **same pre-commit inventory**, commit
  both, repeat until both orders in that slot are exhausted.
  - `SELL`: `money += price`, `shed -= 1`, and **inventory += 1 only if
    `price > 1`** (floor sales don't add supply). So the marginal price **drops
    within your own order** as you sell — a `SELL TOMATO 60` gets a worse average
    than 60 separate small sells would across turns.
  - `BUY_PRODUCT`: priced at **post-buy** inventory (`inv − 1`). An immediate
    buy-then-sell of the same item against an otherwise-unchanged market nets
    exactly $0.
- `market["prices"]` in the observation refreshes only **after** each slot and
  after town consumption — so the price you see in `obs` is last step's
  post-everything price, and what you actually realise depends on your own
  volume and the opponent's.
- There is **no per-turn quantity cap**, only 10 order **lines**. One line can be
  `SELL WHEAT 200`.

## Town consumption math (both players share one market)

- **Town center:** 1 of each of WHEAT, CARROT, TOMATO, STRAWBERRY, MELON, EGG,
  MILK, WOOL, per day (step % 24 == 0). Flat. 30 units/product/season.
- **Shops:** ticks at `step % 4 == 0` → hours 0, 4, 8, 12, 16, 20 → **6/day**
  per instance per demanded product; **12/day** for a single-product shop's one
  product. 8 instances unlock by end of day 23 (~132 shop-days of demand).
- Rough **combined season town demand** (both players, expected shop draw):
  WHEAT ~525, STRAWBERRY ~425, CARROT ~325, MILK ~325, TOMATO ~230, WOOL ~230,
  EGG ~230, MELON 30 (town-center only; no shop wants it).
- As sole supplier at base price that's **~$220k of demand you could fill.**
  The binding limit is one farm's *production*, not demand (see `06 §0`).

## Derived economic facts (measured from replays — carry these forward)

- **The market barely moves in a normal game.** Across full seasons both players
  combined dent inventory by only ~100–450 units/product (from I0 = 10000). Town
  drains faster than typical production, so **premium/ongoing prices climb well
  above base and stay there.** Observed end prices: STRAWBERRY 185–348,
  MILK up to 364, TOMATO 44–380, WOOL up to 255, MELON bimodal 7–280.
  **Implication: produce far more high-value goods than feels safe.**
- **WHEAT is rock-stable** — 33–56 all season across 30 games, never crashes,
  never spikes. It is a pure *volume* lever; a wheat flood sells 600–1600
  units/season at a reliable ~$20–40.
- **CARROT** has a low ceiling and few consumers (only PET_CAFE + FARMERS_MARKET)
  — oversells easily, often $23–48. Worst $/tile-day crop in the set.
- **MELON** crashes below ~$50 on **any** glut (`sq` above-curve). Only a
  scarcity side-bet; hard-cap ~5 tiles.
- **MILK / WOOL / FERTILIZER are the contested goods.** When *both* players sell
  them they floor to single digits (milk seen at 5, wool at 1, fertilizer at 13).
  A big cow/sheep herd is only a blowout when the opponent is **not** also an
  animal farm. Spread these sales; skip them when price < ~0.5× base and hold for
  the terminal dump.
- **STRAWBERRY is the safest premium** — never ended below 185 (base 120) in 30
  ladder games. Ongoing, high scarcity ceiling, no observed glut collapse.
- **TOMATO** has a `hinge` scarcity ceiling — ran to $380+ uncontested; a strong
  ongoing line if planted early enough to fire its 4 ticks.
- **EGG** is usually ~$60 but spikes hard (to ~$211) if nobody else keeps geese.
  Relatively glut-resistant (`log` above-curve).
- **Selling at the $1 floor still pays $1/unit and doesn't add supply** — so on
  the final day, dump everything; every unit is positive reward.
