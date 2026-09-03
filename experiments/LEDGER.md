# Kaggriculture improvement ledger

One row per agent version. Fill it in as each version is benchmarked. See
`PLAN_300K_WORKFLOW.md` for the loop that produces these rows and the promote rule.

**Columns**
- **Ver** — `vN`; the file is `experiments/main_vN.py` (a promoted version is also copied to `main.py`).
- **Parent** — version this forked from.
- **Change** — the *single* multiplier / hypothesis (ref PLAN_300K §2: M1..M5, §3).
- **Local mean / p10** — `test.py` paired OVERALL own-coins, candidate side.
- **vs incumb** — paired coin delta vs the `--incumbent` (W-T-L in parens).
- **Err / unsold / ms** — error count, terminal unsold units, ms/step (must be 0 / ~0 / ≤4).
- **Ladder** — Kaggle score once the submission has real episodes (pull with `download_episodes.py`).
- **Tokens** — new-tokens for the session(s) that produced this version, from `experiments/TOKENS.md`.
- **Status** — `promoted` / `reverted` / `pending` (+ short reason if reverted).

| Ver | Date | Parent | Change | Local mean / p10 | vs incumb | Err / unsold / ms | Ladder | Tokens (new) | Status |
|---|---|---|---|---|---|---|---|---|---|
| v1 | 2026-09-02 | — | Gen A baseline: 6 hands, carrot-heavy, 1 land, no animals | ~27k | — | 0 / — / — | **332.9** (sub 55945642) | n/a | superseded |
| v2 (main_600) | 2026-09-02 | v1 | tomato/strawberry lean, 2 land buys, movement halved | ~40k | — | 0 / — / — | **477.1** (sub 55952549) | n/a | superseded |
| v3 | 2026-09-02 | v2 | persistent per-unit zones; priority task engine; crop-mix lean | ~52k | — | 0 / — / — | — | n/a | superseded |
| v4 | 2026-09-02 | v3 | animals on (COW-heavy), 12 hands, fertilizer collect, land 2-3 | ~55k | +24k vs v3 | 0 / — / — | seeded 600 only (1 ep) | n/a | superseded |
| p2 | 2026-09-02 | v4 | endgame-only fork: liquidate from d29 h0, crew disband, SELL-first d29 | ~55k | +300..+827/run vs v4 (81-0-39) | 0 / 0 / ≤4 | — | n/a | folded into v5 |
| v5 | 2026-09-02 | v4+p2 | week-1 crop front-load + land-to-4 (incl $4k) + hold-13-hands + animal_tiles empty-only + p2 endgame + test.py instrumentation | **60.6k / ~49k** | +9.4k vs v5-snap (7-0-1); +7.4k vs p2 (6-0-2); starter 58k→70k | 0 / ~3 / ≤4 | *pending submission* | ~2.5M (2026-09-02, est) | **promoted → main.py** |
| v6 | 2026-09-02 | v5 | field-fill (PLANT prio 1800→3200, DIG 1500→2800) + wedge zones + endgame last-useful-tick (marginal-price market maker split off — regressed −7k vs starter in probe, floods the scarcity curve) | 54.5k / 36.1k | **−8.2k vs v5** (OVERALL 12-game suite); wheatflood −10k, premium −14.6k, animalfarm −3.6k, starter flat | 0 / 8 / ≤4 | — | ~1.3M (2026-09-02) | **reverted** — every isolated cluster is neutral-vs-starter but net-negative vs the active bots; same pattern as PLAN_300K s1–2. Harness can't gate this. `experiments/main_v6.py` kept for reference. |
| v7 | 2026-09-02 | v5 | PLAN_V6 Track A / A3: drop v6's angular-wedge `unlocked_cells` (isolated as the v6→v4 regression, 25%→83% when removed); keep only a retuned field-fill — PLANT 1800→**2400**, DIG 1500→**2200**, both **below** comfort-water 2600 so a live plant is never starved to plant/dig; DIG zone-only | ~64k suite / p10 ~24-29k | **30g conf**: vs `agents/main_v4.py` **27-0-3 (90%) +11.8k p10 29k**; vs `bot_animalfarm` **30-0-0** 55.8k. 12g: starter **70.6k (> v5)**; wheatflood **+2.5k/+6.7k p10 vs v5**; premium byte-identical to v5; v5 h2h 4-4-4 −155 | 0 / 3-5 / ≤4 | *pending submission* | (this session) | **promoted → main.py** — recovers the v4 matchup v6 broke (25%→90%), no regression elsewhere. A2 (opp-conditional wedge) + A4 (endgame) both unnecessary: v7 beats starter without wedges, unsold already ≤ v5. |
| v8-probe (herd-pace) | 2026-09-02 | v7 | PLAN_V6 Track B / B1: herd pacing — steep week-1 working-capital floor on the animal buy (2200 <d6 / 1100 <d10 / 400 <d15) + 2 buys/turn d6-14, to stop the day-1 herd dump so the field compounds d12-20 | 34k / p10 27k | **0-0-12 vs BOTH `agents/main_v4.py` and `main.py` v7**; d20 coins 4-5k vs v7 ~15k. Mild variant (`900 if day<4 else 300`): vs v4 +6k (v7 +13k), **vs v7 4-0-8 −2.3k** | 0 / 5 / ≤4 | — | (this session) | **reverted** — delaying the herd just deletes the early milk that is v7's mid-game engine; "compounding" never appears locally. Track-B caveat (`06 §6`): local opponents don't punish the cash crater. Parked for the portfolio / ladder. v8 files deleted. |
| v8b | 2026-09-02 | v7 | PLAN_LADDER_ECON L1 (herd/land untouched): thin `seed_reserve` $60 for seed+feed buys only + seed cap 12→24 + n_units*2→*3 lookahead + staples sell-every-turn from d3. Isolated as 4 probes (`experiments/probe_c1..c4.py`). | c1 alone: starter 68.5k→67.4k (−1k), **`bot_animalfarm` 62.2k→49.4k (−13k, min 22k)**. c2 (seed cap): starter −12k, d20 craters to 2.6k. c8c (c1+c4): starter −7k, animalfarm −14k. | 0 / 2-8 / ≤4 | — | (this session) | **reverted** — every sub-lever is neutral/positive on a 2-seed starter probe and regresses at 6 games vs `bot_animalfarm` (the matchup that decides ladder rank). Same pattern as v6 / v8 / PLAN_300K s1-2: **the local harness cannot gate a main.py economy change** (`PLAN_LADDER_ECON §2`). Files kept in `experiments/` for reference; real gate = a ladder read after submitting v7. |
| v8 (shipped: agents/main_v8.py) | 2026-09-02 | v7 | **Ladder-motivated, not local-gated.** 105-episode `tools/ladder_analyze.py` read: agent loses ~83% vs "animal_factory" opponents (~6W-30L, ~40% of the pool); everything else ~even. Two fixes: (a) wheat sell/rebuy churn — feed-need now counts hand-inventory wheat + standing wheat plants, buy feed wheat only from day 5 and never into a >1.25x price spike; (b) drop the `opp_animals>=4` herd crouch (was COW3/GOOSE3/SHEEP0 cap6) — vs an animal-heavy opp, MATCH with COW8/GOOSE4/SHEEP1 to claim our own free-fertilizer line. `agents/main_v8.py`. | not gated — machine saturated by a parallel `ml.optimize` 16-worker job; single-game smoke vs starter clean (32.3k, 0 err) | — | 0 / ~3 / ≤4 | *pending submission — the real gate* | (this session) | **pending** — submit and compare the `vs animal_factory` row against v7's 1-7/2-10. `agents/main_v7.py` is the rollback. test.py OOM fixed (it retained every full replay). |

<!-- template row:
| vN | YYYY-MM-DD | v(N-1) | M# one-line hypothesis | XX.Xk / XXk | +Xk vs main.py (W-T-L) | 0 / 0 / ≤4 | — | X.XXM | pending |
-->
