# Loss read 2026-09-14 — H3/H4 first readback and the tomato-flip bug

Companion to `docs/STRATEGY_TOP3_GAP_2026-09-13.md` (which this supersedes as
the queue). Evidence = 88 real-ladder replays of the current lineage
(`56195143` H1, `56199529` N1, `56233524` H3, `56235916` H4), pulled with
`download_episodes.py --submissions 56233524 56235916` and reduced with
`tools/ladder_analyze.py` plus two scratch scans (day-by-day both-seat table;
day-12/15/20 crop mix per game). No raw replay was read into context.

## 1. Ladder state

| sub | flag | eps | W-T-L | animal_factory | ladder | verdict |
|---|---|---|---|---|---|---|
| `56199529` N1 opening-melon (promoted) | `ENABLE_OPENING_MELON` | 32 | 14-0-18 (44%) | 13-12 = 52% | 608.6 | board-best until today |
| `56233524` H3 | `ENABLE_CROP_FERTILIZE` | 27 | 14-0-13 (52%) | 13-11 = **54.2%** | **652.7** | guardrail met exactly (≥54.2%), ladder +44 over N1 → **promote** |
| `56235916` H4 | `ENABLE_CROSS_ZONE_WATER` | 3 | 1-1-1 | 1-0 | 663.1 (provisional) | **hold** — re-read at ≥20 eps |

0 `agent()` exceptions in either sub's logs. Both are above the 620.2 all-time
peak, so the rating-floor guard is satisfied for the next submit.

## 2. What the losses are

Two families, and they are separable by one number — our own crop mix at day 15:

| field at day 15 (our seat) | games | W-L | win% | our final $ (median / min) |
|---|---|---|---|---|
| STRAWBERRY-dominant | 55 | 36-18-1T | 65% | 83.5k / 48.5k |
| mixed (TOMATO ≥ 15 tiles) | 21 | 6-15 | 29% | 64.1k / 37.6k |
| TOMATO-dominant (≥ 40 tiles) | 12 | 2-10 | 17% | 56.7k / **23.2k** |

Tomato-heavy games are 38% of games and **25 of the 43 losses (58%)**. They are
self-collapses, not opponent out-scaling: e.g. `108958556` (H3, 20.1k final)
went 54 TOMATO tiles on days 10-21 and cash sat at 5-12k for ten days until the
tomatoes died at day 22 (60 → 40 plants, 21 weeds). Same shape in `108946279`
(24k), `108963758` (30k), `108428894` (35.8k), `108361470`, `108363455`.

The other family (18 STRAWBERRY-dominant losses) is the known out-scaling
pattern: same 55-58 strawberry tiles as the opponent, but they finish 95-180k
against our 60-100k. Day-by-day of `108528898` (izack2666, 146k vs 86k) and
`108476529` (hongchendai, 168k vs 72k): identical cash through day 15, then the
opponent adds +8-10k/day from day 16 while we add +2k/day until day 20. They
run 14-17 animals from day 12 (we plateau at 8), fertilize, and water ~60
tiles/day with 11 hands; we walk more than we water (WEST/EAST 55-70/day vs
WATER 37-60). This is exactly what H3 (fertilize) and H4 (water coverage)
target, so their readbacks are the measurement of this family.

## 3. Root causes (ranked by $ and certainty)

### C1 — crop-value model ignores lifespan: the tomato flip (mechanical bug)

`_crop_tile_value()` (`main.py:971-974`) values an ongoing crop as one unit
every `interval` days for the *entire remaining season*:
`yield_est = (remaining - fy) // interval + 1`. The engine
(`kaggriculture.py:795-802`, `_daily_refresh_plants`) gives exactly
`max_yield` = 4 production ticks and then ends the plant's lifespan; each
tick adds 1 unit (2 if fertilized *and* watered).

Model vs engine at day 10 (remaining 19), base prices:

| crop | model units | model $/tile/day | engine units | engine $/tile/day (occupied days) | fertilized |
|---|---|---|---|---|---|
| TOMATO (seed 50, fy 8, interval 1) | 12 | **35.3** | 4 | 15.8 (12 d) | 35.8 |
| STRAWBERRY (seed 100, fy 10, interval 2) | 5 | 26.3 | 4 | **22.4** (17 d) | 50.6 |

The model prefers TOMATO by default and is near-indifferent, so which crop
wins is decided by day-10 market-inventory noise (town consumption, the
opponent's early sales — the day-10 STRAWBERRY/TOMATO inventories in the scan
are all 9918-9992 vs I0 10000). When STRAWBERRY's projected price is a few %
lower, the whole field goes tomato, and tomato's real value is 30% below
strawberry's (half of it when fertilized). `TASKS.md` had this deferred as
"the crop-value model's finite-lifespan fix"; the ladder says it is the #1
loss cause.

### C2 — bought animals never installed; herd frozen at 8

`108476529`, our seat: 11 `BUY_ANIMAL` (4 on d0, 3 on d9, 4 on d11), 8 placed.
The three bought on day 11 (COW, GOOSE, SHEEP) left the shed on day 12 and were
carried by crew hands until the day-29 terminal drop put them back in the shed,
while two empty pastures/coop stood from day 12 on. A cow also sat in the shed
days 0-9 (one structure short). `animal_targets()` counts shed + carried
animals as owned (`cur = have + shed`), so the target (COW 5 / GOOSE 5 / SHEEP 1
vs an animal-heavy opponent) reads as met, buying stops, and `day > 17`
freezes the herd. Both losing opponents bought 1-2 animals/day from day 2 and
reached 13-17 by day 12. Cost ≈ $1.3k sunk + ~3 animals × 17 days of produce and
fertilizer ≈ $5-6k/game plus the fertilizer H3 needs. H2 (`56199353`, carry
guard) attacked the carry symptom and was retired at −7.9pp (n=20); the
install path itself (crew never re-targets a carried animal to an empty
structure) was not fixed.

### C3 — yield per strawberry tile (H3/H4 — being measured now)

42% of ongoing-crop tick-days unwatered (H3 gate audit) and 0 fertilizer use
before H3: each unwatered tick day forfeits a unit, each unfertilized one
forfeits the second unit. Nothing new to build until the H3/H4 reads are in.

### C4 — minor, do not act yet

Day-27/28 hand cut to 8 leaves 15-30 tiles to die unharvested (weeds29
17-30 in most games, wins included); `WEED_PILEUP` is a label of this, not a
cause — weeds29 does not separate wins from losses (10-36 in both). Wheat
floor (N2) is *not* supported by the evidence: izack2666 won 146k with 0
wheat tiles days 12-29; hongchendai held 24. Sheep (N3): both winners sold
WOOL steadily; we have 0 sheep — fold into C2's target, not a separate lever.

## 4. Queue (one `ENABLE_*` flag per submission, judged at ≥20 eps)

| # | change | file | mechanism | expected | gate / judge |
|---|---|---|---|---|---|
| **C1** | `ENABLE_CROP_VALUE_LIFESPAN` | new `agents/main_v43_croplifespan.py` | in `_crop_tile_value` ongoing branch: `ticks = min(MAX_YIELD[crop], (remaining - fy)//interval + 1)`; `units = ticks * CROP_VALUE_UNITS_PER_TICK` (1.0; 1.5 when `ENABLE_CROP_FERTILIZE` is ON); `occupancy = min(remaining, fy + (ticks-1)*interval + 1)`; return `(price*units - cost)/occupancy`. OFF path byte-identical. Land gate at `main.py:2190` uses the same function — MELON stays its max, so no land-timing change. | tomato-heavy share 38% → ~0%; those 33 games move from 24% to ~65% win → overall score-rate ~50% → ~62%; median $ +15-20k | unit test: day 10, base prices, opp 30 STRAWBERRY → picks are STRAWBERRY not TOMATO; day 15 → TOMATO allowed (STRAWBERRY past `plant_by` 13). `compete.py --games 96 --baseline main.py` full pool: 0 errors, no `animal_factory` regression. Ladder: TOMATO-dominant games at d15 = 0 of first 20; af ≥ 54.2%. |
| 2 | H3 promote | `main.py` ← `ENABLE_CROP_FERTILIZE=True` | judged above | — | flip the flag, LEDGER row |
| 3 | H4 readback | — | at ≥20 eps | — | af ≥ 54.2%; weeds29 < 17 |
| 4 | H3 + H4 union (if H4 holds) | `agents/main_v44_h3h4.py` | both judged flags ON — a promotion merge, not a bundle | — | standard |
| **C2** | `ENABLE_HERD_INSTALL_FIRST` | `agents/main_v45_herdinstall.py` | (a) animal crew: a hand carrying an animal walks to the nearest empty own structure and `PLACE`s before any feed/harvest goal; (b) build a structure *before* buying when none is empty; (c) `animal_targets` counts only placed + shed animals ≤ 1 day old; (d) freeze day 17 → 20. Reuse H2's tests where they still apply; do not re-enable H2's flag. | placed herd 8 → 11 (target) by day 13; +$5-6k/game; +3 fertilizer/day for H3 | probe: `BUY_ANIMAL` count == placed count by day 14 in `probe_game.py`; 96-pair gate; ladder: avg animals ≥ 10.5 (from 7.5), af ≥ guardrail |
| 5 | herd target 11 → 14 vs animal-heavy opponents (`ENABLE_F1_HERD_MATCH` want COW 6 / GOOSE 5 / SHEEP 3) | after C2 only | matches the 14-17 the winners field; sheep add WOOL | +$3-5k/game | only if C2's read shows placed == bought |

Submission budget: 3 subs remain today (UTC 2026-09-14); ~6 clean main-slot
reads to the 2026-09-30 deadline. Spend them in the order above; C1 first,
tonight if the gate is clean.

## 5. Do not do

- Do not tune TOMATO/STRAWBERRY *shares* (`_choose_crops_legacy_share`) — the
  value model is the live path; fix its math.
- Do not re-submit H2's flag as-is; build C2 on the install path.
- Do not build N2 (wheat floor) or routing/movement variants — evidence above.
- Do not judge H4 before 20 eps; 663.1 at 3 eps is validation noise.
