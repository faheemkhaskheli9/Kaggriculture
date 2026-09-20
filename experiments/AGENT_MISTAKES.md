# Agent mistake & strategy register

Compact, one line per item. `LEDGER.md` stays the full per-version record; this
file is the readable index of **(A)** what the agent does wrong in games,
**(B)** every strategy tested and why it did or did not work, **(C)** the ways
our *tests* went wrong. Built 2026-09-20 from the 49-sub Kaggle history + LEDGER.

**Upkeep (same sitting, re-read first):**
- Teardown / loss read finds a leak → add or update an **A** row (evidence + $/game).
- Candidate built, gated, submitted or judged → add or update its **B** row and
  the linked A row's status.
- A test turns out to have been misleading → tag the B row with a **C** code; new
  failure mode → new C row.
- "Ladder now" = current `publicScore`; refresh only for rows you touch.

Status: `FIXED` (promoted, large proven effect) · `PROMOTED?` (on `main.py`,
ladder effect inside noise) · `OPEN` · `FIX-FAILED` · `WONTFIX` · `CLOSED`
(data says not worth it).

## A. Agent mistakes (what the farm does wrong)

Ranked: open items first by est. cost, then fixed history.

| ID | Mistake | Evidence | Est. cost/game | Fix attempts (→ B) | Status |
|---|---|---|---|---|---|
| M14 | **Herd built late and small**; Q2 land + hands 8-10 bought on d5-8 before animals; cash sits uninvested at d10 | 1,365-game read: animals d8 3.9 vs 8.1 (opps ≥100k), d10 6.4 vs 10.8, d14+ 11.8 vs 14.7; we lead 91% at d10, trail 56% at d15; d15-20 gain 13.6k vs 24.6k; top farms 160-173k on 6 COW + 11 SHEEP vs our 82k median | **≥10k** | B05 B04 B10 B23 B33 B39, HERDBATCH | **OPEN — #1.** Every attempt changed one atom (T5) or was judged by a blind gate (T3). Unknown: how ≥100k farms monetize 15+ animals |
| M15 | **STRAWBERRY planted blind to demand**: 46-51 STR tiles whatever the shop draw | No SMOOTHIE/ICE_CREAM by d12 → STR 129-148, own median 64k; own-money top vs bottom quartile STR revenue 60.6k vs 20.2k, MILK 48.4k vs 12.7k; win-rate 26% (STR<100) → 88% (>260) | 5-15k in dry-board games | B27 B40 | **OPEN.** Cutting volume did not cut crashes (5/38 both arms) → lever is *what to plant instead*, not a cap |
| M16 | **Labour does not cover the field d16-28** | 21-25 of ~55 plants unwatered at h23 on d16-26 with 0% PASS; 407 of 953 WATER ops/game change no engine state; crew cut 12→8 on d27-28 leaves 18.7/27.6 plants dry (opp 8.6); movement 63% of unit-actions vs top-10 48% | ~5k | B14 B37 B38 | **OPEN.** B38 WATER-ON-NEED is the best-supported post-v45 candidate (local +5.6k, CI excl. 0) and was retired on a read that later reversed → re-open |
| M17 | Fertilized STR ticks go unwatered (fertilizer +1 lost) | 25.5 ticks/game on `56321057` | ~2-3k | B35 | OPEN — re-tier below 4800/5000, stack on B38 |
| M18 | STR decays after `max_lifespan_step` (spent plants watered, HARVEST hidden by dedup) | 17.6 units/game → 11.0 with B36 mechanism live | ~2.5k | B36 B45 | OPEN — B45 pending |
| M12 | Weeds pile up: out-of-zone DIG was impossible; older sweeps lived in dead code | weeds29 = 24, 14/14 losses tagged WEED_PILEUP; top-10 median 0 | unknown (tag is not a cause: W/L farms identical) | B07 B10 B41 B44 | PROMOTED? — weeds29 only 24 → 22 |
| M22 | Q3 land bought when the crew cannot cover it | 55-62 tiles, weeds 17-27, move% 63 in af losses | small | B12 | OPEN-low |
| M19 | 14-25 tiles idle d6-10 while the reserve ramp blocks $10 seeds | loss read 09-16 | — | B29 (−8.6k: wheat displaced the d9-10 STR wave) | FIX-FAILED |
| M20 | BUY_ANIMAL re-buys while a hand carries the species | 6.7 of 14.2 BUY orders; herd 13 vs want 11 | — | B31 ×2 | WONTFIX — overshoot is load-bearing |
| M21 | Wheat sold at h0 then re-bought for feed | — | small | B25 | WONTFIX |
| M23 | d29 leaves ~12 ripe plants + ~14 weeds | teardown `56079953` | small; only 28/170 losses within 5% | B09 | CLOSED — endgame polish is not the lever |
| M24 | Dawn HIRE batch pushes top SELLs past the 10-order cap | first slot SELL 32% vs top-10 66% | none found | B08 | CLOSED — truncation not confirmed (A15) |
| M25 | 4 COW buys d0-2 crater cash to $51-480 | all 27 losses on `56044961` | — | B04 B05 B06 | CLOSED — per-buy cash floors are flat or harmful |
| M01 | Feed buy blocked by the cash reserve at 0 shed wheat | diff vs v10 | large | feed-floor `56016363` | FIXED |
| M02 | Greedy task assignment, wasted walking | — | large | B02 B03 | FIXED |
| M03 | Day 29: no HIRE (hands reset daily), final fertilizer skipped, ~10 units unsold | top-3 replay audit | ~3% | B13 | FIXED |
| M04 | 100-item shed overflows | 22/23 games, ~$6.3k/game + 51 bought animals discarded | **6.3k+** | B16 | FIXED (+8.3pp, +9.1k local) |
| M05 | No melon opening → cash flat d10-17 | d15 cash 794 vs opp 9.6k, leaders 16-25k | **14-17k** | B18 | FIXED (+10.4pp CI excl. 0) |
| M06 | Bought animals never installed | buy ~11, place ~8; PICKUP 81×, PLACE 8× per game | **~10k** | B17 B21 | FIXED (placed 14/14) |
| M07 | Crop value ignored the 4-tick lifespan → TOMATO flip | 37% of games, win 28% vs 63% | ~3k+ | B22 | FIXED |
| M08 | Animals escape unfed although the shed has wheat | 2.15 animals/game, 81/96 games | ~2k | B24 | FIXED (→ 0.03) |
| M09 | Goose slots kept while a YARN_STORE is open | sheep ~480/day vs goose ~200/day | +13-35k in yarn-by-d9 games (27/76) | B30 | FIXED (conditional) |
| M10 | Cows 5-6 bought after 3 draws show no milk shop | 26% of games; MILK d25 ≤ 40 in 81% of them | +4.3k in those games | B32 | FIXED (conditional) |
| M11 | No crop FERTILIZE at all | top farms fertilize | ~4k | B19 B34 | PROMOTED? (copies 675.6 / 651.4 / 623.6) |
| M13 | Out-of-zone crop FERTILIZE impossible | code read; ~65 ops/game | ~0 | B42 | PROMOTED? — correctness only |
| M00 | v6 angular-wedge zones broke the v4 matchup (25% vs 90%) | local | — | v7 | FIXED |

## B. Strategies tested

Local = paired A/B vs `main.py` unless noted. Ladder now = `publicScore` on
2026-09-20. Noise reference: identical bytes read 675.6 / 651.4 / 623.6.

| ID | Strategy (`ENABLE_*`) | Sub | Local signal | Ladder now | Verdict | What went wrong (→ C) |
|---|---|---|---|---|---|---|
| B01 | P4b + cropflip | 56023304 | — | 526.7 | superseded | T1 |
| B02 | Hungarian routing 1c / 1f | 56029879 / 56034847 | 0/719 action mismatches | 522.6 / 565.7 | promoted → reverted → re-promoted | T8: reverted on a 2-episode read |
| B03 | MAXHANDS_12 | 56044961 | +5.0% CI[+1.7,+10] (self-play bucket) | 585.4 (verbatim copy 56078956: 538.1) | PROMOTED | "605.1 peak" was a mid-run high (T2) |
| B04 | EARLY_CASH_GUARD (B3) | 56050226 | +1.0%, CI crosses 0 | 560.3 | regression, OFF | T3 |
| B05 | ANIMAL_PACING (Lever A) | 56055430 | local no-op | 553.3 | flat, OFF | T3 |
| B06 | LEVER_B_Q3_GATE | 56059070 | — | 541.1 | hurt, OFF | delaying Q3 land costs income |
| B07 | LATE_WEED_SWEEP | 56079953 | additive | 562.4 (control 538.1) | PROMOTED | **T6 + T1:** hunk sat in dead `_v11_assign_unused`; a no-op "beat" its control by 69 points |
| B08 | SELL_FIRST_ORDERS | 56089527 | 112-0-8 | 543.2 | retired | hypothesis wrong (M24) |
| B09 | ENDGAME_SWEEP | 56101006 | 101-1-14 | 505.9 | regression, retired | low-value target (M23) |
| B10 | v30 bundle: HERD_RESERVE_EXEMPT + WEED_SWEEP_EARLY | 56126876 | 0 err | 530.0 | retired | T4 bundled; weed half was dead code (T6) |
| B11 | v33 STRAWSKEW + LANDRESTRAIN | 56135689 | flat | 554.3 | not promoted | T4, T3 |
| B12 | LAND_RESTRAINT | 56178741 | +4.2% CI[0,+8.3] | 545.5 | HOLD, ambiguous | T1 |
| B13 | TERMINAL_WORKFORCE | 56184777 | +3.3% CI[+0.8,+6.7] | 542.3 | PROMOTED | — |
| B14 | MOVE_THRIFT_V2 | 56186245 | +1.6%, CI crosses 0 | 511.0 | retired | T3; possibly a real regression |
| B15 | OPP_SHADE | 56190458 | +3.1%, CI crosses 0 | 549.4 | HOLD → OFF | T3 |
| B16 | **SHED_STAGING** H1 | 56195143 | +8.3pp, af margin +9.1k | 600.9 | **PROMOTED — real step** | — |
| B17 | ANIMAL_CARRY_GUARD H2 | 56199353 | +5.2pp CI[0,+10.4], +6.0k | 578.7 | retired | T1 — same leak later fixed by B21, so likely a false retire |
| B18 | **OPENING_MELON** N1 | 56199529 | +10.4pp CI[+3.1,+17.7], +13.9k | 608.6 | **PROMOTED — real step** | — |
| B19 | CROP_FERTILIZE H3 (first build) | 56233524 | 0.0% externals | 638.6 | parity → re-tested as B34 | T5: labour was the binding constraint then |
| B20 | CROSS_ZONE_WATER H4 | 56235916 | 0.0% | 608.8 | not promotable | T6: own-zone-clear gate almost never opens (one zone per hand) → v69 |
| B21 | **HERD_INSTALL_FIRST** C2 | 56256380 | +2.6% CI[0,+5.7], af margin +10.5k | 642.5 | **PROMOTED — real step** | — |
| B22 | CROP_VALUE_LIFESPAN C1 (+ union v45) | 56256499 / 56259132 | +2.6% CI[−0.5,+6.2], af +3.4k | 638.9 / 656.8 | PROMOTED via union | alone missed the af guardrail by 1-2 games (T1) |
| B23 | HERD_14 (v46, v52) | — | −2.1%; own −1.6k; af −3.1k | — | REJECTED ×2 | T5: extra milk/wool into a saturated market, no species/sales plan |
| B24 | FEED_FIRST (at-risk v48; blanket v47 −10.8k) | 56281675 | escapes 2.15 → 0.03, margin flat | 644.4 | PROMOTED | — |
| B25 | W1 wheat churn | — | — | — | dropped | too small |
| B26 | CROP_CROWD_OWN_ONLY C3 | — | gate clean | — | held, superseded by B27 | — |
| B27 | SHOP_DEMAND_VALUE S1 | 56282756 | +463 | 656.9 | not promotable | STR crash rate unchanged 5/38 → volume is not the cause; T1 |
| B28 | S2 herd-by-drain | — | backtest +400/game | — | dropped | T10 |
| B29 | IDLE_SEED_BYPASS M1 | — | −8.6k | — | REJECTED | displaced the d9-10 STR wave |
| B30 | SHEEP_ON_YARN | 56307690 | +2.9k mean; yarn seeds +13.5k/+35.5k/+24.8k | 663.8 | PROMOTED | — |
| B31 | BUY_COUNT_CARRIED v54 / _REALIZED v57 | — | +4.0k then +1.4k, median ≤ 0 | — | REJECTED ×2 | overshoot is load-bearing (M20) |
| B32 | COW_ON_MILK | 56311727 | affected pairs +4.3k, rest identical | 670.5 | PROMOTED | — |
| B33 | HERD_CAP_RESERVE | — | — | — | REJECTED | sheep pay back even stacked |
| B34 | CROP_FERTILIZE re-read (v58) | 56321057 | +3.1% CI[0,+6.8], af own +4.3k | 675.6 (copies 651.4, 623.6) | PROMOTED | "693.6 / 705.8 peak" = T2 |
| B35 | FERT_WATER_PRIORITY v59 | — | tier 6200: −2.2k vs af; 4600 re-tier rejected | — | REJECTED | T7 |
| B36 | SPENT_NO_WATER v60 | 56327834 | +863 | 652.5 | parity, OFF | T10 |
| B37 | LATE_CREW v61 | 56331079 | +576 | 660.1 (control 651.4) | retired | T10 |
| B38 | **WATER_ON_NEED v62** | 56347628 | **+4.7% CI[+1.0,+8.9], own +5.6k**, WATER 932 → 699 | **674.9 (control 56347642: 623.6)**; at judgement 654.5 vs 673.7 | FLAT, OFF | **T1/T2:** judged at 21 eps on af win-rate; gap has since flipped to +51 for the candidate → **RE-OPEN** |
| B39 | HERD_BEFORE_LAND v63 | — | every real archetype 0.0% W/L; af margin −6.8k; headline −3.1% is the n=10 self-play bucket | — | REJECTED | T3 + T5 |
| B40 | STR_CAP v64 | — | never fired in 96 games | — | PARKED | T3/T6: untested, not rejected |
| B41 | CROSS_ZONE_DIG v65 | 56349621 | margin +101 | 665.8 | PROMOTED at 20 eps (55.6%), 50.0% by 29 eps | T1, T10 |
| B42 | CROSS_ZONE_FERTILIZE v66 | 56353648 | 0.0% | 651.8 | promoted on correctness | T10 |
| B43 | PIZZA_SHOP mechanism | — | full-history read | — | ruled out | — |
| B44 | ZONE_GATE_RELAX v67 | 56389085 | +2.5% CI[−2.5,+7.5] | 666.0 (30 eps) | JUDGED 2026-09-20 FLAT: af 53.8% (14-12) vs floor `56353648` 53.1% (17-15); weeds29 23 vs 24 (mechanism did not move weeds); keep OFF | T10 |
| B45 | HARVEST_CROSS_ZONE v68 | 56389176 | +1.2% CI[−4.6,+6.7] | 665.1 (31 eps) | JUDGED 2026-09-20 FLAT: af 53.6% (15-13) vs floor 53.1%; mean coins 81.0k vs 84.8k; keep OFF | T10 |
| B46 | WATER_GATE_RELAX union v69 | — | +2.5% | — | NOT SUBMITTED: both components judged flat on the ladder in isolation (B44 + CROSS_ZONE_WATER `56235916`); `bug`/cross-zone family benched 2026-09-20 | — |
| B46b | CROSS_ZONE_PLANT v70 (`agents/main_v70_crosszoneplant.py`) | — | −2.9% CI[−7.9,+2.1], I/S/R 6/105/9, margin −924, 0 err (120 pairs) | — | REJECTED locally 2026-09-20; first gate attempt died on OpenBLAS OOM from two concurrent compete runs — run gates one at a time with `OPENBLAS_NUM_THREADS=1` | — |
| B47 | Early local-only: Lever 2 crop value, Workstream B rules R1-R3, E2/E3 animal reserve, TXCASH, HERDBATCH, HIRE_SLOT_CAP (−7.4k), B4 lead-aware liquidation | — | mostly CI crossing 0 | — | kept ON (E3, TXCASH, Lever 2) or OFF | T3 |

## C. Test mistakes (why reads misled us) and the rule that prevents each

| Code | Mistake | Evidence | Rule |
|---|---|---|---|
| T1 | Judged inside the noise band | 20-30 eps = ±10pp SE (±19pp 95% CI on a 26-game af read); identical bytes 675.6 / 651.4 / 623.6; B38's gap flipped sign after judgement | The ladder can only confirm ≥ ~50 rating points vs a concurrent identical-bytes control read at the same age. Below that, decide on local evidence |
| T2 | Wrong yardstick | Pairing is rating-matched, so win-rate sits at 46-58% whatever the strength (rating 515 → 655, win-rate flat); "peaks" 605.1 / 693.6 / 705.8 were mid-run highs | Never use af win-rate or a peak score as the bar. Settled rating vs concurrent control only |
| T3 | Local gate blind | Win/loss saturates at ~93-0-3; economy levers read +0.0% on every real archetype | Gate on paired **own final money** (mean + CI), strongest local opponents. "Never fired locally" = untested, not rejected |
| T4 | Bundled on the ladder | B10, B11 | Attribute locally (paired A/B per flag), then ship the stack |
| T5 | One atom of a coordinated strategy | B23, B39: more animals without species mix / sales spreading / labour plan | Build the coordinated economy behind one flag; compare own money |
| T6 | Fix never executed | B07/B10 in dead `_v11_assign_unused`; B20 gate never opens; B40 never fires | Every candidate logs a mechanism fire-count; 0 fires = do not submit |
| T7 | Priority-tier collision | B35: 6200 tier outranked animal harvest | Slot new tiers against 4800/5000; check displaced-task counts |
| T8 | Judged too early | B02 reverted on 2 episodes; 16-20-ep spikes decay (B07, B41) | No verdict before both arms are the same age and ≥20 eps |
| T9 | Non-`main.py` files submitted ad hoc | `main_v12.py` 96.6, env probe 209.8, 168.2 | Only promoted `main.py` + flagged candidates |
| T10 | Effect too small to ever measure | B36 +863, B37 +576, B41 +101 each took a slot | Submit bar: ≥ +8k own money locally, CI excluding 0 — the three real steps were +9.1k / +13.9k / +10.5k. Smaller wins get stacked, not submitted alone |
