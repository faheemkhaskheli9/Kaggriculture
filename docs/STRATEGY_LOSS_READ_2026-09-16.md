# Loss read 2026-09-16 — v45 `56259132` at 37 eps (20W-0T-17L, af 17-17)

Scratch scripts (session temp, reduce replay JSON): plant_trace.py (per-day
crop mix / idle tiles / seeds / action counts), mix13.py (d13 mix, idle tiles
d15/d20, opp STR sells), strinv.py (STR inventory + realized prices), cc_replay.py
(re-runs `choose_crops` on the real observation), income.py (daily $ by item,
prices, herd fed state), milk.py (MILK/EGG/WOOL/FERT/STR prices d12-25 + herds).

## Findings, ranked by what we can act on

**A. Crop chooser crowding artefact → WHEAT churn + idle tiles (5/37 games: 3L 2W).**
`choose_crops` Lever-2 prices each crop at `price_at(mkt_inv + opp_tiles*decay +
own picks)`. At d12 h1 in `109371856`: STR observed 168 (inv −32) → value 30;
39 opp STR tiles project 107 → 19.3; drained WHEAT market (inv −154, price 37)
values WHEAT at 20.2 → 21-23 of 24 picks WHEAT. Result: the fresh 3rd quadrant
gets 2-day WHEAT churn the labour-bound hands cannot keep replanted (12-21 idle
tiles d13-25; 12 STR + 9 TOM seeds held unplanted to d29). In 37/37 games STR
inventory stayed below I0 through d20 regardless of opp tiles (max 49); the
late crashes came from the opp's *selling* pace (41 opp tiles → no crash, 36 →
$1). → **C3 `ENABLE_CROP_CROWD_OWN_ONLY`** (drop the opp-tile term; keep own-pick
decay). `agents/main_v49_cropcrowd.py`, tests/test_crop_crowd_own_only.py (5).
EV modest (~$5-9k in affected games, none of the 3 losses flips) but it is a
model bug contradicted by every game, mechanical, byte no-op when opp field empty.

**B. Opponent product dumps crash thin markets — not fixable on our side.**
MILK ≤ $63 at d20 in 11/37 games (6L 6W): opp sells 21-27 MILK/day at d15-16
(MILK T=122, linear 1.6 → $1 at +76). Our MILK income $4-10k in crash games vs
$30-65k otherwise; our 5 cows then earn only fertilizer. Opp cow count at d10
(3-9) does NOT separate crash from no-crash games → herd switching is a coin
flip (EV<0). STR crash at d23+ (price $1-20 at d25) in 6-7 games, 5-6 of them
losses incl. the 3 worst (31k/32k/35k): combined ~50 STR/day > drain from d20
(inventory −54 → +62). Our sells were production-limited before the crash;
holding for d28-29 recovery is worth ≤ $3k. Do not tune sells for this.

**C. The three worst losses are out-scaled before any crash.** d15-20 income
+4.9k vs +17.6k in a comparable win: the MILK crash (B) removed ~$1.5-2.5k/day.
Opp animal_factory variants finish 8-9 COW + 4-6 SHEEP + 30-40 STR tiles → the
throughput answer remains feed-first (`56281675`, pending) → HERD-14 re-gate.

**Dropped: W1 wheat sell/buy churn.** Engine quotes BUY_PRODUCT at post-buy
inventory ("a buy/sell round-trip against an unchanged market nets zero"), so
the h0 sell / h3-5 re-buy is cash-neutral; only market-slot noise. Not a sub.

## D. The market's only sink is the town shop draw — and we never read it (headline)

Engine (`_town_consume`, `SHOPS`): every unlocked shop instance removes 1 unit of
each of its products every 4 steps (6/day; 12/day for the single-product
YARN_STORE / PET_CAFE), the town centre removes 1/day of everything but
FERTILIZER, and one shop is drawn with replacement every 3 days (d3..d24, max
8). Nothing else drains inventory. `obs.town.unlocked_shops` is public.
STRAWBERRY shops: BRUNCH, ICE_CREAM, SMOOTHIE, FARMERS (4/8). MILK: PIZZA,
ICE_CREAM, SMOOTHIE (3/8). EGG: BAKERY, BRUNCH. WOOL: YARN only (12/day).

Ladder (37 eps, scratch shops.py): **all 7 STRAWBERRY crashes had 0-1
strawberry shops among the first four draws (drain ≤ 6/day at d12)**; every game
with ≥ 2 had d25 prices 196-267. **All 12 MILK crashes had 0-1 milk shops at
d12.** `109354747` drew YARN×5 (WOOL drain 60/day, price 254; MILK 0 shops →
$1 from d16; STRAWBERRY 0 shops → $1 at d25): we fielded 5 cows, 1 sheep, 24
STR. The gate's game-91 −23k swing was the same thing (shop draw diverged).
`demand_counts()` exists in main.py but only decides SHEEP 2 vs 1.

→ **S1 `ENABLE_SHOP_DEMAND_VALUE`** (`agents/main_v50_shopdemand.py`,
tests/test_shop_demand_value.py, 8): Lever-2 sale price = observed-inventory
price × marginal absorption — drain (shops + expected undrawn shops + below-I0
buffer / production window) minus the supply of tiles already planted (ours +
opponent's, units/day); the remainder is worth $1. Replays: `109533084` d11 ON
plants 1 STR + 23 WHEAT instead of 23 STR (mine 27 + opp 31 already saturate
19/day); high-drain `109355960` ON == OFF at every step. Supersedes C3.
→ **S2 (next): herd by drain** — COW/GOOSE/SHEEP `want` from MILK/EGG/WOOL
drain vs opp herd supply (COW 0.5 MILK/day, GOOSE 1 EGG/day, SHEEP 1/3 WOOL/day).

## Queue after this read
1. Judge `56281675` (feed-first) at ≥20 eps → promote → re-gate HERD-14 on it.
2. S1 `ENABLE_SHOP_DEMAND_VALUE` — gated, submit on the v45 parent (C3 held).
3. S2 herd-by-drain (single flag) on whichever parent is promoted.
4. H3 re-read only after the above.
