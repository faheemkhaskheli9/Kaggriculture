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
| A3 | SELL-FIRST market ordering — reorder `market_orders` slot assembly so the top premium SELL(s) fill slot 0 before HIRE / BUY_SEED / BUY_PRODUCT on turns where inventory value > 0. Orders process in slot order and >10 overflow is dropped. | mechanical (execution-efficiency) | **NEW — 2026-09-08 iter 3 replay-mining subagent, gap #4.** Our first market slot each turn: SELL 32% / BUY_SEED 28% / HIRE 22% / BUY_PRODUCT 17%. Top-10: **SELL 66%** / BUY_PRODUCT 15% / BUY_SEED 13% / HIRE 5%. Top-10 convert inventory→cash before spending; we lead with hires/seed buys. Directly targets the mid-game cash crater (deficit onset ~d6 close losses, ~d11–12 blowouts vs animal_factory). Not on the reverted list. Cadence sub-gap (#5): we touch market on 26.7% of turns vs 41.8% — same fix family (open the market SELL-first more often). | mechanical class + targets the dominant loss mechanism (cash-starved animal_factory games). Plausibly the highest-EV unbuilt item. **BUILT 2026-09-08 iter 3** as `agents/main_v23_sellfirst.py` (copy of `main.py` + flag default OFF + one guarded `elif` in `market_orders`: `out = sells[:3] + hires + buys_hi + buys_lo + sells[3:]`). `ENABLE_TXCASH_FORECAST` already puts sells[:3] ahead of buys; this moves them ahead of `hires` too, so the dawn heavy-hire turn no longer pushes cash-in past the 10-order cap. Gate 2026-09-08 iter 5: OFF zero-diff **0/3595** (5-seed paired), OFF 120g 107-1-12 / 89.6% / 0 err / starter 3-0-0, ON 120g **112-0-8 / 93.3% / 0 err / 0 crash**, no external-archetype regression (animal_factory 11-0-0), all 8 losses lineage self-play. Not inert (ON +3.7pp over OFF, unlike HIRE-SLOT-CAP). **SUBMITTED 2026-09-08 as `56089527`** (autonomous, 1 of ≤2/12h; evicts `56078956` 538.1). Flag reverted OFF on `main.py` post-submit; dormant `elif` retained. | submitted `56089527` | `ENABLE_SELL_FIRST_ORDERS` |
| A4 | ENDGAME LIQUIDATION SWEEP — on the final day, route idle/near hands to HARVEST standing crops and clear weeds so the board is empty at step ~718 (auto-drop to shed still catches inventory, but standing plants/weeds are worthless). | mechanical | **iter 3 subagent gap #2 (also parked from iter 1).** At final step we leave 8 plants + 17 weeds standing (25 tiles) vs top-10 2 plants + 0 weeds; our d29 crop count is also lower (14 vs 24) — top-10 grow to the wire AND clear. | Real but smaller than A3; "harder to fix without more hands / better final-day routing" — not a clean additive hunk. Build only if A3 is submitted and the queue is otherwise dry. | parked | `ENABLE_ENDGAME_SWEEP` |
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
