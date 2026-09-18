# Win-rate plan 2026-09-18 — read of all 1,365 public ladder games

Source: every PUBLIC episode in `episodes/index.csv` (49 subs, 2026-09-01 →
09-18), reduced by session scratch scripts `allgames.py` (one row per game:
result, opponent, money d5-29, plants/animals/weeds/quads/hands both seats, crop
mix d20, shop-draw days) and `curgames.py` (current lineage only: 2-day curves
both seats + our revenue by item at the pre-order price). "Current lineage" =
the 356 games since 2026-09-15 (v45 `56259132` onward). 0 of 1,365 games ended
with a non-`DONE` status on either seat.

## 1. Where we stand

| era | games | W-L | my median | opp median |
|---|---|---|---|---|
| 09-01..05 | 382 | 164-218 (43%) | 40.1k | 45.4k |
| 09-06..10 | 342 | 167-175 (49%) | 68.3k | 63.2k |
| 09-11..14 | 285 | 135-150 (47%) | 71.4k | 68.9k |
| 09-15..16 | 178 | 94-84 (53%) | 79.1k | 77.9k |
| 09-17..18 | 178 | 92-86 (52%) | 86.2k | 84.1k |

Own money doubled; win-rate sits at ~52% because matchmaking feeds us
opponents of our own rating. Rating only moves when the *money distribution*
moves: inside the current lineage the win-rate by our own final-money quartile
is 33% / 46% / 58% / 71% (<64k / 64-83k / 83-98k / >98k). **Target: +10k median
own money ≈ +6-8pp win-rate against today's pool.**

## 2. What separates wins from losses (356 games, 186-170)

**A. Our farm is identical in wins and losses.** Plants d15 58.1 vs 57.5,
animals 11.7 vs 11.6, hands 12.0 vs 12.0, quads 3.0 vs 3.0, weeds d20 0.7 vs
1.0. No own-side build feature separates W from L. Seat: 51% / 54%.

**B. The opponent's strength decides the game.** Win-rate by opponent final
money quartile: 94% (<59k) / 70% (59-79k) / 38% (79-100k) / **8% (>100k, 7-83)**.
Losses are not close: 28 within 5%, 39 at 5-15%, 48 at 15-30%, 55 above 30% —
there is no pool of coin-flip losses to convert with endgame polish.

**C. The opponents who beat us build the herd 3-4 days earlier and 3 animals
bigger, with fewer hands and fewer plants.** Opponents finishing ≥100k (n=91)
vs us, at hour 12:

| day | our $ / animals / plants / hands | top-opp $ / animals / plants / hands |
|---|---|---|
| 6 | 0.4k / 3.4 / 25 / 7.8 | 0.8k / 5.5 / 19 / 6.3 |
| 8 | 0.7k / 3.9 / 21 / 10.0 | 0.8k / **8.1** / 28 / 8.3 |
| 10 | 1.0k / 6.4 / 31 / 10.0 | 3.0k / **10.8** / 32 / 10.5 |
| 14 | 10.3k / 11.5 / 56 / 12.0 | 15.2k / 14.2 / 50 / 10.3 |
| 20 | 25.7k / 11.8 / 56 / 12.0 | 46.3k / 14.7 / 50 / 11.7 |
| 28 | 73.1k / 11.8 / 19 / 8.2 | 105.4k / 14.7 / 27 / 10.8 |

We sit at 3-4 animals through day 8 while buying quadrant 2 (day 5-6) and
hands 8-10; they buy animals first. Win-rate by *opponent* animals at d8:
85% (<3) / 69% (3-5) / 48% (6-8) / 35% (9-11). Phase gains in losses: d10-15
−0.9k vs +12.2k, d15-20 +13.6k vs +24.6k, d20-25 +27.3k vs +32.0k. We lead
91% of games at d10 (cash we have not yet invested) and trail 56% at d15;
leading at d20 wins 86%, trailing at d25 wins 16%. The game is lost d8-20.

**D. Our own variance is the STRAWBERRY and MILK price we realize.** Top vs
bottom own-money quartile: STR revenue 60.6k vs 20.2k (realized 237 vs 114,
units 255 vs 177), MILK 48.4k vs 12.7k (230 vs 75, units 210 vs 170); every
other line is flat. Win-rate by realized STR price: 26% (<100) / 41% / 40% /
70% (220-260) / 88% (>260). Both crashed (STR <160 and MILK <150): 67 games,
39%, median 53k. Neither: 142 games, 64%, 99k.

**E. We plant 46-51 STR tiles whatever the board says.** No SMOOTHIE/ICE_CREAM
shop by d12 (125 games): STR 129-148, our median 64k vs 92k with one. Opponent
STR tiles d20 ≥25 (211 games = 59%): 36-42% win — and our STR count does not
move (46 vs 51). `knowledge-base/03` still says "STRAWBERRY never ended below
185"; on the 09-15+ ladder 105 of 356 games realize <160. S1 (shop-demand crop
value, `56282756`) did not cut the crashes, so this is a *cap* question, not a
valuation one.

**F. The shop draw moves both players together.** YARN_STORE by d9 45% win
(vs 57%), PIZZA 44% (vs 56%), SMOOTHIE 60%, PET_CAFE 60%. We under-use yarn and
pizza draws relative to the field; sheep-on-yarn and cow-on-milk already
address the first.

## 3. Plan — ranked, one atomic `ENABLE_*` change per sub

Order is by evidence × size. Every item: new `agents/main_vNN_*.py`, flag OFF on
`main.py`, paired 96-game gate (0 err, no af regression), judge at ≥20 eps
against the concurrent floor resubmit. Deadline 09-30 → about 20 judged reads.

| # | change | evidence | local size | kill if |
|---|---|---|---|---|
| 0 | **In flight:** judge LATE-CREW `56331079`; submit WATER-ON-NEED v62 (09-19 batch 1) | §C d28 hands 8.2 vs 10.8; 407 no-value waters/game | +0.6k; +5.6k | af < floor at ≥20 eps |
| 1 | **HERD-BEFORE-LAND**: days 3-9, hold `BUY_LAND` (quadrant 2) and hands 9-10 until the placed+pending herd ≥ 6 | §C: 8.1 vs 3.9 animals at d8; the only own-side lever the 356-game table points at | est. +5-8k (11 animals × 3.5 days earlier) | gate own money < 0 or d12 plants < 40 |
| 2 | **HERD-14 re-gate over v62**: rejected twice because the herd "eats the crew"; v62 frees ~230 hand-actions/game (PASS +201) | §C: 14.7 vs 11.8 animals from d14 | HERD-14 was −1.6k on the old parent | own money ≤ 0 over v62 |
| 3 | **FERT-TICK water re-tier over v62**: 26 fertilized tick nights/game resolve unwatered with idle labour | fert-water gap read (09-18) | 26 × ~$190 ≈ +3-5k | animal harvest displaced (v59 failure mode) |
| 4 | **STR-CAP on a dry board**: from d12, when no STR-demanding shop is open and STR price < base, cap new STR plantings (remainder to the chooser's next crop) | §D/§E: 125 games at STR 129-148 | unknown; local pool rarely crashes STR | STR units −20% without price gain |
| 5 | **Late STR decay**: 12-14 units/game still decay after `max_lifespan_step` | spent-no-water read | ≈ +2.5k | — |

Sequencing: 0 → 1 → 2 (2 only after v62 is judged, since it depends on the
freed labour) → 3 → 4 → 5. Items 1 and 3 touch disjoint code (market orders vs
`build_tasks` water tier) and can share a 2-sub batch.

Item 1 teardown before building (no code yet): trace days 3-9 on 20 current
games — cash, `reserve`, the E3 gate term `cost + 150*placed`, and the order
`BUY_LAND` / `HIRE` / `BUY_ANIMAL` clear in. Prior art to respect:
ANIMAL-PACING (`56055430`, flat) and the per-day herd cap *throttled* early
buys and failed; HERD-RESERVE-EXEMPT (`56126876`, flat) loosened the reserve
but the herd still did not move (8.0 → 9.0) — i.e. the blocker was cash already
spent on land/hands, which is exactly what item 1 reorders. Lever B (Q3 gate)
regressed: item 1 must not touch quadrant 3.

## 4. What this read closes

- Endgame/close-loss polish: 28 of 170 losses are within 5%; not where the
  rating is.
- Seat, weeds, hands, quadrant count: no signal.
- Reading opponent identity: 331 unique opponents in 356 games, none seen ≥4
  times — no per-opponent adaptation is possible.
- Exceptions: 0 non-`DONE` statuses in 1,365 games.

## 5. Judge metrics added by this read

Beyond af win-rate vs the concurrent floor: animals at d8 / d10 (target ≥6 /
≥9), money at d16 (parent 13.0k; wins peak in the 12-16k band), d15-20 gain
(parent 13.6-14.8k vs 24.6k for winning opponents), realized STR and MILK price.
