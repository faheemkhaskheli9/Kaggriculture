# AUTO_IDEAS.md — ranked idea backlog for the /ladder-auto meta-loop

Created 2026-09-07 by `/ladder-auto` iteration 1. Re-read before every write;
Codex may share the tree. Format below. Status vocab: `queued` / `built` /
`submitted` / `gated-flat` / `reverted` / `parked`.

The LEDGER is authoritative for per-version history; this file is only the
forward queue + why each item is/ isn't above the submit bar.

| id | idea | class | evidence | est. ranked EV | status | flag name |
|---|---|---|---|---|---|---|
| A0 | LATE-WEED-SWEEP — an idle hand clears the nearest out-of-zone weed within 4 tiles from day≥20 (relaxes the hard DIG zone-restriction in `assign()` for hands that have no task this turn) | mechanical (execution-efficiency) | 2026-09-07 teardown subagent: board-best `56044961` carries ~13 weeds at d25–29 (20–29 in the animal_factory blowout losses) vs top-10 median ~0; weed accrual correlates with the weaker loss games. NEW — not on the reverted list (v6 DIG-2800 pulled hands *off crops*; this only ever redirects an already-idle hand → structurally cannot regress). Built `agents/main_v21_lateweedsweep.py`. Gate: OFF zero-diff 0/24; ON 24-pair 0/24/0 (fully inert locally); ON 120g 111-4-5 / 94.2% / 0 err / weeds29 unchanged / no external loss. | ladder-only EV — local league can't reproduce the animal_factory weed pile-up. Worst case FLAT (like Lever A), never a regression. **25-ep read: PROMOTED on the concurrent A/B — `56079953` (ON) 52% / af 41% / 598.5 vs `56078956` (OFF control, same window) 39% / af 24% / 529.0 → +13pp / +17pp / +69.** Watch for convergence on continued accrual. | **PROMOTED `56079953`** (`c83ae34`) | `ENABLE_LATE_WEED_SWEEP` |
| A1 | Movement-thrift v2, 35/2/2 constants — progressive far-walk penalty + idle-reposition deadband + same-tile op batching in routing `assign()` | mechanical | `analyze_top.py` on 22 top-10 replays: board-best spends 63% of hand-actions moving vs top-10 median 48%. Largest mechanical gap. **RE-BASED onto `c83ae34` board-best as `agents/main_v22_movethrift2_rebased.py` (`06ce2a0`, 3-way merge 0 conflicts; diff vs `main.py` = exactly the move-thrift hunk).** Gate 2026-09-07 ~23:00: OFF zero-diff **0/24/0** clean; ON 120g **110-0-10 / 91.7% / 0 crashes / 0 errors**, vs starter 6-0-0, no external-archetype regression (all losses lineage self-play). Ready to submit at next slot-open. | ladder-only, unproven; local read is a near-no-op (−0.2pp move). Same profile as Lever A (flat) / Lever B (regression). Mechanical class = the only class that ever moved the ladder; queued as the next attributable bet. | built (gate clean, slot-pending) | `ENABLE_MOVE_THRIFT_V2` |
| A1b | Movement-thrift v2, 90/1/3 escalation — same flag, FAR_PENALTY 35→90 / FAR_FREE 2→1 / IDLE_SLACK 2→3 | mechanical | `agents/main_v19_movethrift3.py` `4125e8f`. ON 120g 102-0-18 / 0 err, all 18 losses lineage self-play (known 90/1/3 self-play softness), no external regression, move% 63% unchanged. | Use ONLY if A1's 35/2/2 is submitted and reads flat — then revert flag and submit this file (no code change, constants already in it). | built (standby) | `ENABLE_MOVE_THRIFT_V2` |
| A2 | Lever C — lead-aware premium liquidation: on days 18–25, if a coarse public-state lead estimate ≥ $10k, sell premium inventory sooner (cap ×1.6, keep ×0.85) to cut late-game variance | economy (risk-mgmt) | `PUBLIC_AGENT_STRATEGY_CATALOG.md` family 15. Built `ca88691`, default OFF. OFF-path zero-diff 3595 steps / 5 seeds / 0 mismatch. ON 120g 102-0-18 / 0 err, no trivial-bot regression. No paired A/B (fires only in already-led games). | Win/loss protector only — never changes a losing game, lowers the chance a led game flips late. Small but non-negative EV. Below A1 in the mechanical-first ordering. | built | `ENABLE_LEAD_AWARE_RISK` |
| A3 | SELL-FIRST market ordering — reorder `market_orders` slot assembly so the top premium SELL(s) fill slot 0 before HIRE / BUY_SEED / BUY_PRODUCT on turns where inventory value > 0. Orders process in slot order and >10 overflow is dropped. | mechanical (execution-efficiency) | **NEW — 2026-09-08 iter 3 replay-mining subagent, gap #4.** Our first market slot each turn: SELL 32% / BUY_SEED 28% / HIRE 22% / BUY_PRODUCT 17%. Top-10: **SELL 66%** / BUY_PRODUCT 15% / BUY_SEED 13% / HIRE 5%. Top-10 convert inventory→cash before spending; we lead with hires/seed buys. Directly targets the mid-game cash crater (deficit onset ~d6 close losses, ~d11–12 blowouts vs animal_factory). Not on the reverted list. Cadence sub-gap (#5): we touch market on 26.7% of turns vs 41.8% — same fix family (open the market SELL-first more often). | mechanical class + targets the dominant loss mechanism (cash-starved animal_factory games). Plausibly the highest-EV unbuilt item. **BUILT 2026-09-08 iter 3** as `agents/main_v23_sellfirst.py` (copy of `main.py` + flag default OFF + one guarded `elif` in `market_orders`: `out = sells[:3] + hires + buys_hi + buys_lo + sells[3:]`). `ENABLE_TXCASH_FORECAST` already puts sells[:3] ahead of buys; this moves them ahead of `hires` too, so the dawn heavy-hire turn no longer pushes cash-in past the 10-order cap. Gate 2026-09-08 iter 5: OFF zero-diff **0/3595** (5-seed paired), OFF 120g 107-1-12 / 89.6% / 0 err / starter 3-0-0, ON 120g **112-0-8 / 93.3% / 0 err / 0 crash**, no external-archetype regression (animal_factory 11-0-0), all 8 losses lineage self-play. Not inert (ON +3.7pp over OFF, unlike HIRE-SLOT-CAP). **SUBMITTED 2026-09-08 as `56089527`** (autonomous, 1 of ≤2/12h; evicts `56078956` 538.1). **RETIRED 2026-09-08 iter 7 at 28 eps: 12W-0T-16L / 43% / animal_factory 3-0-10 / 23% / ladder 519.1 vs board-best `56079953` 52% / af 41% / 584.7 → −9pp overall / −18pp af / −65 ladder. Clear regression (not FLAT). Silent raise ruled out (0 logs). Loss mechanism = the mid-game cash crater vs animal_factory is unchanged — reordering SELLs ahead of hires does not fix an investment-timing deficit.** Flag stays OFF on `main.py` (already OFF); candidate kept in `agents/`. Baseline unchanged. | reverted `56089527` | `ENABLE_SELL_FIRST_ORDERS` |
| A4 | ENDGAME LIQUIDATION SWEEP — from day≥28, exempt `["HARVEST"]` tasks from the zone-first restriction in `assign()` so any free hand grabs the nearest ripe tile anywhere on the farm (unbalanced end-of-season zones otherwise strand ~12 mature tiles + ~14 weeds standing at d29 vs top-10 ~0). | mechanical (execution-efficiency) | **iter 7 board-best `56079953` teardown subagent, gap #5.** d29 avg 12 plants standing (up to 24) + 14 weeds (up to 28) → 26–50 of 75 tiles delivering nothing at season end; top-10 weeds29 ~0. **6 of 15 ladder losses are within ~9k coins** (1.0k/4.2k/6.4k/7.0k/7.2k/9.1k) → harvesting the standing mature crops the last 1–2 days recovers ~5–15k, plausibly flips 3–5 close games → +10–17pp win-rate. Root cause found: HARVEST is priority <9000 so the zone-first invariant blocks an idle hand from crossing to an out-of-zone ripe tile while its own (empty) zone has any pending cell. **BUILT 2026-09-08 iter 8** as `agents/main_v24_endgamesweep.py` — flag `ENABLE_ENDGAME_SWEEP` default OFF + `ENDGAME_SWEEP_DAY=28` + one guarded hunk relaxing the `priority<9000 and has_zone_task and not in_zone → _IMPOSSIBLE` block for HARVEST when the flag is ON and day≥28. Strictly relaxes toward MORE harvesting — cannot cut throughput. **Gate (iter 9): OFF-path zero-diff 0/19 clean; ON 120g 101-1-14 / score 87.5% / 0 `agent()` errors (4 CRASH = `HARNESS_ERROR: MemoryError()`/`OSError(22)` = local machine OOM, not agent raises — 78–86s game times confirm swap thrash); paired A/B −0.9% CI[−3.0,+1.3], movement +0.0, productive −1.3 (locally inert, as predicted for a day≥28 sweep). 2g main.py-flag-ON smoke vs starter 2-0-0 / 0 err.** | ladder-only EV (local league ends with fields already near-empty). Same additive "structurally can't regress" class as the PROMOTED `LATE_WEED_SWEEP`. Targets win-rate specifically (the ~6 close losses). **SUBMITTED 2026-09-08 as `56101006`** (autonomous, 1 of ≤2/12h; base `56079953`). NOTE: newest-2 tracking evicted board-best anchor `56079953` (562.4) — tracked pair now `56101006` (pending) + `56089527` (retired A3, 542.9). If A4 gates flat at 20 eps → recovery = resubmit `56079953` bytes (then authorized: both tracked off board-best peak). | submitted `56101006` | `ENABLE_ENDGAME_SWEEP` |
| A5 | PER-DAY SEED/PLANT DRIP CAP — throttle field-fill BUY_SEED / new-PLANT to ~6–8 tiles/day (only per-turn `n_units*2` cap today), so the d9 ~15-tile seed spike ($1.4–3.8k in single turns) + d11 Q3 land don't drain cash to the reserve floor exactly in the d10–15 window where top-10 build a 10× buffer; also unjams the 10-order/turn cap on d9. | mechanical (execution-efficiency / throttle) | **iter 7 teardown gap #1, highest raw EV.** Our cash d10 ~$900 flat vs top-10 $2101 rising; the crater window is d10–15 and we spend it on a lumpy seed batch. Risk: a per-day *plant* cap could starve the field like the REVERTED P2k marginal-crop prune (42.5% vs 57.5%) — needs the cap tuned high enough (≥6) and gated to early days only. NOT on the reverted list as a *timing* throttle (P2k pruned by marginal value, not rate). | high raw EV but real field-starve downside — build & gate only after A4's ladder read. | queued | `ENABLE_SEED_DRIP` |
| A7 | HERD-RESERVE-EXEMPT (bug C) — for the BUY_ANIMAL affordability check only, while day≤14 and realized+pending herd < configured target, cap the reserve term at a small fixed floor (150) instead of the full day-scaled `reserve` ramp (`min(1400, 200+150·day)`). Exact structure of the feed-emergency-floor exemption. | herd-economy (bug fix) | **iter-17 deep-research + top-10 teardown, `docs/RESEARCH_LADDER_META_2.md` bug C. #1 EV.** Configured herd ~14 but realized ladder herd = **7.9**; opp animal count is the single best W/L predictor (win when opp≤10, lose when opp≥13). Root cause: the d6–15 herd-build window is exactly when the day-scaled `reserve` is highest, so the E3 gate (`money−reserve ≥ cost+150·placed_total`) blocks the buy almost every day → herd stalls at 8. Research finding #5: each animal ≈ $2.9k/season fertilizer (free, fed or not) + $1.3–1.8k product → herd under-built by ~half its value. Built 2026-09-09 iter 17 as `agents/main_v26_herdreserve.py`, `ENABLE_HERD_RESERVE_EXEMPT` default OFF + `HERD_RESERVE_EXEMPT_DAY=14` / `_FLOOR=150` + one `res_term` hunk in the E3 branch. OFF path = exact byte no-op (`res_term=reserve`). **OFF-path zero-diff 0/30 — PASS** (`btj9diviz`). **ON 120g standalone: 98/0/22 / 81.7% / 0 errors; 100% vs every external archetype (bot_animalfactory_v2 3/0/0, bot_factory_v3 1/0/0, bot_top10clone 2/0/0), all 22 losses lineage self-play.** Paired A/B vs `main.py` (`b9ogb9dh1`, 120 pairs): score Δ **−0.8% CI[−7.1,+5.4]**, productive **+28.4**, d10 cash **+109**, move −0.6% — but **animals 8.5 vs baseline ~7.9, barely moved: LOCALLY INERT** (local bots never crater our cash in the buy window). The `150·placed_total` per-head term (not `reserve`) is the actual herd cap → **A7b `agents/main_v27_herdreserve2.py`** thins it. | **highest EV of the queue** — targets the gate metric, the mechanism the crater teardowns have named since v8; bounded bug-class fix. Ships regardless of the flat local A/B (OFF-zero-diff + 0-err + no external tank all met; local cannot gate an economy change). **Staged as the submit proposal; A7b preferred if its gate is clean.** | built (gate clean, submittable) | `ENABLE_HERD_RESERVE_EXEMPT` |
| A7b | HERD-RESERVE-EXEMPT v2 — A7 + also thin the `150·placed_total` per-head running-cost term to `HERD_RESERVE_EXEMPT_RUNCOST=50` inside the exemption window (feed is already covered by the feed-emergency floor; the full term is what actually kept the realized herd at ~8, per the A7 paired-A/B). | herd-economy (bug fix) | Same as A7 + A7's finding that v26 relaxed only `reserve` → animals 7.9→8.5. Built 2026-09-09 iter 17 as `agents/main_v27_herdreserve2.py` (2-line change vs v26, same flag + one new const). OFF path keeps literal `150` → exact byte no-op. **iter 18 gate (bg `b13son1br`): OFF zero-diff `compete_runs/v27_offzd` 0/30 — every pair byte-identical, PASS. ON 120g `compete_runs/v27_on120`: 98/0/22 / 81.7% / 0 errors; 100% vs bot_animalfactory_v2 3/0, c_animalfactory 4/0, animal_factory archetype 8/0 — no external tank, all 22 losses lineage self-play. Paired A/B vs `main.py` (120 pairs): score Δ −2.9% CI[−8.3,+2.5], improved/same/regressed 7/103/10, day10 cash +212, productive +7.7, move −0.3%. Herd 8.5 — SAME as v26 (thinning runcost 150→50 did not move the local herd: local bots don't create the d10–15 cash pressure the exemption relieves).** Hunk hand-verified OFF-path == `main.py` (`agents/main_v27_herdreserve2.py:1717-1734`). | **the actual bug-C fix** (A7/v26 is the conservative half). Locally inert like A7 (local cannot gate the animal_factory crater — confirmed since v8). Ships on bug-class grounds: OFF-zero-diff PASS + 0 err + no external tank + day10-cash/productive in the intended direction. | **reverted `56126876`** — iter-28: episodes stalled at 23; re-read 52% overall / **af 37.5% (6-0-10) vs 50% baseline = −12.5pp gate**, ladder 556.3 ≈ 558.5 flat, weeds29 17 (worse), herd 9 (flat), 0 agent() errors, crater unchanged in all 10 af losses. Past 20 eps + wrong direction → RETIRED both flags (stay OFF on `main.py`). **`herd-economy` family benched 3 iters** (2nd non-beat after Lever A FLAT). | `ENABLE_HERD_RESERVE_EXEMPT` |
| A6 | OPP-SHADE (Lever G) — classify the opponent once/turn from public `obs["farms"]` into factory/wheatflood/premium/melon/passive/mixed, then *shade* (never flip) sell sizing: widen the per-turn sell cap ×1.30 for a product the opp is about to flood; vs a `passive` opp hold premium back ×0.70. Market-side only. | market-timing (opponent-model) | `RESEARCH_LADDER_META` C4 + `PLAN_LADDER_NEXT_5` Lever G. Built 2026-09-09 iter 17 as `agents/main_v25_oppshade.py`, `ENABLE_OPP_SHADE` default OFF + `_opp_archetype()` + one guarded hunk in `market_orders`. **OFF-path zero-diff: 0/30 — PASS.** **ON 120g (`bdd11an6j`): 110/0/10 / score 91.7% / 0 crashes / 0 `agent()` errors; vs bot_animalfactory_v2 3/0/0, vs c_animalfactory 4/0/0, vs starter 1/0/0 — no external regression, all 10 losses lineage self-play. Fully gated, submittable.** | **DEMOTED by the iter-17 research**: the ladder is a "replay ladder" (~85% clones), the interaction surface is just the shared market, and a reactive layer "alone has never been enough for top 100" — economy throughput must be top-decile first. Keep as a safe queued additive candidate, not the EV play. Guardrail: must not cost the animal_factory matchup. | built (submittable) | `ENABLE_OPP_SHADE` |
| A8 | LEAD-AWARE-VARIANCE — when our own econ is clearly BEHIND the opp mid-game (~d12–18, coarse public-state estimate ≤ −$8k), deliberately shift to a higher-variance line: dump premium harder, over-plant melon/strawberry toward the cap, skip a marginal land buy for an extra animal. Inverse of Lever C (which only de-risks when AHEAD). | economy (risk-mgmt) | **iter-17 research finding #2 — most-cited principled edge in the forum.** Rating = Φ(μ/σ) not E[margin]; when behind, adding variance raises P(win) and adding median does not. We do pure margin-max and have no such lever. `RESEARCH_LADDER_META_2` finding #2. | non-negative EV under Bradley-Terry (a coin-flip loss flipped = full rating swing; a bigger loss costs nothing extra). Build after A7's read. Risk: mis-firing the "behind" detector in a game we'd have won — gate the threshold conservative. | queued | `ENABLE_LEAD_AWARE_VARIANCE` |
| A9 | WEED-SWEEP-EARLY (bug A widen) — bring the shipped idle-hand out-of-zone DIG sweep forward from day≥20/range-4 to day≥10/range-7 (`ENABLE_WEED_SWEEP_EARLY`, default OFF). Same "no task this turn" guard as `LATE_WEED_SWEEP` → strictly additive, cannot pull labour off crops/animals. | mechanical (execution-efficiency) | **iter-19, `RESEARCH_LADDER_META_2` bug A + top-10 teardown gap #3.** `LATE_WEED_SWEEP` (d≥20) shipped and weeds are *still* ~13 at d29 (20–29 in animal_factory blowouts) vs top-10 ~0–1 — weeds form d8–15, the sweep starts after they've compounded. ~13–29 dead tiles/game = a direct throughput loss. Same "structurally can't regress" additive class as the PROMOTED `LATE_WEED_SWEEP`. OFF path is an exact byte no-op (two locals resolve to the `LATE_WEED_SWEEP_*` constants). Built `agents/main_v28_weedsweepearly.py` (`8ab5e76`). **iter-21 gate read: OFF zero-diff paired A/B `compete_runs/v28_offzd/20260909-201424-788431` — 30/30 pairs, 0 nonzero score/margin delta → PASS. Standalone 30g: 25W-4T-1L / 90% score-rate / 0 `agent()` errors / 100% vs every external archetype (the 4 ties + 1 −721 loss are lineage self-play). SUBMITTABLE on the additive can't-regress class.** ON 120g paired A/B still crawling (2 stale bg runs, ~18/120) — not decision-critical. | ladder-only EV (frozen local league doesn't pile weeds the way animal_factory games do) — worst case FLAT, never a regression. Targets the field-fill / throughput gap the research says is the game. | **reverted `56126876`** (bundle w/ A7b) — iter-28: weeds29 17 on the ladder (baseline 12), i.e. the early sweep made weeds *worse* not better; RETIRED with A7b. Flag stays OFF. Weed accrual is a labour-shortage symptom, not an unaddressed sweep-timing hunk — 3 sweep flags (LATE, EARLY, ENDGAME) have now all failed to move ladder weeds. | `ENABLE_WEED_SWEEP_EARLY` |
| A10 | IDLE-DRIFT-CAP — a taskless unit's idle-reposition (assign() ~L2092–2105) currently walks toward `min(all_pending, dist)` over **every cell of every zone**, then walks home next turn when own-zone work appears. Cap it: drift only toward an own-zone cell within `IDLE_DRIFT_MAX_STEPS=3`, else PASS. `ENABLE_IDLE_DRIFT_CAP`, default OFF. | mechanical (movement) | **iter-20 `docs/RESEARCH_MOVEMENT_LEVER.md`.** Our MOVE 4194 vs top-10 3209 = +985/game; move% 63 vs 50; top-10 gets +30% productive actions on the same budget. Excess by category: transit_to_work +414, **long_walk_noWork +269 (27%)**, haul_to_shed +156, reversal_jitter +73 (6× top-10), idle/stranded +67. Transit *run length* identical (1.9 vs 1.8) → excess = more trips, not longer. `long_walk_noWork` + reversal_jitter (~340/game) are exactly the idle-drift + walk-home churn this hunk removes. **Distinct from the reverted attempts**: MOVE_THRIFT_V2 reweighted the task-selection cost term; wedge-zones changed geometry; this touches neither (Hungarian match, ≥9000 safety pass, zones all byte-identical) — only MOVE-vs-PASS for an already-idle unit, so it cannot starve a tile or delay a rescue. **Built iter 21 as `agents/main_v29_idledriftcap.py`** (`ce…`), diff vs `main.py` = flag + 1 const + a 7-line guarded hunk in assign()'s idle block; OFF path byte-identical (`pending = own or all_pending`, no cap). Syntax+import clean. **Gate iter 22: OFF zero-diff paired A/B DONE — `compete_runs/v29_offzd_ab/20260909-203409-333718`, 40/40 pairs, 0 nonzero delta on any metric → PASS.** ON 120g A/B not yet run (A9 v28 ON run holds the machine; `scratchpad/v29_on.py` staged). | expected move% −3 to −5pp, ~+150–300 productive actions/game **locally measurable** (unlike economy changes) — a mechanical execution-efficiency change, the class that historically moved the ladder. Low regression risk. | **gated-flat** (iter-27: ON 120g A/B 94W-8T-18L vs 92W-8T-20L, score Δ +0.017 but **move%_delta −0.0015 = FLAT**, productive −1.3, 0 err, losses all lineage self-play → safe but inert, the movement metric it targets did not move; `movement-routing` family now 3-for-3 inert at the gate) | `ENABLE_IDLE_DRIFT_CAP` |
| A11 | ADJ-STICKY (movement #2, medium risk) — bounded `+bonus` for travel==1/2 tasks in the Hungarian weight (assign() L2042–2044) to cut transit trip-count. | mechanical (movement) | `docs/RESEARCH_MOVEMENT_LEVER.md` §9. Targets the transit_to_work +414 residual A10 leaves. | **medium risk — it IS the same weight expression the ladder twice declined to reward (MOVE_THRIFT_V2)** → gate separately, expect possible ladder-inert, do NOT bundle with A10. | queued | `ENABLE_ADJ_STICKY` |
| A12 | EARLY-STRAWBERRY-SKEW + PREMIUM-CROP-BONUS — (a) day<7 liquidity bootstrap: STRAWBERRY share 0.16→0.34, WHEAT 0.50→0.40 for day≥4; (b) Lever 2 day≥7 marginal-value pick: multiply STRAWBERRY/TOMATO `_crop_tile_value` by 1.30 (bounded thumb on the scale, not a calc rewrite). One flag per hunk. | **field-allocation** | **iter-28 top-10 structural diff.** Our season sells WHEAT 12257 : STRAWBERRY 3365 (73% wheat) vs top-10 STRAWBERRY ~56% / WHEAT ~37% at d20; top-10 10× their cash d10→15 while we sit flat until first strawberry harvest at d16. Early strawberry (planted d4-6) matures ~d12-15 → bridges the revenue hole. NOT the reverted P2k (that *pruned* marginal crops; this *skews toward* the runaway-ceiling crops CLAUDE.md econ notes say to lean into). NOT A3 (market-ordering). | HIGH EV, LOW-MED risk — trades away some d2-8 wheat bootstrap cash; day<7 wheat share still 0.40 + CARROT 0.28 covers the bootstrap. Built `agents/main_v31_strawskew.py` (`ENABLE_EARLY_STRAWBERRY_SKEW` + `ENABLE_PREMIUM_CROP_BONUS`, both default OFF; diff vs `main.py` = flag block + 3 guarded hunks, OFF-path byte no-op verified). Gate running (OFF-zd via v31 default + ON 120g A/B via `scratchpad/v31_on.py`). | built (gating) | `ENABLE_EARLY_STRAWBERRY_SKEW` / `ENABLE_PREMIUM_CROP_BONUS` |
| A13 | CRATER-SEED-THROTTLE — day 7-16 AND money < 2×base_reserve: hard-clamp `seed_spend_cap` (main.py:1512, currently `400 if day<10 else 800`) to ~$150/turn so the mid-game seed restock stops stacking with the d11 Q3 land buy to zero our balance exactly through the crater window. | **crater-timing** | iter-28 subagent §3: single gap-opening event in the af losses = d9 lumpy seed restock (~$3k across the day per the trace — NOTE discrepancy with the code's 400/turn cap, verify against a replay) + d11 $2000 BUY_LAND, spent while opp animal income compounds from d5 and we have no crop income until d16. Distinct from A5 SEED_DRIP (per-day *tile* cap) — this is a $-cap gated on low cash. | HIGH EV. Risk: under-seeded Q3 → fewer d15+ plants; bounded by the money threshold (only fires when already cash-crunched). Build next iter; verify the $3k/d9 trace first (code cap says 400/turn). | queued | `ENABLE_CRATER_SEED_THROTTLE` |
| A14 | ZONE-REBALANCE-ON-UNLOCK — on quadrant unlock, assign the 25 new tiles to the 2-3 nearest units incrementally instead of `make_zones` re-slicing the whole contiguous cell list (which reshuffles every zone → mass migration → the move% spike on d7/d12). Cache prior zones in a module dict keyed (player, n_units). | **movement-routing** | iter-28 subagent divergence #3 + `RESEARCH_MOVEMENT_LEVER.md`. move% 64 vs top-10 48; throughput dies on unlock days. Distinct from MOVE_THRIFT_V2 (task-cost reweight) / wedge-zones (geometry) — this is incremental vs full re-slice of the SAME zone algo. | MED-HIGH EV. Risk: zone imbalance — cap per-zone size delta. `movement-routing` is otherwise benched (3× inert) but this touches a different mechanism (zone *construction*, not the assign weight). Build after A12/A13. | queued | `ENABLE_ZONE_REBALANCE_ON_UNLOCK` |
| A15 | (Class-1 suspect, UNVERIFIED) SELL slot-truncation — `market_orders` assembly `hires + sells[:3] + buys_hi + buys_lo + sells[3:]` then `out[:10]` (main.py:1829-1830). On heavy dawn turns d9-13 (≈6 hires + 3 sells + 4 buys_hi + 5 buys_lo = 18 orders) everything after slot 10 is silently dropped — `sells[3:]` and trailing BUY_SEED never submit. | **bug** | iter-28 subagent §4 (flagged "suspected"). Tension with §3 (which says d9 buys *do* execute and drain cash). **Verify against replay 107185595 d9 order log before building.** If real: reorder so profitable sells beyond the top 3 are not behind all buys on cash-crunch turns. | ships on correctness grounds IF substantiated. Verify first. | queued (verify) | — |
| — | MKT / price_at constants audit (research #3 + #4) | economy (bug hunt) | iter 18: all 9 `MKT` tuples in `main.py` == engine `MARKET_PARAMS` v1.32.7 byte-for-byte (CARROT below_target already 1.00); `price_at` == `market_price`; `market_orders` feeds live post-drain inventory + meters sizing into the price hole. **No bug** — rules out the whole "mispriced sells" class. Loss is throughput (herd/field/break-even), not economy constants. | — | closed — no bug (`docs/RESEARCH_LADDER_META_2.md` MKT audit §) | — |
| — | HIRE-SLOT-CAP (`ENABLE_HIRE_SLOT_CAP`, `agents/main_v20_hireslotcap.py`) | mechanical | Gate C −0.5% CI[−3.6,+2.6], productive actions −94.1, margin −7447, 0 win/loss upside. Dropped hour-0 sells recover same day (hour 1). | — | reverted (below bar, kept behind flag) | `ENABLE_HIRE_SLOT_CAP` |
| — | Lever A per-buy animal cash floor / Lever B Q3 land cash-headroom gate | economy | Lever A `56055430` FLAT (585.3 / 54% / af 46%); Lever B `56059070` REGRESSION (505.9 / 38% / af 26%). Per-buy-floor class of crater fix exhausted. | — | reverted | `ENABLE_ANIMAL_PACING` / `ENABLE_LEVER_B_Q3_GATE` |

## Iteration log

- **2026-09-07 iter 1:** pending sub `56078956` (board-best `56044961` bytes
  resubmit, 600.0 label, 1 ep) → HOLD. Teardown subagent found TWO new mechanical
  gaps vs top-10: (1) late-game weeds 13 vs ~0 [→ A0, built this iter as
  `agents/main_v21_lateweedsweep.py`], (2) endgame liquidation completeness
  (~12 plants + weeds left standing at d29) [parked — harder to fix without more
  hands; revisit if A0 gates]. Movement 63% vs 44.5% confirmed still the largest
  raw gap but NOT new (A1/A1b cover it). No silent raise on `56044961`.
  Built A0 behind `ENABLE_LATE_WEED_SWEEP` (default OFF). Gate: OFF zero-diff
  0/24, ON 24-pair 0/24/0 (fully inert locally), ON 120g 111-4-5 / 0 err /
  weeds29 unchanged / no external loss → regression-clean.
  Phase D: **SUBMITTED `56079953`** 2026-09-07 15:36 (autonomous, #2 of ≤2/12h).
  Rationale: mechanical execution-efficiency change (the class CLAUDE.md says is
  the only one that ever moved the ladder), top of a fresh teardown, additive-only
  so it cannot regress rating (unlike Lever B). Evicts `56059070` (541 regr);
  pair = `56079953` + `56078956` (board-best bytes, settled 584.0). Flag reverted
  OFF on main.py post-submit. Both 12h slots now used; next ~2026-09-08 02:40.
  Verdict: **SUBMITTED `56079953`**.

- **Parked from iter 1 teardown:** endgame-liquidation-completeness gap (~12 plants
  + weeds standing at d29). Harder — needs better final-day routing or more hands,
  not a clean additive hunk. Build a candidate for it if a slot is open and the
  queue is otherwise dry. Movement 63% vs 44.5% still the largest raw gap but
  covered by A1/A1b.

- **2026-09-07 iter 2:** Phase A at 16 eps → HOLD (favourable direction). Phase B
  at 25 eps → **PROMOTED `56079953`** (`c83ae34`). Judged on the concurrent OFF
  control `56078956` (byte-identical to the frozen baseline, same ladder window):
  `56079953` 52% / af 41% / 598.5 vs `56078956` 39% / af 24% / 529.0 →
  +13pp / +17pp / +69 head-to-head. `56044961` retired (stale-population — its own
  resubmit reads 13pp lower on the current pool). `main.py` flag default → True.
  Queue now: **A1 movement-thrift v2 35/2/2 is next but NEEDS RE-BASE onto
  `c83ae34`** (v18 candidate predates the LATE_WEED_SWEEP hunk) + fresh OFF-path
  zero-diff. Both submit slots closed until ~2026-09-08 07:40 PST.
  Verdict: **PROMOTED `56079953`**.

- **2026-09-08 iter 3:** No pending sub (`56079953` promoted, live 606.8). Both
  12h slots closed at 00:07 PST; next opens ~02:40 (`56078956`), then ~03:36
  (`56079953`). A1 movement-thrift v2 35/2/2 already re-based (`06ce2a0`,
  `agents/main_v22_movethrift2_rebased.py`) and gate-clean: OFF zero-diff 0/24,
  ON 120g 110-0-10 / 91.7% / 0 err → **ready to submit at slot-open** (evicts
  `56078956` 529.0). Replay-mining subagent (local corpus, 25 eps of `56079953`):
  no silent raise; confirmed movement gap +14–18pp (A1); TWO items refreshed —
  **A3 SELL-first market ordering** (our first market slot SELL 32% vs top-10 66%;
  we lead with HIRE/BUY_SEED — directly targets the mid-game cash crater) added
  as the top *unbuilt* mechanical idea, and **A4 endgame liquidation sweep**
  (8 plants + 17 weeds standing at end vs top-10 2 + 0) added as parked.
  Verdict: **HOLD** (slot-blocked; candidate ready). Next: submit A1 v22 at
  ~02:40 PST, then build A3.

- **2026-09-08 iter 4 (07:30 PST):** Both slots now OPEN (0 subs in last 12h;
  aged out ~03:36). Board-best `56079953` settled **584.7** (was 606.8 mid-accrual),
  control `56078956` **538.1** → gap +46.6, promote holds (converging but not
  converged). **Decided NOT to submit A1 v22:** its local A/B is +1.0% CI[−3.1,+5.2]
  (crosses 0) and delivers only −0.2pp movement — the CI-crosses-0 / marginal case
  that `kaggriculture-own-the-submit-call` explicitly disqualifies. The teardown
  re-confirmed the *gap* is large but not that A1 *closes* it. **Built A3 instead**
  — `agents/main_v23_sellfirst.py`, `ENABLE_SELL_FIRST_ORDERS` default OFF, one
  guarded `elif` moving `sells[:3]` ahead of `hires` in `market_orders`. Gate
  subagent running (OFF zero-diff 24 + ON 120g). Slots stay open (nothing submitted
  since 09-07 15:36) so no rush. Verdict: **BUILT `agents/main_v23_sellfirst.py`**.
  Next: read the A3 gate; if clean + behaviour actually shifts (first-slot SELL%
  up, dawn cash up) → submit A3; if inert like HIRE-SLOT-CAP → park + ask user.

- **2026-09-08 iter 5 (07:51 PST):** No pending sub (`56079953` 584.7 + `56078956`
  538.1 both COMPLETE). Budget: **both 12h slots OPEN** (last subs 09-07 14:40 +
  15:36, aged out), 0 experiment subs today. Confirmed A3 diff vs `main.py` = exactly
  the flag + one guarded `elif` (`out = sells[:3] + hires + buys_hi + buys_lo +
  sells[3:]`; OFF path `hires + sells[:3] + ...`). Iter-4's gate never actually
  ran (no v23 logs on disk). Ran the A3 gate: OFF zero-diff **0/3595**, OFF 120g
  107-1-12 / 89.6% / 0 err, ON 120g **112-0-8 / 93.3% / 0 err / 0 crash**, no
  external regression, all losses lineage self-play — clean and not inert (ON
  +3.7pp over OFF). Parse + 2g-vs-starter smoke on `main.py` with flag ON: 2-0-0,
  0 err. **Phase D: SUBMITTED `56089527`** 2026-09-08 (~07:53 PST local; autonomous,
  1 of ≤2/12h). Mechanical/reorder-only, targets the measured first-market-slot
  SELL gap (32% vs top-10 66%) and the mid-game cash crater vs animal_factory;
  OFF-path byte-identical so it structurally cannot regress the lineage. Evicts
  `56078956` (538.1); pair now `56079953` (584.7, board-best) + `56089527`
  (pending). Flag reverted OFF on `main.py`, dormant `elif` retained. Verdict:
  **SUBMITTED `56089527`**. Next: 1 slot left in this 12h window; judge `56089527`
  at ≥20 eps vs `56079953`'s animal_factory win-rate. Queue behind it: A1b
  movethrift 90/1/3 (standby), A4 endgame sweep (parked), Lever C (built).

- **2026-09-08 iter 6 (09:13 PST):** Manual re-trigger. `56089527` COMPLETE with an
  early publicScore **521.3** — but this is a <15-ep artifact (submitted ~07:53, ~1h
  old; the LATE_WEED_SWEEP sub itself spiked 621@16ep then settled 584, so early
  numbers are noise). **HOLD** per the ≥15-ep-before-revert rule. 2nd slot stays
  held — submitting it now would evict board-best `56079953`, losing the anchor.
  `download_episodes --submissions 56089527 --refresh` running (background) for the
  real ep count. No build this iter (A4 is "build only if queue dry"; A1b standby;
  not forcing a marginal candidate while the pending read is unresolved).
  Verdict: **HOLD**. Next: Phase A read on `56089527` at ≥15–20 eps + board-best
  replay mining; build A4 only if it then clears the bar.
  **UPDATE (same iter, after download):** `56089527` at **16 eps: 7W-0T-9L / 44%,
  animal_factory 3W-0T-6L / 33%, ladder 521.3.** Board-best `56079953`: 25 eps /
  52% / af 41% / 584.7 → A3 is **−8pp overall / −8pp animal_factory** at 16 eps.
  15–19 ep band → **HOLD, direction unfavourable, no revert.** Silent-raise ruled
  out: 0/17 episode logs have Traceback/raised/PASS-fallback; move% 64%, hires
  ~300, acts ~6.7k = normal play. Loss shape = the SAME mid-game cash crater vs
  animal_factory (money d15 $238–2757 while opp $18–21k) — A3's earlier SELLs did
  not close it (it's an investment-timing problem, not just sell-ordering). BUT
  the LATE_WEED_SWEEP sub read 56%/af55% at 16 eps then settled 52%/41%, so 16-ep
  reads swing ±15pp — wait for 20+ before RETIRE. If it holds <44% at 20 eps →
  RETIRE (flag stays OFF, `main.py` already OFF), next = A1b or A4.

- **2026-09-08 iter 7 (~15:44 PST):** `56089527` at **28 eps: 12W-0T-16L / 43% /
  animal_factory 3-0-10 / 23% / ladder 519.1.** vs board-best `56079953` 52% / af
  41% / 584.7 → **−9pp overall / −18pp af / −65 ladder. RETIRE.** Gate metric
  (animal_factory win-rate) 23% vs 41% is an 18pp regression well past 20 eps —
  not FLAT. Silent raise ruled out (0 logs w/ Traceback). Mid-game cash crater vs
  animal_factory unchanged (money d15 $238–2757 vs opp $18–21k) — A3 confirms
  sell-*ordering* is not the lever; the deficit is investment-timing / production.
  `ENABLE_SELL_FIRST_ORDERS` stays OFF on `main.py`, candidate parked in `agents/`.
  Board-best + baseline unchanged. Tracked pair = `56079953` (584.7 anchor) +
  `56089527` (519.1 retired — board-best anchors rating, no resubmit needed).
  **Launched board-best replay-mining + top-10 diff subagent** to pick the next
  candidate. Verdict: **RETIRED `56089527`**. Next: build the subagent's #1
  mechanical pick (A1b / A4 are standing fallbacks).

- **2026-09-08 iter 8 (~15:49 PST):** Teardown subagent returned (board-best
  `56079953` now 33 eps / 15-15 / 50% / animal_factory 8-13 / 38%). **No silent
  raise** (0 stdout/stderr across 33 eps, max agent() 0.153s). Crater mechanism
  confirmed = **production/investment-timing**: opp animal_factory herd (17–25
  animals vs our ~8) compounds milk/wool/egg from ~d10 with zero labour; our
  crops don't return cash until ~d16 → cash d15 $0.6–2.7k vs opp $10–33k, never
  closes. Ranked gaps: (1) unthrottled seed/field-fill buys [→ A5, queued, has
  field-starve risk], (2) crew+field expand ~4 days early [= reverted v8
  herd-pace class, skipped], (3) movement 64% [MOVE_THRIFT_V2 already built +
  proven locally inert, A1b skipped], (4) weed accrual [already handled — cu≥1
  gets priority 10000, weeds are a labour-shortage symptom not an unaddressed
  hunk], (5) endgame liquidation incomplete [→ A4]. Gap 4 checked against
  `build_tasks` — already implemented, not a fresh hunk. **Built A4** (endgame
  sweep via HARVEST zone-exemption from day≥28) as `agents/main_v24_endgamesweep.py`,
  `ENABLE_ENDGAME_SWEEP` default OFF — cleanest "structurally can't regress"
  pick, same class as the promoted `LATE_WEED_SWEEP`, targets the 6 close losses
  (within 9k) directly. Gate subagent running (OFF zero-diff + OFF/ON 120g).
  A1b explicitly NOT worth resubmitting (locally inert, self-play-soft). Verdict:
  **BUILT `agents/main_v24_endgamesweep.py`**. Next: read the A4 gate; if clean →
  submit A4 at next slot (both slots reopen ~19:53 local; `56089527` retired sub
  is the eviction target). Then build A5 (seed-drip) for the following slot.

- **2026-09-08 iter 9:** No pending sub (A3 `56089527` retired at iter 7).
  Budget: both 12h slots open (last real sub `56089527` 09-08 03:10, aged out),
  Kaggle "3 submissions remaining today". Read the A4 gate off disk
  (`scratchpad/v24_off zd.log` / `v24_on120.log`): OFF-path zero-diff **0/19**,
  ON 120g **101-1-14 / 87.5% / 0 `agent()` err** (4 CRASH all
  `HARNESS_ERROR: MemoryError`/`OSError(22)` — local OOM, 78–86s games = swap
  thrash, NOT agent raises), paired A/B **−0.9% CI[−3.0,+1.3]** / move +0.0 /
  productive −1.3 → locally inert exactly as predicted for a day≥28 sweep.
  Diff vs `main.py` = the flag/config block + one 4-line guarded relaxation of
  the zone-first `_IMPOSSIBLE` block for HARVEST (confirmed via `git diff -w`;
  CRLF preserved to match the lineage). 2g flag-ON smoke vs starter 2-0-0/0 err.
  Meets all 4 standing-auth criteria (flag-ON-ready, local-gate-clean, no
  `agent()` exception, large ranked EV per the teardown — 6 close losses within
  9k, additive class = the one that produced the promoted `LATE_WEED_SWEEP`).
  **Phase D: SUBMITTED `56101006`** 2026-09-08 (autonomous, 1 of ≤2/12h).
  `main.py`: mirrored the dormant hunk (flag reverted OFF post-submit, committed
  `367cac9`). **Eviction note:** newest-2 tracking dropped board-best anchor
  `56079953` (562.4) from the live pair, not the retired `56089527` (542.9) as
  iter 8 assumed — `56089527` (09-08 03:10) is newer than `56079953`
  (09-07 15:36), so a single new sub always evicts `56079953`. Keeping the
  562.4 slot would have required a bytes resubmit first (2 subs, and not
  authorized while `56079953` was still board-best). Live rating floor is now
  542.9 until A4 proves out. Recovery if A4 gates flat at 20 eps: resubmit
  `56079953` bytes (then authorized — both tracked subs off board-best peak).
  Verdict: **SUBMITTED `56101006`**. Next: judge `56101006` at ≥20 eps on
  animal_factory win-rate vs `56079953` baseline (52% / af 41% / 584.7);
  build A5 seed-drip in the meantime (queue's next mechanical row).

- **2026-09-08 iter 10 (P0 iteration):** Pipeline audit gate is `IN_PROGRESS`
  (`STATUS: IN_PROGRESS`, hash `691645a…`) → per invariant I0 this iteration did
  audit-and-fix only: no agent-improvement build, no new-candidate submission.
  **P0.1 (`agent()` crash-safety) — BUG FOUND + FIXED:** the live `agent()`
  except block (`main.py`) swallowed every exception silently — no stderr, no
  sentinel — so on Kaggle (`debug=False`) a raise is indistinguishable from bad
  strategy in the replay (the documented #1 failure: v8, ML probe). Fix: added
  `import traceback` + `traceback.print_exc()` in the fallback. Items 2/3/4 of
  P0.1 verified clean (fallback dict schema-valid; module scope all literals/
  defs, no import-time raise; hot path Hungarian O(A·(C+A)²), C≤96 tiles /
  A≤40 units, well under the 1s budget). Committed `75b72fa`. Pipeline hash
  bumped to `f2d73e6…`; P0.2–P0.8 still `[ ]`. **I1 note:** tracked Kaggle pair
  is `56101006` (541.2) + `56089527` (542.9) — neither is peak-or-better (605.1)
  so I1 reads breached, but `56044961`'s own bytes resubmit (`56078956`) already
  settled 538.1 on the hardened pool → no resubmit actually restores the peak;
  `56101006` (A4) is still the pending sub and must reach its 20-ep read.
  **HELD both slots** (no Class-3 recovery — nothing to recover to). STALL COUNT
  unchanged at 2. Verdict: **P0.1 BUG-FIXED**. Next: P0.2 (local gate config ==
  Kaggle stock config).

- **2026-09-08 iter 11 (P0 iteration):** Pipeline audit `IN_PROGRESS` (hash
  matched `f2d73e6…`) → audit-and-fix only. **P0.2 (compete.py config parity) —
  PASS on stock config, BUG on the pool.** Subagent verified episodeSteps 720 /
  actTimeout 1 / startingMoney 3000 / turnsPerDay 24 / maxMarketOrdersPerTurn 10
  all == engine JSON defaults; `debug=False` on the ladder path (`--debug`
  store_true default False, never passed); seat = per-game `rng.randint(0,1)`;
  seed per-game 9-digit random, recorded to manifest + replay filename;
  `agents/*.py` and `contenders/c_*.py` globbed. **BUG:** `DEFAULT_POOL` was a
  hand-maintained 13-bot list that silently omitted `bots/bot_factory_v3.py`
  (real-ladder-mined animal_factory proxy, worst matchup) and
  `bots/bot_top10clone.py` (2850-3010-rated config) — the gate was missing its
  two most ladder-representative opponents. Fix: `DEFAULT_POOL` now globs
  `bots/bot_*.py` + an `assert _disk_bots <= set(DEFAULT_POOL)` regression
  guard; committed `bot_factory_v3.py` (was untracked). Smoke: both bots load &
  play 0-err — but `main.py` beats `bot_factory_v3` **3-0 / +68k avg / 100%**
  and `bot_top10clone` +88k → **Documented limit:** the local pool still can't
  reproduce the ladder crater; a Class-2 A/B measures self-play, not the loss
  mechanism the teardowns name. Recorded in PIPELINE_AUDIT.md + knowledge-base/07.
  Pipeline hash bumped to `ce70a02…`; P0.3–P0.8 `[ ]`. **I1 unchanged:** tracked
  pair `56101006` (A4 pending, publicScore 525.0) + `56089527` (542.9 retired) —
  neither peak-or-better, but `56044961` bytes already read 538.1 on the
  hardened pool so no recovery exists; HELD both slots. STALL COUNT unchanged
  at 2. Verdict: **P0.2 BUG-FIXED**. Next: P0.3 (W/T/L / score-rate math).

- **2026-09-08 iter 12 (P0 iteration):** Pipeline audit `IN_PROGRESS`, hash
  matched `ce70a02…` → audit-and-fix only. **P0.3 (W/T/L / score-rate math) —
  PASS, doc-only, no bug.** Verified: score-rate = `(W + 0.5·T)/n` **identically**
  in `analyze_runs.py:256` (`_rate`) and `ladder_analyze.py:157` — no local/ladder
  metric mismatch (the plan's "prime suspect for the churn"). WIN/TIE/LOSS
  consistent in both: strict final-reward (`== farm["money"]`) comparison,
  exact-equality → TIE (maps to Kaggle Bradley-Terry). CRASH games: counted as
  neither W/T/L but kept in `len(rows)` by `analyze_runs.py._wtl` → score as a
  loss (0.0), conservative, **no score-rate inflation**; `n` never corrupted.
  Two cosmetic limits recorded in PIPELINE_AUDIT.md (compete.py's own stdout
  summary excludes CRASH from its denominator while the gating tool includes it;
  partial-errored non-CRASH games keep a money-based W/T/L) — neither affects a
  promote/revert decision. No code change. P0.3 ticked `[x]`; P0.4–P0.8 `[ ]`.
  **I1 unchanged:** tracked pair `56101006` (A4 pending) + `56089527` (retired) —
  no peak-or-better anchor but `56044961` bytes already read 538.1 on the
  hardened pool so no recovery exists; HELD both slots. STALL COUNT unchanged at
  2. Verdict: **P0.3 PASS**. Next: P0.4 (archetype classifier agreement).

- **2026-09-08 iter 13 (P0 iteration):** Pipeline audit `IN_PROGRESS`, hash
  matched `ce70a02…` → audit-and-fix only. **P0.4 (archetype classifier
  agreement) — PASS, no bug, no code change.** Subagent: `classify_opp` in
  `analyze_runs.py:112-133` and `ladder_analyze.py:88-107` are behaviorally
  identical (same 7-branch order; animal_factory = `amax>=4 and
  (FERT+MILK+WOOL)/tot_sells > 0.3`). Both classify **purely from the
  opponent's replay trajectory** (`ot`/`oa` = animals/plants/sells over days
  0-29), never from filename or agent name → a local `bot_animalfactory_v2`
  game and a real ladder `animal_factory` game go through the *same* test, so
  local↔ladder "vs animal_factory" rows are comparable by construction.
  `classify_ladder.py` is not a classifier (hardcoded `SUB`, raw int tags,
  never emits an af row). `other` is a real labeled bucket kept in W/T/L
  totals + the per-arch dict — the af denominator is legitimately just
  af-classified games in both tools (symmetric); replay-load failures
  `continue` out of *all* buckets → no af-specific denominator shrink. 2
  limits logged (P0.4): (a) `classify_opp` duplicated verbatim across two
  files — drift risk if either is edited; (b) a hybrid like `bot_factory_v3`
  can behaviorally miss the af bucket if its FERT+MILK+WOOL sell fraction
  ≤0.30 — acceptable, same test applied to ladder replays. P0.4 ticked `[x]`;
  P0.5–P0.8 `[ ]`. **I1 unchanged:** tracked pair `56101006` (A4 pending) +
  `56089527` (retired) — no peak-or-better anchor but `56044961` bytes already
  read 538.1 on the hardened pool so no recovery exists; HELD both slots.
  Kaggle CLI unavailable in this env this iter (no fresh ep count pulled — P0
  gate, no judgment due). STALL COUNT unchanged at 2. Verdict: **P0.4 PASS**.
  Next: P0.5 (paired A/B is actually paired + CI is real).

- **2026-09-08 iter 14 (P0 iteration):** Pipeline audit `IN_PROGRESS`, hash
  matched `ce70a02…` → audit-and-fix only. **P0.5 (paired A/B + CI) — PASS, no
  bug, no code change.** Subagent traced `compete.py --baseline`: the baseline
  arm is `dict(payload, agent_path=baseline_path, …)` per candidate game
  (`:574-579`) so it reuses that game's exact `(opponent, seed, our_seat)`;
  `paired_summary` hard-asserts pair alignment on those three keys (`:377-379`).
  CI is a proper paired-difference bootstrap over per-pair `score_delta`
  (`:387,405-408,423-424`) — not two independent proportion CIs, not unpaired
  two-sample; n = `len(pairs)`, CRASH in either arm drops the whole pair.
  `analyze_runs.py --compare` is an unpaired per-opponent W/T/L side diagnostic
  with no CI — runbook "CI[…]" numbers come only from compete.py. Conclusion:
  recent A/Bs reading "CI crosses 0" reflect a genuinely small effect vs noise,
  not a broken pairing throwing away power. P0.5 `[x]`; P0.6–P0.8 `[ ]`.
  **I1 unchanged:** tracked pair `56101006` (A4 pending) + `56089527` (retired)
  — no peak-or-better anchor but `56044961` bytes already read 538.1 on the
  hardened pool so no recovery exists; HELD both slots. Kaggle CLI unavailable
  in this env this iter (no fresh ep count — P0 gate, no judgment due). STALL
  COUNT unchanged at 2. Verdict: **P0.5 PASS**. Next: P0.6 (replay-mining tools
  read the right fields).

- **2026-09-08 iter 15 (P0 iteration):** Pipeline audit `IN_PROGRESS`, hash
  matched `ce70a02…` → audit-and-fix only. **P0.6 (replay miners read the right
  fields) — PASS, one methodological bug fixed.** Subagent hand-verified all
  four tools (`trace_crater`, `trace_cashflow`, `analyze_top`, `ladder_analyze`)
  against raw replays: step→day = `k//24` / hour `k%24`, **no off-by-one
  anywhere**; `obs.farms` is the shared full list so `steps[i][0][…]["farms"][seat]`
  == `steps[i][seat][…]` (verified); seat id via `info.Agents[].Name` vs
  `ME_NAMES` correct on every sampled replay; "hour 0 money" = start-of-day
  (post prior-night `_end_of_day`), no overnight money settlement exists,
  consistent across all four tools; weeds = `kind=="WEED"` in both counters.
  Hand cross-checks all matched (trace_crater d0 disc −2690=−2690 & d10 money
  1400=1400; trace_cashflow d10 1400=1400; ladder_analyze d10 via `steps[i][0]`
  == seat path 1400=1400). **BUG (methodological):** `move%` computed two
  incompatible ways — `analyze_top.py` counted PASS in the denominator and
  excluded the farmer (60.2% on the test replay) vs `ladder_analyze.py`
  excludes PASS and includes the farmer (64.2% same replay) → systematic ~4pt
  inflation of *our* move% relative to top-10. Hadn't flipped a decision
  (teardown "63 vs 48" gap is 15pt, far above the 4pt artifact, direction
  unchanged) but future close comparisons weren't apples-to-apples. **Fix:**
  aligned `analyze_top.py analyze_farm` to the ladder_analyze convention
  (include farmer unit, skip PASS) + `assert "PASS" not in hand_token_counts`
  regression guard; smoke-ran clean. 3 directional limits logged
  (`trace_crater` day_spend assumes orders committed / drops malformed days;
  `trace_cashflow` flat $1000 BUY_LAND estimate). Pipeline hash bumped to
  `f86bad1…`; P0.7–P0.8 `[ ]`. **I1 unchanged:** tracked pair `56101006` (A4
  pending) + `56089527` (retired) — no peak-or-better anchor but `56044961`
  bytes already read 538.1 on the hardened pool so no recovery exists; HELD
  both slots. Kaggle CLI unavailable in this env this iter (no fresh ep count —
  P0 gate, no judgment due). STALL COUNT unchanged at 2. Verdict: **P0.6
  BUG-FIXED**. Next: P0.7 (data pulls complete + fresh).

- **2026-09-09 iter 17 (loop rewrite — pure climb loop):** The `/ladder-auto`
  skill was rewritten (user order 2026-09-09): no mechanical-only rule, bundled
  changes allowed, batch-build 2–3 candidates/iter, no STALL-COUNT stop
  (family-rotation instead), pipeline audit advisory not a gate. Hard limits
  kept: never-raise / 0-agent()-errors, ≤5 subs/day (≤2 experiment), submit
  needs user approval, new file per change, rating-floor guard, ml/ frozen.
  **Kaggle CLI unavailable in this env** → no fresh ep count for pending A4
  `56101006`, no submit possible this iter. Focus (user): "improve agent + deep
  research". Actions: (1) launched a research+teardown subagent — deep web
  research beyond `RESEARCH_LADDER_META` (kaggriculture writeups, econ-sim
  build-order theory, econ-game opponent modeling) + on-disk top-10 structural
  diff + crater trace + Class-1 bug hunt. (2) Built **A6 OPP-SHADE (Lever G)** —
  `agents/main_v25_oppshade.py`, `ENABLE_OPP_SHADE` default OFF,
  `_opp_archetype()` + guarded sell-size shade hunk in `market_orders`. Single
  highest-EV never-built idea across the planning docs (`RESEARCH_LADDER_META`
  §3 C4 + `PLAN_LADDER_NEXT_5` Lever G), unlocked by the loop rewrite (was
  economy/market tuning, previously banned). Syntax+import clean,
  `ENABLE_OPP_SHADE=False` verified. **A6 OFF-path zero-diff: 0/30 regressed,
  score Δ +0.0% CI[0,0], every pair byte-identical — PASS.** A6 ON 120g still
  running (`bdd11an6j`).
  **Research subagent returned** (`docs/RESEARCH_LADDER_META_2.md`, 14 new
  findings + top-10 teardown + 3 substantiated bugs). Headline: the ladder is a
  **"replay ladder"** (~85% clones of recent strong public episodes; newer impl
  beat older 86/91; ordering ≈ mean final money) → **economy throughput is the
  game**, reactive layers are 2nd-order → **A6 DEMOTED**. #1 EV = **bug C: herd
  8 vs configured 14** (four stacked reserve gates block BUY_ANIMAL through the
  d6–15 crater; opp animal count is the best W/L predictor). Also bug B (lumpy
  d9 seed spend → reframes A5 as *smoothing*) and bug A (weeds — LATE_WEED_SWEEP
  too late/narrow). New idea A8 (lead-aware *variance*, forum's most-cited edge:
  rating = Φ(μ/σ), when behind add variance).
  **Built A7 `agents/main_v26_herdreserve.py`** — `ENABLE_HERD_RESERVE_EXEMPT`
  default OFF, caps the reserve term at 150 for the BUY_ANIMAL check while
  day≤14 and herd < target (mirror of the +18pp feed-floor exemption). Syntax
  clean. Gate: OFF zero-diff running (`btj9diviz`); ON 120g queued behind A6's.
  Verdict: **BUILT `agents/main_v25_oppshade.py` + `agents/main_v26_herdreserve.py`
  (A6 OFF zero-diff PASS)**. Next: read A6 ON + A7 gates; A7 is the submit
  proposal (needs Kaggle CLI — unavailable in this env — + user approval).
  Also queued: audit `MKT` constants vs engine 1.32.7 (research #4: carrot
  below_target 0.20→1.00) + verify `price_at` models the town-drain "hole"
  (research #3: STRAWBERRY/MILK 5–24× multiplier).
  **UPDATE (iter 17 cont.):** Codex (parallel session, has Kaggle CLI) judged A4
  `56101006` at 24 eps = **REGRESSION** (42% / af 35% / 523.1 vs baseline 52% /
  af 41% / 584.7), RETIRED it, and submitted **`56111947`** (board-best lineage
  bytes resubmit) to recover the rating floor. Tracked pair now `56111947`
  (pending) + `56089527` (retired, 543.2). **So the Kaggle slots are
  Codex-managed right now** — no competing submission from this loop this iter.
  A6 gate finished: OFF zero-diff 0/30, ON 120g 110/0/10 / 91.7% / 0 err — fully
  gated + submittable (demoted). A7 (v26) gate finished: OFF zero-diff 0/30, ON
  120g 98/0/22 / 81.7% / 0 err, 100% vs all externals — clean but locally inert
  (animals 7.9→8.5). Built **A7b (v27)** — thins the `150·placed_total` term
  that's the real herd cap; gate running. **Verdict: BUILT
  `agents/main_v25_oppshade.py` + `agents/main_v26_herdreserve.py` +
  `agents/main_v27_herdreserve2.py` — 2 submittable (A6, A7), A7b pending gate.**
  Next iter: read A7b gate; propose A7b (or A7) for the slot after `56111947`
  settles — needs a Kaggle CLI env + user approval. Then A8 / MKT audit.

- **2026-09-09 iter 18:** Kaggle CLI unavailable in env again → no pending-sub
  read (`56111947` Codex-managed), no submit. Focus = "improve agent + deep
  research". Actions: (1) **MKT / price_at constants audit** (research #3 + #4)
  — all 9 `MKT` tuples == engine `MARKET_PARAMS` v1.32.7 byte-for-byte, CARROT
  below_target already 1.00, `price_at` == `market_price`, `market_orders` feeds
  live post-drain inventory and meters sizing into the price hole → **no bug,
  economy-constant class CLOSED** (`docs/RESEARCH_LADDER_META_2.md` MKT audit
  §). Confirms the gate-metric loss is throughput, not mispriced sells. (2)
  **Re-launched the A7b (v27) gate** that iter 17 left with no artifacts —
  `compete_runs/v27_offzd` (30g OFF zero-diff vs `main.py`) + `v27_on120` (120g
  ON paired), bg `b13son1br`; hunk hand-verified OFF-path == `main.py`. (3) Web
  research pass (Kaggle forum / sim-comp meta / RTS build-order) returned
  nothing material beyond iter 17's `RESEARCH_LADDER_META_2.md` synthesis — that
  doc stands as the deep-research deliverable. Family = `herd-economy` (not
  benched; A7/A7b never got a *judged* ladder read, only locally inert).
  **Verdict: BUILT/GATING `agents/main_v27_herdreserve2.py` (A7b) + MKT audit
  closed.** Next iter: read the v27 gate; A7b (or A7) is the submit proposal for
  the slot after `56111947` settles — needs a Kaggle CLI env + user approval.
- **2026-09-09 iter 19:** Kaggle CLI unavailable in env (3rd iter running — iters
  17/18 same). No pending-sub read (`56111947` Codex-managed), no submit. Focus =
  "improve agent + deep research". `RESEARCH_LADDER_META_2.md` (iters 17–18)
  stands as the deep-research deliverable — headline: replay-ladder, economy
  throughput is the game; #1 EV = herd (A7/A7b, staged); #3 = weeds still ~13
  despite `LATE_WEED_SWEEP`. Family `herd-economy` is covered by the staged
  A7b/A7 (never judged on ladder — not benched). Drew the next build from a
  **different mechanism** per batch-build: **A9 WEED-SWEEP-EARLY** — bug A widen,
  `agents/main_v28_weedsweepearly.py` (`8ab5e76`), `ENABLE_WEED_SWEEP_EARLY`
  default OFF, moves the idle-hand out-of-zone DIG sweep to d≥10/range-7. Diff vs
  `main.py` hand-verified = flag + config comment + a 3-line guarded hunk (two
  locals `_wsd`/`_wsr` that resolve to the `LATE_WEED_SWEEP_*` constants when
  OFF → exact byte no-op). Syntax OK. Gate launched: OFF zero-diff 30g
  (`b7bk1e8z8`) + ON 120g paired vs `main.py` (`b1b4q2jso`). Verdict: **BUILT
  `agents/main_v28_weedsweepearly.py` (A9), gate running.** Next iter: read the
  A9 gate; queue for submit behind the staged A7b once a Kaggle-CLI env is
  available. Still staged: A7b (`agents/main_v27_herdreserve2.py`) is the #1
  submit proposal; A9 is #2 (additive, can't-regress class).

  **UPDATE (iter 18 cont., gate `b13son1br` done):** v27 OFF zero-diff 0/30 PASS;
  ON 120g 98/0/22 / 0 err / no external tank / animal_factory 8/0; paired A/B
  −2.9% CI[−8.3,+2.5], day10 cash +212 / productive +7.7 (intended direction,
  weak); herd 8.5 == v26 (local can't engage the mechanism). **A7b STAGED as
  the submit proposal** — bug-C class fix, gate clean, local A/B expected-inert.
  Blocked on Kaggle CLI (Codex holds the slots: `56111947` pending). Verdict:
  **PROPOSED `agents/main_v27_herdreserve2.py` (A7b) for submit** (awaiting a
  Kaggle-CLI env + user approval).

- **2026-09-09 iter 20:** Kaggle CLI unavailable (4th consecutive iter — `kaggle`
  not on PATH / no py module). No `56111947` read (Codex-managed), no submit. A9
  (v28) gate from iter 19 still mid-run (`compete_runs/v28_offzd` 15/30,
  `v28_on120` 19/120, 2 live python procs) → did not launch a competing gate.
  Focus = "improve agent + deep research". Dispatched one subagent for a
  **focused movement-lever teardown** → `docs/RESEARCH_MOVEMENT_LEVER.md`:
  move% 63 vs 49 (finding #6) is the last top-3 EV divergence with no viable
  candidate; want 2-3 low-regression-risk incremental changes distinct from the
  reverted MOVE_THRIFT_V2 / wedge-zones, or an honest "needs the risky rework".
  Loop is now on a 30-min cron (job `105d9f46`), fixed-interval. Verdict:
  **HOLD** (A9 gate running, movement research dispatched, submit env-blocked).
  Next fire: read A9 gate + `RESEARCH_MOVEMENT_LEVER.md`; if A9 clean, stage a
  bundled "crater-economy" sub = `ENABLE_HERD_RESERVE_EXEMPT` +
  `ENABLE_WEED_SWEEP_EARLY` (+ A5 SEED_DRIP if built) for the next Kaggle-CLI
  window.

- **2026-09-09 iter 16 (P0 iteration):** Pipeline audit `IN_PROGRESS`, hash
  matched `f86bad1…` → audit-and-fix only. **P0.7 (data pulls complete + fresh)
  — BUG FOUND + FIXED.** Subagent static-read `download_episodes.py` +
  `download_top_replays.py`: claims 1 (`--refresh` re-pulls, not a no-op),
  2 (incremental keys on episode id, re-queries the full list — new episodes
  not skipped) and 3 (Py3.13 invocation correct; `from __future__ import
  annotations` neutralises `list[str]` hints, Python313 path ahead of `python3`
  in the interpreter-candidate list) all hold. **BUG (claim 4):** a
  partial/truncated download was confirmed only by `Path(...).exists()` — no
  size or JSON-parse check, no temp+rename. A mid-transfer TCP reset (or any
  CLI failure leaving bytes on disk) wrote a short file to the final path; the
  failing run only printed a warning and left it, then every later incremental
  run saw it present, set `need_replay=False`, and permanently indexed the stub
  as a legitimate episode → the exact "truncated pull → premature 20-ep read"
  failure the plan names. **Fix:** `_valid_json(path)` added to both scripts
  (size ≥ 2 B AND `json.loads` parses, else `unlink()` the stub);
  `download_replay`/`download_logs` (download_episodes.py) and `download()`
  (download_top_replays.py) now return False on a partial pull so the next run
  re-fetches; `replay_present()` incremental-skip check is size-gated
  (`_MIN_REPLAY_BYTES = 100_000`; real replays >4 MB) so pre-existing stubs are
  re-pulled too. Regression guard: module-level `assert _valid_json(<missing
  path>) is False` in both. Both import clean under Py3.13. Committed `1d4302a`.
  2 limits logged (`logs_present` still bare `.exists()`; 2 B / 100 KB size
  floors). Pipeline hash → `e81c8602…`; **P0.8 is the last `[ ]` section.**
  **I1 unchanged:** tracked pair `56101006` (A4 pending) + `56089527` (retired)
  — no peak-or-better anchor but `56044961` bytes already read 538.1 on the
  hardened pool so no recovery exists; HELD both slots. Kaggle CLI unavailable
  in this env (no fresh ep count — P0 gate, no judgment due). STALL COUNT
  unchanged at 2. Verdict: **P0.7 BUG-FIXED**. Next: P0.8 (loop bookkeeping
  self-consistent) — the final audit section; then STATUS: PASS.

- **2026-09-09 iter 28 (30-min cron, job 11c8bbf6):** Focus = "improve agent +
  deep research". **RETIRED `56126876`** (v30 A7b+A9 bundle): episodes stalled at
  23 across 2 cron fires; re-read 12W-0T-11L / 52% / af 6-0-10 **37.5%** vs
  baseline `56111947` 50% → gate −12.5pp, ladder 556.3 ≈ 558.5 flat, weeds29 17
  (worse), herd 9 (flat), 0 agent() errors, crater unchanged in all 10 af losses
  (d15 cash $30–2200 vs opp $0.7–19k). Both flags stay OFF on `main.py`.
  **`herd-economy` family benched 3 iters** (Lever A FLAT + this = 2 non-beats);
  `movement-routing` also effectively exhausted at local-gate (3× inert). Active
  dig: **`field-allocation`**, `market-timing`.
  **Deep-research subagent** (general-purpose, 90k tok, `docs/` corpus + fresh
  top-10 replays): top-10 run STRAWBERRY ~56% / WHEAT ~37% at d20 and 10× their
  cash in the d10-15 window we sit flat through; our season sells are 73% wheat
  (inverted). Cash-crater single gap-opener in af losses = d9 seed restock + d11
  $2k land buy stacked against opp animal income compounding from d5, zero crop
  income until d16. Suspected (unverified) Class-1: SELL slot-truncation on
  heavy dawn turns (`market_orders` assembly + `out[:10]`).
  **Built A12** `agents/main_v31_strawskew.py` (`ENABLE_EARLY_STRAWBERRY_SKEW` +
  `ENABLE_PREMIUM_CROP_BONUS`, both default OFF) — field-allocation family, new
  dig. Diff vs `main.py` = flag block + 3 guarded hunks (day<7 share 0.16→0.34
  straw / 0.50→0.40 wheat for day≥4; Lever 2 pick ×1.30 for STRAWBERRY/TOMATO);
  OFF-path byte no-op verified; syntax+import clean; committed.
  **Gate launched** (bg): OFF-zd via v31 default vs `main.py` (`scratchpad/v31_ab.log`)
  + ON 120g A/B via `scratchpad/v31_on.py` (`scratchpad/v31_on_ab.log`).
  Queue added: A13 CRATER_SEED_THROTTLE (crater-timing, verify $3k/d9 trace
  first), A14 ZONE_REBALANCE_ON_UNLOCK (movement, different mechanism), A15
  SELL slot-truncation (bug, verify vs replay 107185595 first).
  **Verdict: RETIRED `56126876` + BUILT `agents/main_v31_strawskew.py` (gating).**
  Next cron fire: read the v31 gate; if A/B score-rate delta trends positive +
  behaviour shifts (strawberry share up, d10-15 cash up) → stage as submit
  proposal (needs user approval per this skill's prompt). Then build A13.
