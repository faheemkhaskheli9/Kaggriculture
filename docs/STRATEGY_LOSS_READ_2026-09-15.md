# Loss read 2026-09-15 — H3/H4 at 40/38 eps; the herd-install bug fires in 100% of games

Read of every lost game of the two latest subs (`56233524` H3, `56235916` H4),
78 episodes total, pulled 2026-09-15 with `download_episodes.py --submissions
56233524 56235916` + `tools/ladder_analyze.py` + `tools/trace_cashflow.py` +
three scratch scans (crop mix / herd install / crew actions). Supersedes the
queue in `docs/STRATEGY_LOSS_READ_2026-09-14.md` §4; its C1 analysis stands.

## 1. Ladder state (readback)

| sub | flag | eps | W-T-L | score-rate | vs animal_factory | ladder | verdict |
|---|---|---|---|---|---|---|---|
| `56233524` | H3 `ENABLE_CROP_FERTILIZE` | 40 | 20-0-20 | 50% | 16-16 = 50% | 638.6 | **HOLD, not promotable** — yesterday's 54.2% at 27 eps regressed to 50%; misses the guardrail (N1 `56199529` = 54.2%, 30 eps). Keep OFF. |
| `56235916` | H4 `ENABLE_CROSS_ZONE_WATER` | 38 | 19-1-18 | 51% | 16-16 = 50% | 608.8 | **not promotable** — weeds29 fell 18 → 14 (the intended mechanism moved) but win-rate did not. Keep OFF. |

0 `agent()` exceptions, 0 over-budget steps in both. Both are noise-level vs
the board-best; neither flag is worth a merge. The loss mix is the same for
both subs (H3: 12 `WEED_PILEUP` + 8 `OTHER`; H4: 11 + 5 + 2 `CLOSE/NOISE`), so
the 38 losses below are analysed as one pool.

## 2. What the 38 losses are

Splits over all 78 games (both subs), our seat:

| split | n | W-L | win% | our final $ (median) |
|---|---|---|---|---|
| STRAWBERRY-dominant at d15 (TOMATO < 15 tiles) | 49 | 31-17 | 63% | 87.4k |
| mixed (15 ≤ TOMATO < 40) | 11 | 2-9 | 18% | 49.4k |
| TOMATO-dominant (≥ 40) | 18 | 6-12 | 33% | 45.8k |
| opponent herd ≤ 9 at d12 | 31 | 24-6 | 77% | 76.3k |
| opponent herd 10-13 at d12 | 27 | 8-19 | 30% | 75.8k |
| opponent herd ≥ 14 at d12 | 20 | 7-13 | 35% | 76.3k |
| STRAWBERRY-dominant **and** opponent herd ≥ 12 | 23 | 11-12 | 48% | 84.7k |

Means, wins vs losses:

| | W (39) | L (38) |
|---|---|---|
| our herd d12 / max | 6.7 / 8.1 | 6.6 / 7.5 |
| opponent herd d12 / max | 9.5 / 12.2 | 12.3 / 13.7 |
| our cash d15 → d20 | 12.7k → 21.1k (+8.4k) | 11.7k → 18.9k (+7.2k) |
| opponent cash d15 → d20 | 8.0k → 21.4k (+13.3k) | 13.0k → 34.6k (**+21.6k**) |
| our lowest cash d12-d18 (idle floor) | 11.4k | 10.5k |
| opponent lowest cash d12-d18 | 4.1k | 6.4k |

The 38 losses are three families:

1. **Tomato flip, 16 losses** (finals 23-55k): `109112393 109162767 109201513
   108983969 108978795 109001911 108990345 108958556 108951028 108955220
   108948804 108946279 108963758 109038240 108952108 109235720`. TOMATO ≥ 130
   units sold, STRAWBERRY ≤ 120; cash flat 10-20k from d15 to d25. Same
   self-collapse as yesterday's C1 — 29/78 games (37%) go tomato-heavy and win
   8-21 (28%) against 31-17 (63%) for the rest.
2. **Out-scaled by a 12-29-animal opponent, 17 losses** (our finals 75-102k vs
   their 87-135k): `108981884 108999819 108982937 109117101 109010353
   108986079 108997712 108992465 109217291 109119973 109006623 109275420
   108960344 109098643 108966895 108944571 108956500 109051439 108998492
   108954170`. Same 55-60 tiles as the opponent, same d15 cash; they add
   +4-5k/day from d16, we add +1-2k/day until d19.
3. **Close, < $5k margin, 5 losses**: `108989361 108941342 109001911 108998492
   108990345` — flipped by any of the fixes below.

Day-by-day of `109098643` (STRAWBERRY-dominant loss, 102k vs 132k, opponent
15 animals from d15): identical cash at d11 (13.8k vs 1.2k — we are *ahead*
after the melon harvest), then we sit at 11.6-17.9k for seven days with **1
COW + 2 GOOSE + 1 SHEEP in the shed and 2 empty structures on the field**,
while the opponent spends down to 4-8k building to 15 animals by d15 and
out-earns us 2:1 from d16 (MILK 12-21 + WOOL 4-11 + FERTILIZER 5-10 a day).

## 3. Root causes (ranked; C2 has moved to #1)

### C2 — herd install bug: 4 of 11 bought animals never placed, in 78 of 78 games

Scan of all 78 games (`private.shed` + our actions):

| | mean |
|---|---|
| `BUY_ANIMAL` units per game | 11.4 (4 on d0, 1-3 on d9, 4-6 on d11) |
| max animals ever placed | 7.8 (7.5 in losses) |
| animals in the shed at d5 / d9 / d14 / d17 / d29 | 1.0 / 1.0 / 4.1 / 3.8 / 3.5 |
| structures built vs occupied at d14 | 9.3 vs 7.3 (**2 empty**), 10 empty tiles |
| crew `PICKUP <animal>` actions per game | **81.3** |
| crew `PLACE` actions per game | 7.8 |
| `PLACE` by day | d0-1: 234, d9-12: 312, d13-29: 63 |

Every game: the 4th day-0 COW sits in the shed until day 9, and 3-5 of the
animals bought on d9/d11 never leave it. The crew *does* pick them up — ~3
times a day, mostly hours 13-23 — but in `animal_crew_actions()` the
shed→structure path sits **below** the opportunistic `goals` loop
(feed / harvest / `COLLECT_FERTILIZER` / care), which is never empty because
every placed animal drops a fertilizer every day. So the hand that just did
`PICKUP COW` is re-targeted to a goal on the next turn, walks around with the
cow, and the end-of-day drop puts it back in the shed. The
carried-animal-first branch exists but is gated behind the retired H2 flag
(`ENABLE_ANIMAL_CARRY_GUARD`), and after day 17 `animal_targets()` returns
placed-only counts, so `animal_tiles()` stops reserving build spots and the
shed animals can never be installed at all.

Cost per game: 4 animals × 15-20 days × 1 FERTILIZER/day (base $100) ≈ $6k,
plus their MILK/EGG/WOOL ≈ $3-4k, plus ~80 wasted crew actions and shed walks
→ **≈ $8-10k/game, every game**. 12 of the 38 losses are inside $10k. It also
explains why we plateau at 8 animals against opponents' 12-15 (the strongest
single loss predictor above) even though we *paid* for 11.

Why H2 (`56199353`, retired at 45% / n=20) did not show this: it bundled (a)
carried-first placement with (b) hour-gated pickups and (c) shed-cap buy
refusals, the n=20 read is inside noise, and (a) alone leaves the post-day-17
reservation freeze and the day-0 4th cow untouched.

### C1 — crop-value model ignores lifespan: the tomato flip

Unchanged from `STRATEGY_LOSS_READ_2026-09-14.md` §3 C1: `_crop_tile_value()`
(`main.py:948-975`) credits an ongoing crop one unit per interval for the whole
remaining season; the engine gives exactly `MAX_YIELD` = 4 ticks. 37% of games
flip to tomato and win 28%. Fix is the same math change; evidence now 78 games.

### C3 — idle cash d12-d18 and herd size (after C2, economy — not yet)

We hold a $10.9k floor for a week while the opponent runs at $4-6k. With C2
fixed the 11 bought animals are installed by ~d13; the remaining gap to the
12-15 the winners run is the herd target (`COW 5 / GOOSE 5 / SHEEP 1`), and
we never sell WOOL. Raise to 14 only after C2's read shows placed == bought.

### C4 — H3 / H4

Both flat at 40/38 eps. H3's fertilizer supply comes from the herd, so it
should be re-measured **on top of C2** (11 animals → +4 FERTILIZER/day) rather
than merged now. H4 lowered weeds29 but not the win-rate: `WEED_PILEUP` is a
label of the day-27/28 hand cut, not a cause (wins carry weeds29 17 too).

## 4. Queue (one `ENABLE_*` flag per submission; judge at ≥ 20 eps, never revert before 15)

| # | change | file | mechanism | expected | gate / judge |
|---|---|---|---|---|---|
| **1 — C2** | `ENABLE_HERD_INSTALL_FIRST` | new `agents/main_v43_herdinstall.py` | In `animal_crew_actions()`: (a) a unit carrying an animal `PLACE`s it into a matching empty structure — else `BUILD_*` on the nearest reserved free tile — **before** the `goals` loop, unconditional on `ENABLE_ANIMAL_CARRY_GUARD`; (b) while the shed holds an animal and a matching empty structure or build spot exists, the crew hand nearest the shed is assigned `PICKUP → PLACE` ahead of `goals` (one hand per turn; only if walk + place fits before hour 23, else it stays on goals); (c) `animal_targets()` after day 17 returns placed **+ shed** counts so `animal_tiles()` keeps a reserved spot per paid-for animal (buying still stops: `cur = have + shed ≥ want`). OFF path byte-identical. | placed herd 7.8 → 11 by ~d13; shed animals at d17 3.8 → 0; ~80 crew actions/game freed; +$8-10k/game; flips the 12 losses inside $10k → score-rate ~50% → ~60% | unit tests (`tests/test_herd_install_first.py`): shed animal + empty structure + fertilizer goals → crew picks `PICKUP`/`PLACE`; carried animal → `PLACE` first; day-20 targets include shed. `probe_game.py`: `BUY_ANIMAL` units == max placed by d14. `compete.py --games 96 --baseline main.py`: 0 errors, no `animal_factory` regression. Ladder: avg animals ≥ 10.5 (from 7.8), shed animals at d17 = 0 in ≥ 18 of 20, af ≥ 54.2%. |
| **2 — C1** | `ENABLE_CROP_VALUE_LIFESPAN` | `agents/main_v44_croplifespan.py` (on the C2 parent once C2 is gated; else on `main.py`) | `_crop_tile_value` ongoing branch: `ticks = min(MAX_YIELD[crop], (remaining - fy)//interval + 1)`; `occupancy = min(remaining, fy + (ticks-1)*interval + 1)`; `(price*ticks - cost)/occupancy`. | TOMATO-heavy share 37% → ~0%; those games 28% → ~63% → +13pp overall; median $ +15-20k | unit test: d10 base prices → STRAWBERRY over TOMATO; d15 → TOMATO allowed. 96-pair gate. Ladder: TOMATO ≥ 15 at d15 in ≤ 2 of first 20; af ≥ 54.2%. |
| 3 | C2 + C1 union | `agents/main_v45_c2c1.py` | promotion merge of two judged flags, not a bundle | | standard |
| 4 — C3 | herd target 11 → 14 (`COW 6 / GOOSE 5 / SHEEP 3`) | after C2's read only | | +$3-5k/game | only if C2's read shows placed == bought |
| 5 | H3 re-read on top of C2 | | fertilizer supply 8 → 11 animals | | af ≥ guardrail |

Why C2 before C1: C2 fires in 100% of games, is a pure mechanical bug (the
project rule: mechanical fixes are the only class that has ever moved the
ladder), and is **locally provable** (placed == bought is deterministic in
`probe_game.py`); C1 is a crop-choice change the local pool cannot gate.
Both are atomic and can go out today as two attributable subs (0 of 5 used
2026-09-15 UTC): C2 now, C1 ~12h later on whichever parent is current.

## 5. Do not do

- Do not re-submit H2 as-is; C2 is (a) + the two root fixes, without (b)/(c).
- Do not promote H3 or H4 on the current reads; leave both hunks dormant.
- Do not tune weeds (sweeps), wheat floor, TOMATO/STRAWBERRY shares, or
  routing — no loss in this pool traces to them.
- Do not raise the herd target before C2 lands: buying more animals into a
  shed we never empty only sinks more cash.
