# 06 — Strategy playbook

Evidence-tagged. Sources: 30+ downloaded ladder replays, `test.py` paired
benchmarks, and env-math re-derivation. Files behind this: `PLAN_3000.md`,
`PLAN_3000_v4.md`, `PLAN_300K.md`, `SCORE_IMPROVEMENT_PLAN.md`, `WINNING_PLAN.md`,
`STRATEGY.md`, and the project memory notes.

---

## 0. What score is actually reachable

Reward is `farm["money"]` at step 718. Two ceilings — **demand** and **supply** —
and **supply (one farm's production) is the binding one.**

- **Demand:** combined season town consumption (both players) ≈ WHEAT 525,
  STRAWBERRY 425, CARROT 325, MILK 325, TOMATO 230, WOOL 230, EGG 230, MELON 30.
  As sole supplier at base that's ~$220k of fillable demand, ~$280–340k with
  scarcity uplift.
- **Supply:** 100 tiles, ~24 productive days. Even with **CARE fully exploited**
  (~3× animal yield) and **FERTILIZE on every in-window ongoing crop** (~2×),
  near-perfect solo play tops out around **$150–250k vs a passive opponent**, and
  **~$90–160k plus a win vs an opponent who also fills their field** (shared
  supply collapses the scarcity prices).
- **300k is the extreme top edge of the env, not a reliable target.** Treat
  **~150k as the "playing well" floor** and 300k as a ceiling to chase only when
  the matchup is favourable. Since rating is win/loss only, a 150k-capable agent
  is already dominant.
- Pre-work agents scored ~55–60k in local benchmarks. `main.py` (v5) lands
  ~60k local / and the real earned ladder progression is **333 → 477**.

---

## 1. The core failure modes (ranked by how much they cost)

1. **Movement is the scarce resource.** The 600-score agent spent **~76%** of
   all unit-actions moving because it recomputed a global nearest-task
   assignment every turn, so hands oscillated across the whole farm. Fix =
   persistent per-unit zones. `main.py` got this to ~58%, then stalled at ~65%
   — most of the remainder is *legitimate* dawn commute (shed → a large field),
   not oscillation.
2. **Linear growth vs the winners' exponential growth.** We are level or ahead
   through ~day 12, then grow linearly while winners compound from day 12–20
   (first animal cohort + first big rotation mature and snowball). Our field is
   the same ~30 tiles on day 25 as on day 5.
3. **Under-selling 2–4×.** Winners sell a steady **30–90 units/day from ~day 10**
   plus a **130–160-unit terminal dump on day 28–29**. Our Gen A/B sold ~11–20
   units/day. Cause is mostly throughput (fewer productive tiles, weeds), some
   over-holding, and leaving `SELL` slots empty mid-game.
4. **Weed backlog.** 15–27 weed tiles by day 29 in Gen A/B games — up to half the
   field unfarmed late. Coverage is short at scale.
5. **Terminal inventory dumped unsold.** MELON 10, WHEAT 3–7 seen unsold at
   step 718 — pure lost score in coin-flip games.
6. **Idle capital.** Sitting at $4k–9k mid-game with no land/animal buy queued.
7. **Carrot overproduction.** ~12 carrots/game sold at $23–48 — the worst
   $/tile-day crop, given a third of the field.
8. **Silent exceptions.** The top-level try/except makes a crash look like a bad
   strategy. Rule it out first on any flat/lost submitted episode.

---

## 2. Opponent archetypes (ladder)

Every downloaded **win** was against a passive opponent (did nothing / 1–3 wheat
all game / a stalled melon bot / a single-unit farmer). Every **loss** was
against one of four active strategies:

| Archetype | Behaviour | Their coins / ours |
|---|---|---|
| **Animal + fertilizer factory** | 6–39 animals by ~day 10; sell FERTILIZER (280–460 u), MILK, WOOL, EGG steadily; 3–4 quadrants; wheat only as feed; CARE 200–830×/game | 38k–74k / 13k–29k |
| **Wheat flood** | max wheat tiles; `SELL WHEAT` 60–90 **every turn from day 0**; 600–1600 wheat/season; terminal spike day 28–29; ~10 hands | 35k–111k / 15k–30k |
| **Melon monoculture** | ~19 melon on a tight replant loop; one crop; sell in ~12-unit batches | 30k–37k / 12k–23k |
| **Strawberry / premium concentration** | 10–17 strawberry planted once and held; minimal labour; ride the $250–330 price | 13k–23k / 12k–14k (our *closest* losses) |

**Implication:** a monoculture beats a *weak* opponent but collapses against a
diversified animal+premium agent (verified locally — forcing `main.py`'s engine
to wheat-only loses ~12k vs 63k). The ladder floods that scored 60–110k did it
against weak or mirror opposition. Local reproductions live in `bots/`
(`bot_wheatflood`, `bot_animalfarm`, `bot_melonmono`, `bot_premium`).

---

## 3. Phase plan (current best understanding)

**Days 0–6 — liquidity race, not a value race.**
Front-load **WHEAT + CARROT** (first yield day 2) so cash flows from ~day 4.
`main.py`'s `early` branch: WHEAT .50 / CARROT .28 / TOMATO .16 /
STRAWBERRY 0→.12 / MELON 0. The old mix stalled at 1 quadrant and $206 cash
until ~day 15 because week-1 plantings were all slow crops (tomato/straw/melon,
first yield day 8–10). Hire cheap hands early (fib is ~free for the first 6).

**Days 4–11 — build the bigger game.**
Buy quadrant 2 by day 3–4, quadrant 3 by day 6–8, quadrant **4 ($4k) by
day 9–11** — each gated on `fill ≥ ~0.5–0.6` and a cash cushion. The $4k
quadrant is +25 tiles and pays back in ~2 days *if bought before ~day 14 and you
have the hands to work it*; a trap otherwise. Place animals so they are
**producing by day 8–12** (buy 2/turn in the dawn window days 1–4, pre-build
structures) — ours historically only produced from ~day 20 because of a money
gate + one-buy-per-turn.

**Days 6–24 — run the crew and sell to production.**
Hold ~12–13 hands (the fib knee is 13–14; 16 costs ~$2.5k/day). Target movement
< 30%. Sell **every turn** from ~day 6 for every product above a thin feed/seed
reserve; fill all 10 order slots; never return a short market list while the
shed is non-trivial. Cadence target ≥ 35 units/day from day 10.

**Days 25–29 — endgame precision (turns the coin-flips).**
Reward locks at step 718 and day-29 end-of-day never runs, so day-29 ticks bank
nothing and unit inventory not in the shed by hour 22 is lost. Stop
watering/fertilizing/CARE-ing anything whose only remaining yield is the day-29
night tick; redirect that labour to harvest + `DROP` + `SELL`. Every carrying
unit must reach a shed tile; the shed must be **sold to $0** (floor $1 is still
positive). Winners spike 130–160 units on day 28.

---

## 4. Crop / animal mix (for the monopolist envelope)

- **STRAWBERRY ~28–32% of tiles** — safest premium, never crashed in 30 games,
  ongoing. Plant-by ~day 13 (needs to fire its 4 ticks).
- **TOMATO ~30%**, held into ~day 20 — `hinge` scarcity ceiling ran to $380+.
  Plant-by ~day 18–20.
- **WHEAT ~20%** — feed + a volume line that never crashes (`log` glut side
  floors ~$19). In an animal-vs-animal matchup, allow a wheat-flood sub-mode
  (~50% of tiles, sell to the cap every turn).
- **MELON ≤ 5 tiles** — `sq` glut crash; scarcity side-bet only.
- **CARROT ~0–4 tiles** — only on live PET_CAFE / FARMERS_MARKET demand and late
  for quick cash. (Exception: it *is* worth a big week-1 share for liquidity;
  a day-24 carrot on the same tile still beats a day-24 wheat — measured.)
- **Animals: COW 9–15 / GOOSE 2–4 / SHEEP 1–4**, all placed by ~day 10, freeze
  new purchases after ~day 17 (a fresh cow needs ~10 days to break even).
  **Opponent-conditional:** if the opponent shows ≥ 4 animals by day 7, drop to
  COW 3 / GOOSE 3 / SHEEP 0 — keep only the free-fertilizer + egg value and put
  the field into wheat + strawberry, because milk/wool floor to ~$5 under mutual
  dumping.

---

## 5. The ranked levers (PLAN_300K "five multipliers")

Implement one at a time, gate with `test.py` (see `07`), promote only on higher
paired own-coins mean **and** non-worse p10 **and** 0 non-DONE statuses **and**
0 terminal unsold **and** ≤ 4 ms/step.

| # | Lever | Rough $ multiple | Status |
|---|---|---|---|
| **M4** | **Sell cadence** — sell to production every turn, all 10 slots, size each line against `price_at`; keep premium-line inventory ~100–200 *below* I0 (monopolist mode) | ×2–3 (biggest) | **untried** — the one genuinely unexplored lever |
| **M1** | **Land** — 4 quadrants incl. the $4k, fast (Q4 by day 9–11), gated on fill + cash cushion; raise the land order's priority so it isn't truncated | ×1.33 capacity | partly done (v5 buys Q4 day 8–20, fill ≥ .62) |
| **M2** | **Labour + movement** — 12–14 hands from ~day 4; movement < 30% via spawn-proximity zone assignment | ×1.3 effective actions | hands done; movement rework **not** solved |
| **M3** | **Yield/tile** — FERTILIZE in-window ongoing crops; CARE every animal daily | ×1.5–2 on ongoing lines | **repeatedly reverted** — see §6 |
| **M5** | **Endgame** — fold `main_p2` (done in v5); per-plant last-useful-tick; sell shed to $0 | ×1.05–1.15 | base done; last-useful-tick not done |

Plus a **passive/active "monopolist mode" switch**: classify the opponent
(few tiles / low plant count / static money / 0 animals = passive) and, when
passive, expand harder and under-sell the hinge + premium lines to ride scarcity;
when active, use the contested-mode caps. **This switch as tried (§6) regressed**
— it needs a much more careful passive detector.

---

## 6. Tried and reverted — do not re-run these blind

| Change | Result | Why it failed |
|---|---|---|
| **CARE as a general task** (priority ~2650, dedicated 5-unit crew) | −2k overall, −9k vs wheatflood, one starter game as low as 16k | The crew pulled too many hands off crops; passive-case loss outweighs the self-play gain. The dedicated animal crew still does CARE in its own sweep. |
| **Opportunistic FERTILIZE pass** (idle unit carrying animal fertilizer tops up a nearby in-window tomato/strawberry) | regressed, matches `main_p2`'s earlier revert | Carrier logistics churn costs more than the capped +yield. `max_held = 4` saturates the +1/day doubling within ~2 harvested days → ceiling ~$6k/game before walk + zone-reshuffle cost. |
| **Courier FERTILIZE** (dedicated hand) | not attempted — 3 independent signals say dead end | Same `max_held = 4` cap; ~$6k/game ceiling not worth the plumbing. |
| **§3 passive/active aggression** (big herd + aggressive land when opp is tiny by day 8) | starter 70k→60k, wheatflood 67k→57k, one animalfarm game 14k | Aggressive expansion overshoots what the hands can work (weeds spread, cash sunk in immature animals); `opp_is_passive` misfires on bots that are merely slow to ramp, then they ramp and crush us. |
| **M2 sticky targets** (module-global `{unit: last_target}`, `+240` to continuing last turn's target) | 12 games looked +16k; 30 games showed it was variance — −5.8k vs `main_v5`, wheatflood 67k→45k, move% unchanged at 65% | The movement is mostly legitimate dawn commute, not oscillation, so the sticky bonus only ever overrode *better* nearby task choices. |
| **Cut day>22 CARROT for late WHEAT** | 14-0-16, −63 in self-play | Carrot's 3-day cycle genuinely beats a day-24 wheat on the same tile. |

**Net:** the shippable step up is the throughput bundle already in `main.py` v5
(week-1 front-load + land-to-4 + 13 hands + `animal_tiles` fix + endgame fold).
Every lever beyond it tried so far is net-negative or not worth it **on the local
harness** — but the local harness only has `starter`/self-play/`bots` as
opponents, and 48–0–0 locally has coexisted with a 477 ladder score. **Trust
ladder replays over local self-play** for anything strategic.

---

## 7. Principles that keep proving true

- **Actions are the scarce resource, not land or money.** Hire cheap hands
  before buying land; never plant a tile you can't guarantee daily water +
  harvest for.
- **Survival deadlines outrank yield bonuses.** Priority order: water a plant
  dying tonight → feed an animal escaping tonight → liquidate before step 718 →
  harvest at cap / decay → yield-window water/fertilize → collect animal product
  before `max_held` blocks it → drop before overflow → plant/build → clear weeds
  / reposition. Fold travel time and turns-to-deadline into the priority, don't
  use a static list.
- **Optimise net value per unit-action**, not price per item:
  `expected revenue − seed/feed/fert/land/hire cost − action opportunity cost`.
  Reject any crop that can't finish a profitable harvest before step 718.
- **Exploit demand without gluting.** Sell staples every turn for liquidity;
  sell premium (strawberry/melon/milk/wool) in small price-aware batches,
  re-checking `price_at` each turn. Count duplicate shops independently.
- **Adapt smoothly to the opponent.** Their field is public — estimate their
  next ~5 days of output per product and shade crop shares / sell sizes *away*
  from what they're about to flood, *toward* products with duplicate shops and
  low combined visible supply. Adjust scores, never flip the whole strategy in
  one turn.
- **The real ladder is not self-play.** Beating `starter` / past versions
  48–0–0 tells you almost nothing. Pull real losses, classify the opponent,
  reproduce it as a `bots/` file, and gate against that.
- **Ship one measured change at a time**, keep every promoted `main` as a
  regression opponent, and re-read the next batch of ladder replays before the
  following change.
