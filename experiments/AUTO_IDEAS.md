# AUTO_IDEAS.md — ranked idea backlog for the /ladder-auto meta-loop

Created 2026-09-07 by `/ladder-auto` iteration 1. Re-read before every write;
Codex may share the tree. Format below. Status vocab: `queued` / `built` /
`submitted` / `gated-flat` / `reverted` / `parked`.

The LEDGER is authoritative for per-version history; this file is only the
forward queue + why each item is/ isn't above the submit bar.

| id | idea | class | evidence | est. ranked EV | status | flag name |
|---|---|---|---|---|---|---|
| A0 | LATE-WEED-SWEEP — an idle hand clears the nearest out-of-zone weed within 4 tiles from day≥20 (relaxes the hard DIG zone-restriction in `assign()` for hands that have no task this turn) | mechanical (execution-efficiency) | 2026-09-07 teardown subagent: board-best `56044961` carries ~13 weeds at d25–29 (20–29 in the animal_factory blowout losses) vs top-10 median ~0; weed accrual correlates with the weaker loss games. NEW — not on the reverted list (v6 DIG-2800 pulled hands *off crops*; this only ever redirects an already-idle hand → structurally cannot regress). Built `agents/main_v21_lateweedsweep.py`. Gate: OFF zero-diff 0/24; ON 24-pair 0/24/0 (fully inert locally); ON 120g 111-4-5 / 94.2% / 0 err / weeds29 unchanged / no external loss. | ladder-only EV — local league can't reproduce the animal_factory weed pile-up. Worst case FLAT (like Lever A), never a regression. **25-ep read: PROMOTED on the concurrent A/B — `56079953` (ON) 52% / af 41% / 598.5 vs `56078956` (OFF control, same window) 39% / af 24% / 529.0 → +13pp / +17pp / +69.** Watch for convergence on continued accrual. | **PROMOTED `56079953`** (`c83ae34`) | `ENABLE_LATE_WEED_SWEEP` |
| A1 | Movement-thrift v2, 35/2/2 constants — progressive far-walk penalty + idle-reposition deadband + same-tile op batching in routing `assign()` | mechanical | `analyze_top.py` on 22 top-10 replays: board-best spends 63% of hand-actions moving vs top-10 median 48%. Largest mechanical gap. Built `agents/main_v18_movethrift2.py` `ec7d442`, local-clean (OFF zero-diff 24/24; ON 120g 115-0-5 / 0 err; 96-pair A/B move −0.2pp / score +1.0% CI[−3.1,+5.2] crosses 0, every external archetype +0.0%). | ladder-only, unproven; local read is a near-no-op (−0.2pp move). Same profile as Lever A (flat) / Lever B (regression). **Below the "large expected gain" bar** until a fresh teardown re-elevates it. | built | `ENABLE_MOVE_THRIFT_V2` |
| A1b | Movement-thrift v2, 90/1/3 escalation — same flag, FAR_PENALTY 35→90 / FAR_FREE 2→1 / IDLE_SLACK 2→3 | mechanical | `agents/main_v19_movethrift3.py` `4125e8f`. ON 120g 102-0-18 / 0 err, all 18 losses lineage self-play (known 90/1/3 self-play softness), no external regression, move% 63% unchanged. | Use ONLY if A1's 35/2/2 is submitted and reads flat — then revert flag and submit this file (no code change, constants already in it). | built (standby) | `ENABLE_MOVE_THRIFT_V2` |
| A2 | Lever C — lead-aware premium liquidation: on days 18–25, if a coarse public-state lead estimate ≥ $10k, sell premium inventory sooner (cap ×1.6, keep ×0.85) to cut late-game variance | economy (risk-mgmt) | `PUBLIC_AGENT_STRATEGY_CATALOG.md` family 15. Built `ca88691`, default OFF. OFF-path zero-diff 3595 steps / 5 seeds / 0 mismatch. ON 120g 102-0-18 / 0 err, no trivial-bot regression. No paired A/B (fires only in already-led games). | Win/loss protector only — never changes a losing game, lowers the chance a led game flips late. Small but non-negative EV. Below A1 in the mechanical-first ordering. | built | `ENABLE_LEAD_AWARE_RISK` |
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
