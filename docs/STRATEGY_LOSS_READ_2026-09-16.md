# Loss read 2026-09-16 — v45 `56259132` at 37 eps (20W-0T-17L, af 17-17)

Scratch scripts (session temp, reduce replay JSON): plant_trace.py (per-day
crop mix / idle tiles / seeds / action counts), mix13.py (d13 mix, idle tiles
d15/d20, opp STR sells), strinv.py (STR inventory + realized prices), cc_replay.py
(re-runs `choose_crops` on the real observation), income.py (daily $ by item,
prices, herd fed state), milk.py (MILK/EGG/WOOL/FERT/STR prices d12-25 + herds);
pt3: herd_bt_extract.py, herd_bt.py, util_scan.py, idle_scan.py;
2026-09-17 (§G): shop_scan.py (STR/MILK d25 prices, shops by d12, crop mix per
game), top_trace.py <ep> (day-by-day both farms: money, mix, herd, hands, prices,
opp market orders), herd_mix_scan.py / wool_scan.py (herd by kind, wool price vs
yarn-store draws and sheep counts), probe_yarn.py <agent> <seeds> (local yarn
day / herd / wool / final vs animal_factory).

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

## E. Herd-by-drain (S2) backtest — WEAK, dropped as a sub candidate (pt3, 61 eps incl. 56281675/56282756)

Scratch: herd_bt_extract.py / herd_bt.py (per-day shops, herds, MILK/EGG/WOOL
inventory; re-runs the marginal-animal rule with `price_at`). Facts:
- MILK is the swing line: revMILK median 5.3k with 0 milk shops by d12, 14.8k
  with 1, 40k with ≥2 (per cow 1.0k / 2.8k / 6.9k). EGG never moves (d25 price
  41-70 in all 61 games, log curve) — a goose is a flat ~2.1k. WOOL 4k/sheep.
- Cows are bought d3-9 (4.0 cows by d9, 5.9 by d12) — before most draws. At
  d9 the "0 milk shops known" rule (future-draw weight 0) calls goose in
  15/61 games, 13 correctly; at d6 it is 10 right / 9 wrong; at d3 half wrong.
- The payoff is asymmetric: a wrong goose call forfeits 2-5k per slot, a right
  one saves only ~0.4-1.4k (a cow in a crashed market still earns ~1.7k vs a
  goose's 2.1k). Net over the 61 games ≈ +400/game at best. Not worth a slot.

## F. The day 6-10 cash crater is the reserve ramp blocking $10 seeds (pt3 headline → M1)

Scratch: util_scan.py / idle_scan.py (tiles by kind per day; idle vs cash,
seed/animal/land spend per day), replay trace of 109713885 d5-d13.
- Tile use by day (57 eps): 1 quad d0-5 full (idle 2.5); quad 2 lands d6
  (BUY_LAND $1,000, money 1,489 → 117 in the trace); idle 13.9 / 18.4 /
  25.1 / 20.0 / 13.4 on d6-d10 ≈ 90 tile-days per game; 3 quads d11-12, then
  labour-bound (idle 25 → 10 over d11-13 with 13-15k cash, plants 7-16/day).
- Cash h0: d7 462, d8 415, d9 1,229 (min-of-day 149 / 272 / 936). Reserve
  ramp `min(1400, 200+150*day)` = 1,250-1,400; P3f relax needs shed value +
  90/animal ≥ 0.75× that and the shed is empty after the h1 sells → seed
  budget `money - reserve` = 0. Seeds bought: d7 0.7, d8 4.4. Same hours we
  pay $27-33 each for 2-4 BUY_PRODUCT WHEAT feed units.
- Leftover seeds: at d7 the shed held 9 CARROT/WHEAT/STRAWBERRY seeds that
  were never planted because `add_plant_tasks` only exposes PLANT tasks for
  the chooser's picks (STR/MELON at d7+), so they sat while 15 tiles idled.
- W vs L idle tile-days d6-11 are equal (114 vs 117) — this is income for
  every game, not a loss discriminator. WHEAT: $10 → ~3 units in ~4 days
  (feed or $25 sale, log curve never crashes); harvest lands d11-12 when
  planting is labour-bound anyway, so it does not delay STRAWBERRY.
- **M1 `ENABLE_IDLE_SEED_BYPASS`** (agents/main_v51_idleseed.py): when the
  seed loop bought nothing and idle unreserved tiles exceed seeds on hand
  (≥6), buy WHEAT seeds for the shortfall down to max(120, one day of feed
  for the herd); the planter fills uncovered empty tiles with leftover seeds
  (WHEAT first, then any crop inside plant-by). Day ≤ 12, hour ≤ 20.
  Replayed d7-8 observations: 6-19 seeds/turn where OFF bought 0. 11 tests.
- **Gate (compete_v51.log, 96 pairs vs promoted main): REJECTED.** 89-0-7 both,
  af 46/46, 0 errors, but own money −8.6k mean (33/96 pairs positive), day-10
  cash −9.8k, vs main 2-1-6. Pair 95 (animal_factory, same seed): candidate
  bought 29 WHEAT seeds d8-10; at d10 it held WHEAT 18 / STR 12 vs baseline
  STR 23; the higher fill tripped the land gate so quad 3 was bought at d9
  ($2,000 → cash 151 at d10 vs 1,441) and the watering load delayed the
  melon harvest (d10 sells 5.7k vs 15.1k; 4 melons still standing at d13).
  Lesson: the d7-8 idle tiles are where the d9-10 STRAWBERRY wave lands;
  wheat planted there matures d11-12 and displaces STR by 1-2 yields
  (~$200/tile) for a $75 wheat cycle. The crater is an opportunity-cost
  window, not free capacity. Flag stays OFF; no sub.

## G. WOOL is the held-up product and sheep are the out-scaling lever — gated by the yarn-store draw (2026-09-17, 76 eps of `56281675` + `56282756`)

Both subs at 38 eps sit on the same plateau: 20-0-18 each, animal_factory
16-15 / 15-15, mean own money 81.0k / 80.1k, and the 18 losses are still
out-scaled (opp 95-174k). Tracing the 161-173k winners (`top_trace.py`
109918076 / 109983266): 6 COW + 11 SHEEP by d11, STR33 + WHE24, ~10 hands,
and from d15 they bank 8-10k/day while we bank 1-4k/day with STR45 and 5
COW / 5 GOOSE / 1 SHEEP. Their herd income is roughly 6 cows x 4 MILK x ~130
= 3.1k plus 11 sheep x 2 WOOL x ~240 = 5.3k per day; WOOL stayed at 232-244
for the whole game.

Engine (`market_price`): every product has I0 = 10000; WOOL is base 200,
T = 105, log-shaped +20% below I0 (to ~240) and a *square* -320% above it, so
it floors at $5 once the market holds ~105 units over I0. The only sink is
`_town_consume`, and YARN_STORE is the one single-product shop (12 WOOL/day).

Across the 76 games (`wool_scan.py`):

| condition | n | WOOL d25 mean | crashes (<=66) | our W |
|---|---|---|---|---|
| YARN_STORE drawn by d9 | 27 | 243-250 | 0 | 9/27 |
| no YARN_STORE by d29 | 28 | 78 | 15 | 20/28 |
| >=1 yarn by d29 & total sheep >= 6 | 29 | 231 | 1 | **5/29** |
| no yarn & total sheep >= 6 | 13 | 25 | 11 | 8/13 |

Opponent sheep count at d20 is the strongest strength correlate: 8+ sheep ->
opp 98k, we win 4/19; <=2 sheep -> opp 38-77k, we win 14/15. Our own herd
averages 5.7 COW / 1.1 SHEEP / 5.3 GOOSE (EGG d25 41-69 always; MILK d25 <=
100 in 32/76). Per animal-day at d25 prices: goose 4 x ~50 = ~200 ($300),
cow 4 x ~130 = ~520 but <= 400 in 42% of games ($400), sheep 2 x ~240 = ~480
when a yarn store exists and ~10 when not ($500).

**Candidate SHEEP-ON-YARN (`ENABLE_SHEEP_ON_YARN`, v53):** while
`demand_counts()["WOOL"] >= 1`, the goose slots go to sheep -- herd-match
want COW5/SHEEP5/GOOSE1, non-match COW8/SHEEP4/GOOSE1, SHEEP ordered before
GOOSE so the one-per-turn buy loop fills sheep first; placed/shed animals
kept; no yarn store -> exact prior targets. Gate 91-3-2, 0 err, af 35/35
(+1.5k), I/S/R 2/94/0, +2.9k mean. 8-seed probe vs animal_factory: the 3
seeds with a yarn store by d9 end SH6/CO5-6/GO1 and +13.5k / +35.5k / +24.8k
own money; the rest are byte-identical games. **Submitted `56307690`.**

Open (not built): the realized herd overshoots the want by 1-2 (probe: GOOSE
6-7 vs want 5, COW 6 vs 5) -- the one-per-turn BUY_ANIMAL loop compares
placed + shed against want, so a purchase that has not yet landed in the
shed lets a second buy through. Mechanical; worth a look if SHEEP-ON-YARN
holds (extra $300-500 per game and one crop tile).

## Queue after this read (pt3)
1. `56281675` feed-first **PROMOTED** (20 eps, af 8-7, 667.3, animals 12.3) — `ENABLE_FEED_FIRST=True` on main.py.
2. M1 `ENABLE_IDLE_SEED_BYPASS` — gated, **REJECTED** (F). OFF.
3. HERD-14 re-gate on the feed-first parent (`agents/main_v52_herd14ff.py`, `compete_v52.log`): 91-0-5, 0 err, af 46/46, escapes fixed, animals 13.05 → 15.20, but own money −1.6k mean / −2.3k median (39/96 positive; vs animal_factory −3.1k, 15/46 positive) → **REJECTED**. Herd size is not the out-scaling lever (cf. §E).
4. Judge `56282756` (S1) at ≥20 eps — the only open item. S2 dropped (E). H3 re-read last.

Open question for the next read: the losses are still "out-scaled by animal_factory" (opp 100-124k vs our 52-83k at 20 eps of `56281675`) yet more animals (HERD-14) and more early tiles (M1) both lose money locally. The remaining candidates are on the demand side: S1's shop-aware crop value (pending) and, if it holds, a shop-aware *sell* pacing / product mix rather than more supply.

## Queue after this read (2026-09-17)
1. `56282756` S1 at 38 eps: 20-0-18, af 50.0%, STR crashes 5/38 = parent -> **NOT PROMOTABLE**, OFF. `56281675` feed-first at 38 eps 20-0-18, af 51.6%, live 638.5 -- stays promoted.
2. SHEEP-ON-YARN `ENABLE_SHEEP_ON_YARN` (`agents/main_v53_sheepyarn.py`) -- gated clean, **SUBMITTED `56307690`**. Judge at >=20 eps: af >= 51.6% AND ladder >= 662.6; primary = avg SHEEP >= 4 and WOOL d25 >= 199 in yarn-store games, W-rate in (yarn & total sheep >= 6) games > 5/29.
3. If it holds: BUY_ANIMAL overshoot fix (section G open item), then a milk-shop-conditional cow/sheep split (S2 was dropped only because cows are bought before the draws; sheep slots are decided later).
4. C3, M1, HERD-14, S2 stay OFF/dropped. H3 re-read last.
