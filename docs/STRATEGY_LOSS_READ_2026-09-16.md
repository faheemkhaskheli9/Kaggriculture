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

**Outcome (2026-09-17, `56307690` at 25 eps): SHEEP-ON-YARN PROMOTED.** 14-0-10,
af 12-10 = 54.5%, 0 err, ladder 661.6 (tie with S1's 662.6; feed-first 644.4).
Yarn by d9 (n=10): sheep d20 5.7 vs 1.0, WOOL d25 228 / 0 crashes, W 6/10 vs
3/9, own money 85.0k vs 70.6k. Late/no yarn (n=11): 8/11, 88.5k vs 87.7k =
unchanged code path. Yarn d10-17 (n=4): 0/4 against 94-141k opponents but own
money 75.0k = parent 75.1k; the herd reaches 5/7/5 = 17 there because placed
geese are kept when sheep are added (cap applies to new buys only).

## H. The BUY_ANIMAL overshoot is a carried-animal blind spot, and it is load-bearing (2026-09-17, 26 eps of `56307690`)

Scan (`overshoot_scan.py`): 6.7 of 14.2 BUY_ANIMAL orders per game are issued
while a crew hand already carries that species. The loop compares placed +
shed against the target; an animal PICKUPed from the shed but not yet PLACEd
is in neither, so the turn after every pickup the loop sees a deficit and
buys again. Realized herd 13.15 placed vs an 11-12 want; 14 bought, one sits
unplaced in the shed all game; 36 PICKUPs per game for 13 PLACEs.

Candidate `ENABLE_BUY_COUNT_CARRIED` (`agents/main_v54_buycarried.py`): count
`private.inventories` animals as owned. Probe: bought 14 -> 11, PICKUP 36 ->
12-14, placed 13 -> 11, shed leftover 0 -- and the 4th cow by d9 (over the
1-quad cap of 3) disappears. Two 96-pair gates (`compete_v54.log`,
`compete_v54b.log`): af 73/73 both ways, 0 err, own money +4.0k / +1.4k mean
but run-2 median -1.6k (46/96 up), mirror vs main 7-13. **REJECTED**: the
overshoot is the herd every promoted read was achieved with. A re-try must
pair the count fix with explicit realized targets (match 6/6/1, 1-quad cap 4)
so only the churn goes away; expected value is small (~$450 + ~23 hand-turns).

## Queue after this read (pt3)
1. `56281675` feed-first **PROMOTED** (20 eps, af 8-7, 667.3, animals 12.3) — `ENABLE_FEED_FIRST=True` on main.py.
2. M1 `ENABLE_IDLE_SEED_BYPASS` — gated, **REJECTED** (F). OFF.
3. HERD-14 re-gate on the feed-first parent (`agents/main_v52_herd14ff.py`, `compete_v52.log`): 91-0-5, 0 err, af 46/46, escapes fixed, animals 13.05 → 15.20, but own money −1.6k mean / −2.3k median (39/96 positive; vs animal_factory −3.1k, 15/46 positive) → **REJECTED**. Herd size is not the out-scaling lever (cf. §E).
4. Judge `56282756` (S1) at ≥20 eps — the only open item. S2 dropped (E). H3 re-read last.

Open question for the next read: the losses are still "out-scaled by animal_factory" (opp 100-124k vs our 52-83k at 20 eps of `56281675`) yet more animals (HERD-14) and more early tiles (M1) both lose money locally. The remaining candidates are on the demand side: S1's shop-aware crop value (pending) and, if it holds, a shop-aware *sell* pacing / product mix rather than more supply.

## I. MILK has the same sink as WOOL, and our 5th-6th cows are bought after the draw has already said no (2026-09-17, 139 eps)

Scan (`milk_scan.py` / `milk_scan2.py` over `56259132`/`56281675`/`56282756`/
`56307690`): the milk-buying shops are ICE_CREAM_SHOP, PIZZA_SHOP and
SMOOTHIE_SHOP, 3 of the 8; the engine draws one shop every 3 days from d3,
with replacement, appended to `unlocked_shops` in order. P(no milk shop in
the first 3 draws) = 26% of games, and there MILK d25 <= 40 in 29/36 (81%,
mean 27); none by d12 -> 21/22 (95%). A milk shop by d6 -> 7/78 crashes,
mean 180. Our cows: 3 by d6, 4 by d9, 5th and 6th between d9 and d12 -- the
two late cows are bought right after the third draw. In the 15 (yarn by d9,
no milk by d12) games we still ran 5-6 cows into a $5-13 MILK price.

Candidate `ENABLE_COW_ON_MILK` (`agents/main_v55_cowmilk.py`): from d9, if no
MILK shop and a YARN_STORE are among the first 3 draws, cap COW want at 4 and
give the freed slots to SHEEP (placed/shed cows kept; sticky: a d12+ milk
shop still crashes 8/14 and a cow bought after d12 never pays back its $400
+ feed). Three gates on the same seed: cows-to-geese when no yarn was a wash
(15 pairs median -1.0k, 4 up) and a d12 yarn draw stacked sheep on the extra
geese (17-18 animals, -12k twice) -> dropped; any-yarn still hit the d12-yarn
case (-8.7k / -3.0k) -> yarn must be an early draw too. Final
(`compete_v55c.log`): 91-3-2, 0 err, af 35/35, I/S/R 1/95/0, CI [+0.0, +1.6];
the 12 targeted pairs +4.3k mean / +5.2k median own money (9 up, herd 4/7/1
vs 6/6/1), 84 pairs byte-identical. **SUBMITTED `56311727`.**

## J. The late yarn draw stacks sheep on kept geese, but the 17-19 herd is not the loss (2026-09-18, 75 eps)

**Read** (`56307690` + `56311727`, scratch `late_yarn_scan.py`), by the day the YARN_STORE is drawn:

| bucket | n | W | own money | opp money | herd d29 | sheep d29 | WOOL d25 |
|---|---|---|---|---|---|---|---|
| yarn <= d9 | 27 | 16/27 | 88.9k | 85.4k | 12.6 | 6.2 | 229 |
| yarn d10-17 | 14 | 5/14 | 81.8k | 97.2k | 17.1 | 6.0 | 234 |
| yarn >= d18 / none | 34 | 21/34 | 83.6k | 78.0k | 12.3 | 1.0 | 104 |

Every one of the 14 late-yarn games ends at 15-19 animals on a 3-quad farm whose cap is 13: `animal_targets` takes `max(have, min(want, cap - tot))` species by species, so the 4-5 geese already placed by d12 keep their slots while SHEEP-ON-YARN adds its 5 sheep, plus the usual +1-2 overshoot. Sheep cost 500 and there is no sell action.

**Candidate** HERD-CAP-RESERVE `ENABLE_HERD_CAP_RESERVE` (`agents/main_v56_herdcap.py`, 9 tests, suite 162/162): each species' room is `cap - tot` minus the placed counts of the species still to come, so the total never passes the quad cap unless it already does. Early-yarn, no-yarn and COW-ON-MILK targets are unchanged (their wants sum to <= cap before any goose is placed).

**Gate** `compete_v56.log` (96 pairs, seed 260918): 95-0-1, 0 err, af 47/47, I/S/R 0/96/0, margin delta -668 mean. The 17 late-yarn pairs it targets: max herd 13.8 vs 17.1, but own money **-919 mean / -942 median, 8 up / 9 down** (worst -18.6k / -12.8k / -9.4k). The 29 early-yarn pairs are 27 identical; 12 late/no-yarn pairs diverged where the cap bound a 10th cow (-22.7k .. +18.1k, -181 mean).

**Verdict: REJECTED, dormant OFF.** The herd-size story was wrong: a 500-coin sheep under WOOL ~245 pays for itself even stacked on six kept geese, so the cap only forfeits wool. The late-yarn bucket's own money (81.8k) sits at the no-yarn level (83.6k); the 5/14 comes from the opponents, who already hold 4-9 sheep when the yarn store lands and cash 97k there against 78-85k elsewhere. Owning sheep *before* the draw is the general "sheep are cheap" economy question, benched. Do not retry a total-herd cap.

## K. The churn-only BUY-COUNT retry cannot beat shop-draw noise (2026-09-18, 75 eps + 192 gate pairs)

**Read** (`56307690` + `56311727`, scratch `overshoot_scan.py`): the re-buy overshoot is +1 on each multi-animal species in 50-60% of games -- noyarn match 5/1/5 gets COW +1 in 17/33 and GOOSE +1 in 17/33, yarn match 5/5/1 gets +1 on COW and SHEEP in 18/29, milk-cap 4/6/1 lands 5/7/1 -- and 4 cows stand by d9 in 74/75 games against the 1-quad cap of 3. Buys 14.2-14.9 per game for 13.3 placed; 120-137 PICKUPs per game.

**Candidate** BUY-COUNT-REALIZED `ENABLE_BUY_COUNT_REALIZED` (`agents/main_v57_buyrealized.py`, 12 tests, suite 174/174): carried animals count as owned (the v54 fix) + every species with want >= 2 bumped +1 when the bumped total fits the quad cap (match 6/1/6, 6/6/1, milk-cap 5/7/1 = 13) + 1-quad cap 4.

**Gate** x2, 96 pairs each: 95-0-1 both, 0 err, af 47/47 and 42/42, I/S/R 1/94/1 both. Churn removed as designed (buys 14.8 -> 13.6, PICKUPs 136 -> 120, cows by d9 4.0 both). Own money **+3,187 mean / +2,762 median (54/96 up) on seed 260918, then -4,657 / -3,502 (44/96 up) on seed 260919**; 0 of 192 pairs byte-identical. Herd d20 13.6 -> 13.0: the non-match branch loses its overshoot (bumped 10/3/1 exceeds the cap, so 9/1/2 replaces the realized 10/1/2 and 10/0/4; that bucket is -10.9k mean on seed 2) while the late-yarn match branch stacks higher (17.3 vs 13.1).

**Verdict: REJECTED, dormant OFF.** Same shape as v54 (+4.0k then +1.4k / median -1.6k). A buy-timing change shifts the RNG stream, so every pair diverges into shop-draw chaos that is 10x the ~$450 + 15 hand-turns the churn costs, and deterministic targets cannot reproduce a stochastic overshoot branch by branch. The BUY-COUNT family is closed after two retries; the re-buy stays.

## L. H3 fertilize pays once the herd stops eating the crew (2026-09-18, 96 gate pairs)

**Why re-read**: H3 `56233524` was judged at parity on the 09-14 parent (40 eps, af 50%, 638.6 > the 620.2 peak of the time) and the 09-15 audit named labour coverage (42% of ongoing-crop tick-days unwatered) as the binding constraint; since then herd-install-first cut animal PICKUPs ~80 -> ~25/game, feed-first/sheep-on-yarn/cow-on-milk landed, and the queue's last item was this re-read. Same dormant hunk, one line flipped (`agents/main_v58_fertilize.py` = `main.py` + `ENABLE_CROP_FERTILIZE = True`; `tests/test_crop_fertilize.py` 6/6, suite 174/174).

**Gate**: Gate `compete_v58.log` (`compete_runs/20260918-095233-436414`, seed 260920) vs `main.py`: 95-0-1, 0 err, score delta +3.1% CI [+0.0, +6.8], I/S/R 6/89/1 (all self-play mirror 6/4/1, +27.3%), af 33/33 I/S/R 0/33/0 own money +4,295 mean / +3,823 median (27/33 up), all 96 pairs +2,469 mean / +2,771 median (65/96 up, 0 identical), premium n=16 -1.1k / -258 median (8 up), FERTILIZE 58.6/game (0 before), STRAWBERRY sold 245 vs 213, WATER ops 932 vs 992, productive actions +65, escapes flat.

**Read**: the +2 fertilized tick converts straight into STRAWBERRY volume (+32 units/game) with fewer WATER ops, not more -- the crew now has the slack the 09-15 audit said it lacked. The one soft bucket is premium (-1.1k mean, -258 median), inside noise. Unlike v54/v57 the effect is a mechanism (58.6 FERTILIZE ops/game from 0), so a single seed is trusted. **SUBMITTED `56321057`** (1/5 today); judge at >=20 eps against `56311727` (af 50.0%, 685.4).

## Queue after this read (2026-09-17)
1. `56282756` S1 at 38 eps: 20-0-18, af 50.0%, STR crashes 5/38 = parent -> **NOT PROMOTABLE**, OFF. `56281675` feed-first at 38 eps 20-0-18, af 51.6%, live 638.5 -- stays promoted.
2. SHEEP-ON-YARN `ENABLE_SHEEP_ON_YARN` (`agents/main_v53_sheepyarn.py`) -- gated clean, **SUBMITTED `56307690`**. Judge at >=20 eps: af >= 51.6% AND ladder >= 662.6; primary = avg SHEEP >= 4 and WOOL d25 >= 199 in yarn-store games, W-rate in (yarn & total sheep >= 6) games > 5/29.
3. `56307690` **PROMOTED** at 25 eps (af 54.5%, sheep 5.7 / WOOL 228 / 0 crashes in yarn-by-d9 games). BUY_ANIMAL overshoot fix (section H) gated x2 and **REJECTED** -- the overshoot is load-bearing.
4. COW-ON-MILK (section I) built, gated x3 and **SUBMITTED `56311727`** -- judge at >=20 eps on the (yarn by d9, no milk by d9) bucket. Next after that: the yarn d10-17 case (placed geese kept -> 17-animal herd, 0/4 on the ladder, -8.7k/-12k in the gates whenever a late yarn draw adds sheep on top of geese) -- cap total herd when sheep are added late, or fill only freed slots.
5. C3, M1, HERD-14, S2, BUY-COUNT-CARRIED stay OFF/dropped. H3 re-read last.
6. (2026-09-18) `56311727` **PROMOTED** at 36 eps (21-0-15, af 50.0%, 0 err, 685.4 = all-time best; targeted bucket herds 4/8/1 as designed). HERD-CAP-RESERVE (section J) gated flat-to-negative and **REJECTED** -- the late-yarn case is closed (opponent strength, not our herd).
7. Remaining: churn-only BUY-COUNT-CARRIED retry (count fix + explicit realized targets 6/6/1, 1-quad cap 4) as filler; H3 re-read last. 0/5 subs used 2026-09-18.
8. (2026-09-18, 2nd) BUY-COUNT-REALIZED (section K) gated +3.2k then -4.7k own money across two seeds -> **REJECTED**; the BUY-COUNT family is closed. Remaining: H3 re-read only; otherwise the ladder waits for new episodes on `56311727` (36 eps, 685.4). 0/5 subs used.
9. (2026-09-18, 3rd) H3 re-read (section L): `ENABLE_CROP_FERTILIZE` on the current parent gated +2.5k mean / +2.8k median own money (65/96 up, af 27/33 up, FERTILIZE 58.6/game) -> **SUBMITTED `56321057`**. Tracked pair `56321057` + `56311727`. Queue is now empty: judge `56321057` at >=20 eps, otherwise wait. 1/5 subs used.
