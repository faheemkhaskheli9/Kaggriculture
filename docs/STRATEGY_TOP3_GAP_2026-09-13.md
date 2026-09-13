# Why we lose, what the top 3 do instead, and the strategy to close it (2026-09-13)

Evidence: 24 real-ladder episodes of the board-best sub `56184777` (our seat +
the opponent seat, day-by-day at hour 0), the 5-game-per-leader top-3 replay set
in `research/top3_20260912/` (Majkel1337 3198, ymg_aq 3080, Artem 3051), and the
installed engine. Numbers below are means unless stated. Analysis script:
scratchpad `traj.py` (mirrors `research/top3_20260912/leader_days.json`).

## 1. The loss mechanism in one table

| day | our money | opp money (same games) | top-3 money | our animals | opp | top-3 | our WHEAT tiles | our MELON tiles | top-3 MELON |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 387 | 366 | 6-32 | 3.0 | 2.9 | 4-6 | 11.7 | 0 | 6-12 |
| 5 | 341 | 429 | 209-459 | 3.0 | 3.5 | 5-6 | 11.2 | 0 | 12 |
| 10 | 1,490 | 1,267 | 669-2,925 | 6.0 | 6.8 | 9-16 | 0 | 5 | 12 |
| 12 | 928 | 5,907 | 7,522-17,500 | 6.2 | 9.0 | 12-18 | 0 | 5 | 0-11 |
| 15 | 794 | 9,577 | 16,627-25,173 | 7.1 | 11.7 | 14-19 | 0 | 5 | 0-12 |
| 20 | 10,742 | 23,914 | 50,664-54,597 | 7.9 | 13.0 | 14-22 | 5 | 0 | 0-2 |
| 29 | 62,968 | 71,595 | 88,984-98,297 | 7.8 | 12.9 | 9-18 | 3.5 | 0 | 0 |

We are level with everyone at day 10 and then **flat from day 10 to day 17**
(money 1,490 → 1,117 → 928 → 688 → 1,074 → 794 → 2,192 → 2,773) while the
ladder opponent goes 1,267 → 9,577 and the leaders 1,205 → 25,173. Our late
engine is actually strong (day 20→29: +$52k, 42 strawberry tiles) but it starts
five days late, and in the 13 losses the opponent's day-10-to-20 lead never
closes. Loss causes from `tools/ladder_analyze.py`: CRATER 9, WEED_PILEUP 3,
noise 1 — the "weed" losses are the same crater (weeds only appear after day
26 when the crew is cut, before that we sit at ≤5 weeds like the opponents).

## 2. Root causes, ranked by $ in the crater window

1. **No day-0 melon batch (~$14-17k missing at day 11-12).** Artem and
   Majkel plant exactly 12 MELON on day 0 (Artem: 12 melon + 7 wheat; Majkel
   12 by day 3); the *average ladder opponent* buys ~20 MELON seeds on day 0
   and holds 8-11 melon tiles through day 10. Engine: one-time crop, +1
   unit per watered day at ages 6-12, cap 6, decays from age 13. 12 tiles ×
   6 = 72 units sold on day 10-12 at the $228-266 the opponents realise
   (nobody has dumped yet) ≈ $14-17k, landing exactly in our crater. Artem's
   money goes 669 → 16,057 between day 10 and 11 on this alone. Our cap is 5
   melons, planted day 9-10 and sold from day 20 into the post-dump curve
   ($196 → $57). Per tile by day 12: melon ~$1,400, carrot ~$315, wheat ~$230,
   tomato ~$220, strawberry ~$220. Seed cost is the same as the tomato+carrot
   we plant instead.
2. **Field goes dark days 9-19.** On day 9 we replant the whole field into
   21 STRAWBERRY + 9 MELON + 3 TOMATO and hold **0 WHEAT tiles from day 9 to
   day 16**. Strawberry planted day 9-13 first ticks on day 19-23, so the
   field produces nothing for ten days and we buy all feed wheat at $29
   instead of growing it at $10/6 units. The leaders keep 15-28 wheat tiles
   all season (top-3 wheat sales 430-460 units, purchases 166-216).
3. **Herd 8 vs 13-22, and it arrives late.** Leaders have 4-6 animals at
   day 1 (2-3 cows + 2-3 sheep, $1,800-2,700 of the $3,000) and 14-18 by day
   12; free fertilizer is $95/animal/day from day 1, wool from day 6, milk
   from day 8. We have 3 cows at day 1, 6 at day 10, 7.9 at day 19 and zero
   sheep. H1 (`ENABLE_SHED_STAGING`, promoted today) stops the shed discarding
   purchased animals; H2 (`ENABLE_ANIMAL_CARRY_GUARD`, submitted today as
   `56199353`) fixes the stranded-last-animal path that kept the realised herd
   at 8 (local: d15 6.4 → 8.7, d29 7.2 → 10.1).
4. **No FERTILIZE.** Leaders fertilize 135-198×/game and harvest 7.2-7.4
   strawberries per tile vs our 4. H3 (`ENABLE_CROP_FERTILIZE`,
   `agents/main_v39_fertilize.py`) is built and queued.
5. **Movement 64% vs 43-48%.** Real, but three routing candidates were flat
   or negative on the ladder (`movement-routing` family benched). Not a lever
   until a materially different mechanism exists.
6. **Labour spend.** We pay 10 hands from day 4 ($143/day) with 17-40 plants;
   Majkel runs 6 until day 6 and 11 from day 10 (total $4.9k vs our ~$7k).
   Second-order; do not touch while 1-4 are open.

What is *not* the problem: land (all three leaders and we end on exactly 3
quadrants; none buys the $4k fourth), the price model (`price_at` matches the
engine on 97,200 recorded prices), silent exceptions (0/26, 0/27 in today's
log sweeps), and weeds before day 26.

## 3. Strategy — the ranked queue of atomic, flagged changes

One `ENABLE_*` flag per submission, judged at ≥20 episodes on the
animal_factory score-rate, exactly as before. Order = $ in the crater window
÷ risk.

| # | flag / file | mechanism | expected effect | status |
|---|---|---|---|---|
| H1 | `ENABLE_SHED_STAGING` | late-day delivery + overflow sell-down | stop ~$6.3k/game + purchased animals discarded | **PROMOTED** (`56195143`: 26 eps, 58% overall, af 9-0-8 52.9% vs 44.4%, ladder 600.9) |
| H2 | `ENABLE_ANIMAL_CARRY_GUARD` (`agents/main_v38_carryguard.py`) | carry-aware animal install, deadline-gated pickup, no buy into a full shed | realised herd 8 → 10+ | **SUBMITTED** `56199353` 2026-09-13 04:57 UTC |
| N1 | `ENABLE_OPENING_MELON` (`agents/main_v40_openingmelon.py`) | 12 MELON on days 0-2 (nearest tiles), tomato share 0 those days, seed target capped at the batch, melon sold with the staple floor (0.45×base, 12/turn) through day 16 | +$13-17k at day 11-12; d15 cash ~$1k → ~$14k (probe: 1,445 → 15,522 d10→d11) | **SUBMITTED** `56199529` 2026-09-13 05:08 UTC (§4) |
| H3 | `ENABLE_CROP_FERTILIZE` (`agents/main_v39_fertilize.py`) | value-gated FERTILIZE on ongoing crops, pickup at dawn, hold fert demand back from the sell | strawberry 4 → ~7 units/tile ≈ +$10-16k/game | built, next batch |
| N2 | `ENABLE_MIDGAME_WHEAT_FLOOR` (not built) | keep ≥10-12 WHEAT tiles from day 7 to 22 (skip the day-9 100% slow-crop replant), so feed is grown not bought and cash keeps flowing | closes the day 9-19 production hole; −$1.5-2k feed purchases | after N1/H3 are read |
| N3 | `ENABLE_OPENING_SHEEP` (not built) | day-0 herd 2 COW + 2 SHEEP instead of 3 COW; wool day 6/9 funds land 2 the way the leaders do it | +$400 day 6, +2 fertilizer/day | `herd-economy` family — build only after H2's read |
| N4 | hire ramp 6→8→10 tied to plants+animals (not built) | matches the leaders' crew curve | −$700 days 4-9 | last |

Do not revisit: general CARE task, opportunistic fertilize courier on the old
base, sticky targets, movement thrift (all reverted on evidence, see
`knowledge-base/06-strategy-playbook.md` §6 and `experiments/LEDGER.md`).

## 4. N1 — OPENING_MELON gate record

- 13/13 engine-style unit tests (`tests/test_opening_melon.py`).
- OFF path: 23/23 paired games byte-identical to the pre-patch bytes
  (`agents/main_v37_shedstaging.py`), +0 margin everywhere.
- ON vs `main.py`, 24 pairs vs `bot_animalfactory_v2` (`--pick-seed 4002`):
  24-0-0 both arms (saturated), margin +$17,519/pair, **day-10 cash
  +$13,158/pair**, plant→weed −2.7, escapes −0.2, 0 errors.
- ON vs `main.py`, 96 pairs full pool with animal_factory ×3
  (`--pick-seed 4003`): **paired score delta +10.4%, 90% CI [+3.1%, +17.7%]**
  (does not cross 0, the first lever in the ledger to clear that),
  improved/same/regressed 14/78/4 with all four regressions in lineage
  self-play (v19/v28/v29/v35) and zero external-bot regressions, margin
  +$13,855/pair, day-10 cash +$12,713/pair, 0 errors.
- **Submitted 2026-09-13 05:08 UTC as `56199529`** (tracked pair with H2
  `56199353`).
- Single probe game vs `bot_animalfactory_v2` (seed 123456789): 12 melons
  planted day 0, harvested day 10, money 1,445 (d10) → 15,522 (d11), final
  92,516 vs 35,085.

Judge on the ladder at ≥20 episodes: guardrail animal_factory score-rate ≥
H1's 52.9% (n=17); primary read = our money at day 12/15 in `traj.py` (expect
≥ $10k from ~$1k) and the CRATER count in `ladder_analyze.py` losses.

## 5. What "winning" looks like after the queue lands

Target trajectory (leader envelope): 12 melons + wheat + 3-4 animals on day
0; land 2 by day 3-6; melon cash day 11-12 → land 3 + herd to 13-15 by day
13; 40 strawberry tiles planted by day 12 and fertilized twice; wheat line
never below ~10 tiles; sell every product every turn; final day liquidation
(already in). That is the shape of every top-3 game in the sample and of the
opponents that beat us; none of it requires a new tool, a new bot, or routing.
