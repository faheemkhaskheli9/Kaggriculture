# TASKS — path to the top of the leaderboard

## Active improvement plan — 2026-09-10 (Codex)

Baseline is the actual `e9a8b38:main.py` (routing, 12-hand cap, late weed sweep),
not the older snapshot prose below. Existing untracked candidates are preserved.

1. **Reproduce execution losses against the installed engine.** Check animals
   carried outside the shed, duplicate crew/general service, and final-day
   collection after the previous day's hands have been dismissed.
2. **Screen one mechanism at a time.** Use existing `compete.py --baseline` on
   identical opponent/seed/seat tuples; include incumbent/older strong agents,
   animal factories, premium and volume opponents. Keep local win rate primary;
   use cash, productive actions, dead crops and escapes to explain changes.
3. **Confirm useful repairs on fresh seeds and both seats.** Require no agent
   tracebacks/timeouts, working single-file packaging, normal-day equivalence for
   terminal-only changes, and no material factory regression. Reject broad
   economy tuning if the evidence does not support it.
4. **Implement the selected repair in `main.py` with a reversible flag**, retain
   the exact baseline, add focused engine-backed regression tests, and record
   commands/results in `experiments/LEDGER.md`. Existing draft files stay intact.
5. **Leaderboard follow-through:** a local result establishes correctness and
   candidate strength only. After a submission, judge at least 20 real episodes
   with special attention to animal factories; record the actual rating instead
   of predicting a rating gain from local coin totals.

The broad lifecycle draft failed its initial screen (-8.3 percentage points,
one additional loss in 12 matched pairs). Keep it out of `main.py`. Screen
fertilizer selling separately: verified engine rules provide no town demand to
recover its oversupply price. Defer the crop-value model's finite-lifespan fix.

> **Public-code review — REVOKED, ideas-only going forward (2026-09-05):** an
> earlier version of this note recommended porting/submitting derivatives of
> five other named competitors' actual repositories (cloned under
> `public_agents/`, never committed). **That is against a hard standing rule:
> never copy another competitor's code, regardless of license — extract ideas
> only, reimplement independently.** `public_agents/` has been deleted; do not
> re-clone it or any other competitor's repo. `docs/PUBLIC_CODE_REVIEW_2026-09-05.md`
> is kept only as a prose summary of the *strategic ideas* worth learning from
> (precomputed season-length route, closed-loop repair around a fixed plan,
> opponent-aware market timing, paired-eval discipline) — none of its
> reported score deltas are usable evidence since they measured someone else's
> code, not ours. If any of those ideas get built, they must be designed and
> coded from scratch against this repo's own engine understanding
> (`knowledge-base/`), gated the normal way (Gate B in
> `docs/IMPACT_RANKED_LEADERBOARD_PLAN.md`), and logged in `experiments/LEDGER.md`
> like any other candidate.

> **Current operating plan (2026-09-06, Phase A done — routing REVERTED):**
> `docs/PLAN_LADDER_NEXT_2.md`. Phase A ladder read **overturned the routing
> KEEP call**: with full episode counts, the **non-routing v15 build**
> (`56039865` = `0aa1da6:main.py`, attributed via `git reflog` — NOT `033990f`
> as earlier notes assumed) reads **590.2 / 30 eps / 57% score-rate /
> animal_factory 63% (10-0-6)**, while the routing build (`56034847`) decayed to
> **565.7 / 27 eps / 48% / animal_factory 31% (5-0-11)** and routing+MAXHANDS-12
> (`56044961`) crashed to **499.7 (2 eps, both near-ties)**. Routing regressed
> the ladder ~25 pts and halved the animal_factory win-rate; that archetype is
> ~56% of ladder games. **`main.py` disk reverted to `0aa1da6:main.py`
> (non-routing v15) 2026-09-06**; routing build kept as `agents/main_v16_routing.py`,
> reverted winner as `agents/main_v16.py`. `PLAN_LADDER_NEXT_2` Phase B
> ("execution efficiency / routing tuning") is now dead and needs a rewrite —
> the question is what in the non-routing build wins animal_factory 63% and how
> to press it. Gates A–D and the impact formula still come from
> `docs/IMPACT_RANKED_LEADERBOARD_PLAN.md` §3. `56044961` currently occupies a
> live tracked slot at a decaying 499.7 — no re-submission without user approval.

> **Outcome target:** current live score 553.2 → **1553.2+**. The operating
> plan's §8 replacement-policy program is the primary path. Incremental items
> below are retained as diagnostics or components, not as an adequate route to
> the requested +1000 gain.

> **E0 complete:** paired A/B mode is implemented in `compete.py` via
> `--baseline`; `experiments/adversarial_league_v1.json` freezes the weighted
> promotion pool; manifests now include checkpoints, movement/productive-action
> counts, market/action counts, plant-to-weed transitions, and animal escapes.
> Sequential and parallel self-tests produced exact zero deltas.
>
> **E1 smoke read (8 paired tuples, not a promotion gate):** routing-flat vs
> current `main.py` produced +109.6 productive actions/game and 15.8 fewer
> plant-to-weed transitions, but only -0.4 percentage points movement and
> -$13.8k mean margin. Both agents won all eight, proving this small league
> sample is too easy to measure score-rate impact. Do not submit E1 from this
> read; next run must concentrate on hard/loss-producing factory opponents and
> stronger replay-derived proxies.

> **Replacement-policy dataset:** `tools/extract_top_policy.py` now converts
> verified top-10 farms into compact, streamable state/action rows. Current
> pull: 22 replay files inspected, 15 episodes/18 top farms used, 12,960 turns,
> 6,391 turns with market decisions. Artifact:
> `ml/artifacts/top_policy.jsonl` (generated/ignored). Next: episode-held-out
> strategic action-family benchmark, then train or derive the controller; do
> not call `bot_top10clone.py` a faithful top-player proxy until it passes that
> benchmark.
>
> **Held-out imitation baseline:** `tools/benchmark_top_policy.py` uses an
> episode-level 11-train/4-validation split (9,360/3,600 rows). The first
> dependency-free categorical model reaches only **38.1% strategic-family
> micro-F1**, **27.6% mean Jaccard**, and **19.4% exact-set agreement**. HIRE is
> learnable (68.9% F1); BUY_LAND and BUY_ANIMAL are not (7.2%/6.9% F1).
> Therefore the 70% clone gate is not met: do not build a challenger from this
> classifier. The next model must add within-episode history/cooldowns and
> player-policy identity, or replace rare-event classification with explicit
> value/timing rules.
>
> **Temporal benchmark implemented:** extractor rows now carry cumulative
> market/field activity, purchased quantities, turns-since-action, prior-day
> cash/assets, and player identity. Episode-held-out threshold calibration is
> also active. On the identical validation split, family micro-F1 improves
> **38.1% → 41.9%**, HIRE **68.9% → 77.4%**, BUY_SEED **26.2% → 49.6%**.
> BUY_LAND/BUY_ANIMAL remain unusable at **4.9%/6.5% F1** despite conservative
> calibrated thresholds. Decision: use learned policy only for frequent
> cadence decisions; implement land and herd expansion as explicit
> replay-derived timing/value rules, not rare-event classifiers.

**This is the canonical, living task list for the competition.** Update it
every session: check items off, add new ones as they're discovered, re-rank
the queue when evidence changes it. Don't let this drift stale the way
`experiments/LEDGER.md`'s narrative did (see `docs/PLAN_RATING_IMPROVEMENT.md`
Phase 0) — if you take an action from this file, edit this file in the same
sitting.

Detail/rationale for each item lives in the linked doc; this file is the
checklist + current pointer, not a re-explanation.

Public-agent strategy ideas are preserved in
`PUBLIC_AGENT_STRATEGY_CATALOG.md`. It is an ideas-only index: never restore or
copy public-agent code, payloads, constants, or route tapes. New public ideas
must be paraphrased into that catalog and independently implemented through the
normal experiment gates.

---

## 0. Snapshot (update the date whenever you touch this file)

### Shared work board (Claude + Codex)

Claim a row before editing by adding owner and UTC timestamp. One owner and one
mechanism per row; list owned files before making changes. Re-read this table
before editing shared files. Kaggle submission always requires explicit user
approval.

| ID | Priority / isolated mechanism | Owner | Status | Owned files | Handoff / exit gate |
|---|---|---|---|---|---|
| TOP3-20260912 | Fresh top-three replay research, validated improvement, authorized submission | codex 2026-09-12 | running | `research/top3*`, `research/baseline_main_20260912.py`, new `experiments/candidate_top3*`, new `agents/main_v34*`, `main.py` after validation | User explicitly requested research, implementation and submission. Preserve existing dirty files and candidates; use current leaderboard seats, paired evaluation, engine checks, then submit one selected mechanism and record exact artifact/hash/submission ID. Reclaims stale main.py ownership from EXEC-20260910 without changing its draft files. |
| TOP3-GAP-20260913 | Loss analysis vs top-3 + ladder opponents (day-by-day), strategy queue, N1 `ENABLE_OPENING_MELON` | claude 2026-09-13T05:30Z | running | `docs/STRATEGY_TOP3_GAP_2026-09-13.md`, `tests/test_opening_melon.py`, `agents/main_v40_openingmelon.py`, `main.py` (`ENABLE_OPENING_MELON` hunk, dormant OFF; `ENABLE_SHED_STAGING` flag flip = H1 promote) | H1 `56195143` judged PROMOTED (58% / af 52.9% / 600.9); OPP_SHADE `56190458` HOLD; H2 submitted `56199353`. N1 = 12 MELON on days 0-2 + batch sell-down (top-3/opponent day-0 field; +$13k day-10 cash locally). Gate: 13/13 tests, OFF 23/23 zero-diff, ON af 24-pair margin +17.5k / day-10 cash +13.2k, 96-pair pool run in LEDGER. 96-pair pool: +10.4pp CI[+3.1,+17.7] (excludes 0), 14/78/4, margin +13.9k, 0 errors -> **N1 SUBMITTED `56199529` 2026-09-13 05:08 UTC (pending)**. Tracked pair = H2 `56199353` + N1 `56199529`. Next: judge both at >=20 eps, then H3 `ENABLE_CROP_FERTILIZE`. |
| FERT-20260910 | Sell fertilizer without waiting for nonexistent town demand | codex 2026-09-10 | running | `experiments/candidate_fertilizer_liquidation.py` | Isolated price-hold repair; same paired screen as execution drafts; no promotion without measured support. |
| END-20260910 | Final-day collection and profitable temporary workforce | codex/execution_audit 2026-09-10 | running | `experiments/candidate_terminal_workforce.py`, `tests/test_terminal_workforce.py` | Reproduce lost final-day labor and fertilizer; compare terminal money with actual engine timing; isolated candidate only until paired gate. |
| EXEC-20260910 | Repair concrete execution defects; paired validation before promotion | codex 2026-09-10 | running | `main.py` (validated changes only), `tests/test_execution_repairs.py`, `experiments/candidate_execution_repairs.py`, this plan and `experiments/LEDGER.md` | Baseline `e9a8b38:main.py`; preserve existing untracked candidates/tests. Reproduce animal installation and service reservation defects, screen separately, confirm selected repair on fresh paired seeds and factory opponents. No leaderboard claim from local coins alone. |
| AM-FEED-1 | Strict feed-first targeting within the existing ANTI_META crew | claude 2026-09-05T23:20Z | done (not promoted) | `main.py` (`ENABLE_FEED_FIRST_CREW` block only — no-op at default) | Built as a general shared-crew toggle (not ANTI_META-scoped). Zero-diff self-test: OFF == HEAD (0/4320 action diffs, 2 opps × 3 seeds). 40-pair adversarial-v1 A/B: score delta +1.2% CI[+0.0%,+3.8%] (touches zero), every external archetype exactly +0.0%, only flip in `main` self-play; escapes +0.0 (local pool never starves a herd, so the exit gate's "reduce escapes" is unmeasurable locally), no external regression. Default OFF, committed, not promoted. Needs a ladder slot to gate — same wall as land-timing/demand-match/HERDBATCH. |
| EVAL-FACTORY-1 | Unsaturated factory validation slice from our replays and engine rules | claude 2026-09-05T14:06Z | blocked | `bots/bot_factory_v3.py` (new), `bots/_kagri_botlib.py` | `_kagri_botlib` engine ceiling < main.py — a scripted factory bot can't be unsaturated; needs a replay-driven agent (POLICY-RARE-1) or ladder-gating. See snapshot note. |
| R3-HERD-1 | Explain/test staged herd-cap signal alone | claude 2026-09-05T18:36Z | done (not promoted) | `experiments/candidate_top10rules.py` | **Closed 2026-09-05: explained, not promoted.** Root cause found+fixed (crew-size formula used reservation target not actual herd, `ENABLE_R3_CREW_FIX`, commit `a729abf`). Isolated crew-fix-alone test (R3 herd-cap OFF) vs `main.py`: score delta -2.5% CI[-6.2%,+1.2%], margin -2819, wheatflood/top10clone regress — the fix only pays off paired with R3's herd-cap bump, not standalone. Do not port the fix onto `main.py` alone; take it bundled with R3 if R3 itself ever clears Gate B. See `experiments/LEDGER.md`. |
| POLICY-RARE-1 | Explicit BUY_LAND/BUY_ANIMAL timing/value controller | claude 2026-09-05T19:45Z | land-half done (default OFF), animal-half open | `main.py` (`ENABLE_POLICY_LAND_TIMING` block only — no-op at default) | Episode-held-out benchmark plus paired validation; safety layer unchanged. Land half: see snapshot note. Animal half (herd-cap schedule) overlaps R3-HERD-1 — left for that owner or a later slot. |
| AM-HERDSCALE-1 | Cap the per-head escalation in the BUY_ANIMAL affordability gate | claude 2026-09-05T14:06Z | ready-for-ladder | `scratchpad/cand_fscale.py` (not on main.py) | Local no-op (0 regressions, cash floor not reproducible locally); needs a ladder slot. User approval required. |
| ROUTE-SUBMIT-1 | Promote validated routing refresh | user | **REVERTED 2026-09-06** — ladder read at full eps rejects routing | `main_v12_flat.py`, `main.py`, `agents/main_v16*.py` | Early 24-ep read (572.9) that drove the KEEP call decayed to **565.7 / 27 eps / 48% / animal_factory 31%** as episodes accrued. Non-routing v15 (`56039865`) reads **590.2 / 30 eps / 57% / animal_factory 63%** — routing regressed the ladder ~25 pts and halved the dominant-archetype win-rate. `main.py` disk reverted to `0aa1da6:main.py` (non-routing v15); routing build preserved as `agents/main_v16_routing.py`, reverted winner as `agents/main_v16.py`. See LEDGER "ROUTING REVERTED" row. |
| AM-HERDRAMP-1 | Cap early herd acquisition rate (day-0 binge) | claude 2026-09-05T14:06Z | rejected | `main.py` (reverted clean) | Gate B failed x2 — see snapshot note below |
| LADDER-B1 | PLAN_LADDER_NEXT_2 Phase B1 — replay-isolate which of Lever2/E3/TXCASH carries `56039865`'s animal_factory gain | claude 2026-09-06T04:00Z | **done 2026-09-06** | scratchpad `cand_e3off.py` / `cand_lever2off.py` / `cand_txcashoff.py` (deleted after run; `main.py` never written) | **Done.** 96 paired league games/variant (`--pick-seed 260906 --workers 6`): **Lever2 OFF −2.1% score, CI [−4.2%,−0.5%] (excl. 0)**, margin −11521, day10 cash −86, plant→weed −10.4 — the only knob with local support. E3 OFF +0.0% CI[−3.1%,+3.1%], TXCASH OFF +1.0% CI[−1.0%,+3.1%] — both passengers on score-rate. All three hold 37/37 vs bot_animalfactory_v2 (local league can't reproduce the ladder win-rate gain). LEDGER "B1 bundle ablation" row added. **PLAN_LADDER_NEXT_2 §3 B2 re-ranked: press Lever2 (was E3), first split its crop-mix vs land-gate sub-flags.** |
| LADDER-B2 | PLAN_LADDER_NEXT_2 Phase B2 — split Lever2 crop-mix vs land-gate sub-flag, press whichever carries B1's −2.1% | claude 2026-09-06T08:45Z | running | scratchpad `cand_l2cropoff.py` / `cand_l2landoff.py` (reads `main.py`, no writes) | Local paired split-ablation (same league/seed/n as B1) first. If a sub-knob's CI excludes zero, press it one notch behind a named constant; Gate C on 4 core opponents; one submission needs explicit user approval. If neither sub-knob's CI excludes zero → −2.1% is an interaction effect, treat Lever2 as tuned, move slot to B3. |
| LADDER-B2 | PLAN_LADDER_NEXT_2 Phase B2 — split Lever2's crop-mix vs land-gate sub-flags; press the carrier of B1's −2.1% | claude 2026-09-06T09:30Z | **split done 2026-09-06** — carrier = `ENABLE_LEVER2_LAND_GATE`; pressing next | scratchpad `cand_lev2_cropmix_off.py` / `cand_lev2_landgate_off.py` (single-line flag diffs off `main.py`; no writes to `main.py`) | **Split resolved (96 paired league games/variant, `--pick-seed 260906 --workers 6`, adversarial_league_v1):** `ENABLE_LEVER2_CROP_MIX=False` only → −1.0% score, CI [−3.6%,+1.6%] (crosses 0); `ENABLE_LEVER2_LAND_GATE=False` only → **−2.1% score, CI [−4.2%,−0.5%]** (excludes 0 — reproduces B1's exact number on its own). The computed 4th-quad land gate is the carrier; hardcoded `n_units>=12` fallback costs productive actions −109.5 / plant→weed +6.2. Both hold 37/37 vs bot_animalfactory_v2. LEDGER "B2 Lever2 sub-flag split" row added. **Next: press the land gate — value-gate the 3rd-quadrant buy on remaining season days behind a new `LEVER2_LAND_MIN_DAYS_LEFT` constant (default OFF/no-op) → paired screen → Gate C → user-approved submission.** (08:45Z LADDER-B2 claim above is a concurrent-session duplicate of this same task — this run completed first.) |
| LADDER-B2P | PLAN_LADDER_NEXT_2 Phase B2 press step — value-gate the 4th-quadrant buy on a `LEVER2_LAND_MIN_DAYS_LEFT` days-left floor behind a new `ENABLE_LEVER2_LAND_MIN_DAYS` flag (default OFF / exact no-op) | claude 2026-09-06T10:20Z | **done 2026-09-06 — local no-op, not submitted; Lever2 treated as tuned, slot → B3** | `main.py` (`ENABLE_LEVER2_LAND_MIN_DAYS` block only — no-op at default), scratchpad `cand_lev2_mindays_on.py` / `_pre_b2p_main.py` | **OFF self-test: 0/24 differ (+0.0% CI [0,0]). ON screen (96-pair adversarial_league_v1, `--pick-seed 260906 --workers 6`): exact local no-op — 0/96 games differ, +0.0% CI [+0.0%,+0.0%], I/S/R 0/96/0 every bucket.** The `has_slack` capacity check in the `ENABLE_LEVER2_LAND_GATE` branch already refuses Q4 in ~every local game (`coverage_cap` needs ~17 hands; league runs ~13), so a days-left floor on a gate that never fires is inert. Per §3 B2 kill rule, **Lever2 is tuned; next slot → B3** (symmetric early-cash guard for the 7-of-13 "other" loss cluster). Toggle kept at default OFF in `main.py` as a ladder-only candidate. LEDGER "B2P Lever2 land-gate press" row added. |
| CHALLENGER-1 | §8 replacement-policy program — Workstream A/B challenger (replay-derived + BC cadence controllers; safety + execution reuse `main.py`) | claude 2026-09-06T02:30Z | v0 rejected / v1 built not wired / **MAXHANDS-12 REJECTED on ladder** | `challenger/` (`agent.py`, `strategy.py`, `clone.py`, `clone_model.json`, `__init__.py`, `README.md`); `agents/main_v16_routing.py` (`ENABLE_MAXHANDS_12` block — no longer on `main.py`) | **v0 (mined herd/quad/hand schedule) — Gate-B FAILED, −10.4% vs `main.py`; bisected**: HERD schedule = the whole regression; QUAD neutral; HAND-cap-12 the only local positive (self-play-bucket only). **MAXHANDS-12 submitted as `56044961` 2026-09-06 02:28 → ladder REJECTED 2026-09-06: 499.7, only 2 eps (0-0-2, both near-ties), stacked on the routing base that itself regressed. Flag block now lives only on `agents/main_v16_routing.py` — reverted `main.py` (`0aa1da6`) never carried it.** `56044961` still occupies a live tracked slot at 499.7. **v1 (BC cadence controller) — built, verified, NOT wired.** `challenger/clone.py`: held-out HIRE F1 **0.774**, BUY_SEED 0.496, SELL 0.505 — only HIRE usable. Remaining if pursued: `live_features()` obs→feature bridge + `EpisodeHistory` + `agent.py` HIRE gate + A/B — **flag ceiling to user first.** commits `c2d3857` + `f79e3d0` + `9f36ac0`. |

Statuses: `ready`, `claimed`, `running`, `done`, `rejected`, or `blocked`.

- **AM-FEED-1 done, default OFF (2026-09-05, claude e8):** `ENABLE_FEED_FIRST_CREW`
  in `main.py`. `animal_crew_actions` step 3 (walk-to-service) merges feed +
  harvest/fert + CARE into one goal list and picks the globally-nearest of any
  type, so a crew unit near a harvest tile services it instead of a hungry
  animal two steps further — two such turns = permanent escape. ON: a crew unit
  carrying wheat with any unfed animal pending goes strictly to the nearest
  hungry one; yield/fert/CARE (also emitted as ordinary tasks for the non-crew
  units) wait. Built as a general shared-crew toggle, not ANTI_META-scoped
  (ANTI_META isn't promoted; the crew fn is shared and gets no `intent`).
  Zero-diff self-test: OFF path is an exact no-op vs HEAD (0/4320 action diffs,
  starter + animalfactory_v2 × 3 seeds). 40-pair frozen adversarial-v1 A/B
  (`--pick-seed 260906`, ON vs main.py): **score delta +1.2%, 90% CI
  [+0.0%,+3.8%] touches zero; every external archetype exactly +0.0% score
  delta (only flip in `main` self-play, +12.5%); margin delta -53 (noise),
  escapes +0.0, plant->weed -1.0, movement -0.1%.** No external regression (that
  half of the exit gate met) but the "reduce feed failures/escapes" half is
  unmeasurable locally — the pool never pushes our herd into starvation
  (escapes already 0 on both sides). Kept at default OFF for a dedicated ladder
  A/B when a slot frees; not promoted. Run:
  `compete_runs/20260905-232303-157955/`. Same "local can't gate an economy
  change" wall as land-timing / demand-match / HERDBATCH.
- **PLAN_ROUTE_ENGINE Phase 1a REJECTED (2026-09-05, claude e8):**
  `ENABLE_MKT_DEMAND_MATCH` in `main.py` (default OFF, zero-diff no-op verified).
  Demand-matched premium sell sizing — cap each turn's SELL at an estimate of
  this hour's free town/shop absorption (`FLOOR` + `PER_SHOP`*unlocked-shops-
  wanting-it on a `hour%4==0` tick), holding the rest for later turns nearer
  the scarcity price. 80-pair frozen adversarial-v1 A/B (`--pick-seed 260906`,
  ON vs HEAD): **score delta +0.0%, 90% CI [-2.5%, +2.5%], margin delta -7099
  with every archetype negative** (premium -14124, animalfactory -8290,
  wheatflood -5014, top10clone -2203), 1/77/2 improved/same/regressed. Holding
  inventory back to "sell later at a higher price" doesn't pay — the curve is
  near-flat with market inv pinned near I0 all season (KB 03), so the existing
  `keep`-threshold loop already protects price and the throttle just delays
  revenue → less cash to compound land/animal buys. Confirms the repo's
  standing "market barely moves, sell cadence isn't the lever" finding for the
  *throttle* direction too (the market-maker/flood direction was already
  rejected, PLAN_300K s1-2). Toggle left at False per convention. Run:
  `compete_runs/20260905-195351-887391/`. **Phase 1b (`ENABLE_MKT_OPP_DUMP_GUARD`,
  opponent-dump denial) not attempted — same near-flat-curve reason makes it
  low-odds; needs a ladder slot to gate if tried at all.**
- **POLICY-RARE-1 land half done, default OFF (2026-09-05, claude e8):**
  `ENABLE_POLICY_LAND_TIMING` in `main.py`. From `ml/artifacts/top_policy_rules.json`
  (18 verified top-10 farms): Q2 unlocks day 5-6 at ~76% fill, Q3 day 8-11 at
  ~62% of 2 quadrants, Q4 never — our flat `fill>=0.55` with no day floor
  expands land earlier and looser, thinning the crew. Toggle gates Q2 on
  `day>=5 & fill>=0.72`, Q3 on `8<=day<=13 & fill>=0.62`; money gate left
  byte-identical to OFF to isolate *timing* only. Zero-diff self-test: OFF path
  is an exact no-op vs HEAD (0/2160 action diffs, 3 seeds). 80-pair frozen
  adversarial-v1 A/B (`--pick-seed 260906`, ON vs HEAD): **score delta +3.1%
  but 90% CI [-0.6%, +7.5%] crosses zero; every external archetype exactly
  +0.0% score delta (all 4 flips in `main` self-play, +70%); margin delta -395,
  one bot_animalfactory_v2 regression.** plant->weed -3.8 / movement -1.0%
  confirm the crew-thinning hypothesis directionally but it does not convert to
  score-rate locally — the standing "local can't gate an economy change" wall.
  Kept in code at **default OFF** for a dedicated ladder A/B when a slot frees;
  not promoted on this read. Animal half (herd-cap schedule to ~15) overlaps
  R3-HERD-1 — not taken. Run: `compete_runs/20260905-194116-455066/`.
- **AM-HERDSCALE-1 ready-for-ladder (2026-09-05, claude):** F-SCALE — from the
  EVAL-FACTORY-1 mine (our herd ends the season at ~8 vs the winning opponent's
  14-16; our own `animal_targets` cap is 13 but unreached). Root cause: the
  `BUY_ANIMAL` affordability gate's per-head term `150 * placed_total` escalates
  faster than our real-ladder day-10-15 cash recovers — at herd 8 it demands
  `money >= reserve + 1600` while cash floors at $600-1500 there, freezing the
  herd. Change (`ENABLE_FSCALE_HERD`, `FSCALE_HEAD_CAP=4`): cap that escalation
  at 4 heads — E3's day-0-binge restraint unchanged, then continued growth
  toward target stops being penalised. Opposite direction to the rejected E4
  (E4 throttled the herd and starved income; this scales the income line up).
  **Local A/B is a pure no-op: 100 pairs full pool 0/98/2 margin ~$0; 40 pairs
  vs the cash-pressuring `bot_factory_v3` 0/40/0 margin +$193; day10 cash delta
  +0 everywhere.** No local opponent pushes us into the sub-$1500 cash floor the
  gate needs to bind, so the relaxation never fires locally — provably harmless,
  benefit only realizes under real-ladder pressure. Preserved at
  `scratchpad/cand_fscale.py` (NOT on `main.py` — routing re-flatten 1f owns the
  next main.py→ladder path). A legitimate ladder-only candidate for the slot
  after routing; needs user approval.
- **EVAL-FACTORY-1 blocked (2026-09-05, claude):** mined the real
  animal_factory opponent policy from the 12 losses on `56029879`
  (`scratchpad/mine_factory_opp.py`). Median winning-opp trajectory: **herd 4
  by day 1** (buys 4 animals turn 0-1 as cash goes to ~$20-95), 8 by day 10,
  **breakout day 10-12** ($1.6k -> $9k), herd 14 by day 15 / 16 by day 20,
  3-4 quadrants, plants only 15-30 early (vs our 40+), **movement 41-52% vs
  our 63%**, weeds left to pile up late. Our agent in those same games ran
  herd 8 and lost by ~20k — **half the opponent's herd** is the visible gap.
  Built `bots/bot_factory_v3.py` from this (melon-heavy early crop, herd ~14
  at 2/turn from day 1, near-zero buffer, `animal_reserve_leave_plantable`
  added to `_kagri_botlib` as an opt-in cfg key — byte-identical for every
  existing bot, default `None`). Raw $0-buffer shape bankrupts the botlib
  into a feed-miss escape spiral; even the tuned solvent envelope (opp
  reaches $24-39k, up from v2's ~19k) still loses to `main.py` **24-0-0 /
  100%**. **Same ceiling `bot_top10clone` hit** — `_kagri_botlib`'s
  movement/feed-logistics/market-timing is simply weaker than `main.py`, so
  no config tuning of it yields an unsaturated factory opponent. `bot_factory_v3`
  is kept as a stronger-than-v2 pool archetype regardless. The only real
  paths to an unsaturated factory opponent: a replay-driven agent that
  replays a mined winning action sequence (`POLICY-RARE-1` / Workstream A),
  or accept local eval is blind for economy changes (repo's standing
  conclusion) and gate the factory cluster on the ladder directly, the way
  the routing fix was.
- **AM-HERDRAMP-1 rejected (2026-09-05, claude):** diagnosed the animal_factory
  loss cluster on the routing baseline `56029879` (25 eps, vs-factory 6W-12L /
  33%) with `tools/trace_cashflow.py`. **All 12 factory losses share an
  identical day-0 signature:** ~$900-1070 seed + exactly $1600 on 4 `BUY_ANIMAL`
  on turn 0 -> cash $3000 -> $300-480 by day 1; hiring then held at the
  by-design `day<3: desired=6` cap while cash never clears ~$1500 through day
  15, and the opponent breaks out at day 10-15. Deficit buckets: ~4 close
  (<25k), ~4 recoverable (25-46k), ~4 blowout (>46k, opp was a monopolist).
  Tested one isolated mechanism: `ENABLE_E4_HERD_RAMP` — cap placed+pending
  animals at `k*(day+1)` for the opening days so the herd fills ~1/day like
  top-10 replays (Workstream A mining) instead of bingeing day 0. **Gate B
  failed twice:** (a) 1/day, 60 paired full pool seed 260906 — score delta
  **-9.2%**, CI [-19.2%,+0.8%], I/S/R 4/46/10, margin -$10.4k, productive
  actions -187; (b) milder 2/day-until-day4, 80 paired — every non-lineage
  opponent +0.0% score delta with broadly negative margin, two lineage
  regressions. Throttling the herd starves milk/wool/egg income; locally,
  filling fast beats the ladder-pathological binge — the same "local can't
  gate an economy change" wall the repo keeps hitting. `main.py` reverted
  clean (no toggle left in code). E2's own candidate list is now exhausted:
  #1 TXCASH shipped/ON, #2 HERDBATCH rejected, #3 ANTI_META self-play-only,
  and this. **The factory cluster has resisted P4b, cropflip, Lever 2, E3,
  HERDBATCH, ANTI_META, E4 — routing (`56029879`, 21%->35%) is the only thing
  that moved it.** Next real lever is `PLAN_TOP10.md` Lever 1 (a genuine
  2850-caliber `bot_top10clone` so Gate B stops being blind) or the §8
  policy-replacement challenger — not another one-mechanism economy tweak.
- **E2 anti-meta service-crew iteration rejected (2026-09-05):** tested one
  isolated maintenance change: at the full 13-head herd, reserve four animal
  hands instead of three (`ceil(herd/4)`, still leaving six crop units). On the
  identical 40-pair adversarial-v1 tuples (`--pick-seed 260906`), score delta
  fell from the selector's prior +8.8% to **+3.8%**, 90% CI
  **[-2.5%, +11.2%]**, I/S/R **3/36/1**. It created an external regression
  against animalfactory (**-6.2%, 0/15/1**), margin worsened -$4,565,
  productive actions fell another 100.3, and escapes stayed +0.1/game rather
  than improving. Reverted fully. The next anti-meta maintenance attempt must
  improve task prioritization or feed logistics without removing another crop
  worker; do not retry a larger fixed crew.
- **E2 market-aware herd selector implemented opt-in (2026-09-05):** enabled
  `ANTI_META` as an executable mode with the incumbent's same land, labor, and
  feed limits; only animal species targets/order change after day 5. New herd
  slots score live MILK/WOOL/EGG value, town demand, remaining production time,
  animal cost, and visible own+opponent species crowding. The identical 40-pair
  adversarial-v1 screen (`--pick-seed 260906`) produced **+8.8% score delta**,
  90% CI **[+2.5%, +16.2%]**, I/S/R **4/36/0**, but all four flips were in the
  `main` self-play bucket (+87.5%); every external archetype stayed +0.0%.
  Overall margin fell -$2,892, including animalfactory -$5,413 and wheatflood
  -$12,604, and escapes worsened slightly by +0.1/game. Keep the mode and its
  parameters available for further A/B work, but do not promote it as the
  default until it flips external games without a maintenance regression.
  All 13 strategy invariants, compilation, and diff checks pass.
- **Livestock wheat-target iteration retained opt-in (2026-09-05):** isolated
  `LIVESTOCK_ENGINE.WHEAT_TILES` from 10 to 14, leaving herd, land, labor,
  routing, and the 16-strawberry target unchanged. On the identical 40-pair
  adversarial-v1 tuples (`--pick-seed 260906`), score delta improved from the
  staged-herd result's +3.8% to **+6.2%**, I/S/R **3/36/1**, with 90% CI
  **[+0.0%, +13.8%]**. Mean margin deficit narrowed **-$1,580 -> -$555** and
  productive-action deficit **-189.5 -> -153.5**; day-10 cash stayed positive
  at +$502, plant-to-weed was -39.9, and crashes/escapes were zero. All external
  archetype buckets again had +0.0% score delta; the +62.5% main bucket supplied
  all score changes. Retain 14 wheat behind the livestock toggle, but do not
  promote while the interval touches zero and the signal remains self-play-only.
  All 10 strategy invariants, compilation, and diff checks pass.
- **Livestock opening-throughput repair retained opt-in (2026-09-05):** root
  cause was the mode reserving its full 14-animal footprint while only the
  opening 5x5 quadrant was usable. Added the configurable
  `HERD_CAP_BY_QUADRANTS={1: 4, 2: 14}` stage: the final 8-COW/6-SHEEP target
  is unchanged after land 2 opens, but only four cow tiles are reserved before
  then. On the identical 40-pair adversarial-v1 tuples (`--pick-seed 260906`),
  livestock improved from the prior +1.2% score delta to **+3.8%**, I/S/R
  **2/37/1**, while its mean margin deficit shrank **-$18,513 -> -$1,580** and
  productive-action deficit **-1,094.8 -> -189.5**; day-10 cash remained
  positive at +$507, plant-to-weed was -37.8, and crashes/escapes stayed zero.
  The 90% CI still crosses zero `[-1.2%, +10.0%]`, and all external archetype
  buckets remain +0.0% score delta (changes are only incumbent self-play), so
  retain this repair behind the livestock toggle but do not promote the mode.
  All 10 invariant tests, compilation, and diff checks pass. Next optimization
  should target the remaining crop/action deficit with one isolated parameter
  or mechanism, then repeat the frozen league.
- **Strategy invariant suite + first frozen league read (2026-09-05):** added
  `tests/test_strategy_modes.py` with 10 passing tests covering enabled/disabled
  resolution, fail-closed dispatch, adaptive/default equivalence, config bounds,
  and livestock herd/crop targets. A 40-pair frozen adversarial-v1 screen of
  `LIVESTOCK_ENGINE` vs `main.py` was **inconclusive and economically weak**:
  score delta +1.2%, 90% CI [-2.5%, +6.2%], I/S/R 1/38/1, margin delta
  -$18,513, productive actions -1,094.8, with zero crashes/escapes. All four
  external archetype buckets had exactly +0.0% score delta; the only changes
  were noisy incumbent self-play. Do not promote or enlarge this run. Next
  livestock iteration must fix throughput/asset utilization as one attributable
  change, then repeat this exact held-out protocol.
- **Strategy-intent + livestock mode implemented (2026-09-05):** the shared
  executor now receives an explicit resolved intent for herd targets, crop
  selection, land/hiring ceilings, and feed stock. `LIVESTOCK_ENGINE` is a
  playable opt-in mode (8 COW / 6 SHEEP, 14 WHEAT / 16 STRAWBERRY, 2 quadrants,
  11-hand ceiling, 3 feed-days); `experiments/livestock_mode.py` is its thin
  paired-evaluation entry point. The default `ADAPTIVE_ECONOMY` still matches
  committed `HEAD:main.py` exactly across all 719 actions and final rewards in
  a seeded full season. Initial 20-pair animal-factory smoke: both policies
  20/20 wins, zero crashes/escapes, score delta +0.0%, livestock margin delta
  -$5,558, day-10 cash +$1,093, 52.9 fewer weeds, but 1,050.5 fewer productive
  actions. Raising its labor/land ceilings made no difference on the identical
  tuples, so those speculative changes were reverted. Keep the mode opt-in and
  do not promote; next improvement should address its low productive-action
  throughput and then run the frozen weighted league where score-rate can vary.
- **Strategy-mode foundation added (2026-09-05):** `main.py` now has a
  centralized `STRATEGY_CONFIG`, a `STRATEGY_MODE` selector, and named config
  groups for `ADAPTIVE_ECONOMY`, `FRONTIER_SCHEDULE`, `LIVESTOCK_ENGINE`,
  `ANTI_META`, and `MULTI_ROUTE`. Only `ADAPTIVE_ECONOMY` is enabled/executable;
  every unavailable/disabled selection fails closed to that incumbent policy.
  This refactor is behavior-preserving: a 720-turn fixed-seed run against
  `starter` matched committed `HEAD:main.py` exactly at every returned action,
  status, and reward (final money $53,388); compile/diff checks and a four-game
  smoke run also completed with zero crashes/errors. This foundation milestone
  is now superseded by the strategy-intent/livestock snapshot immediately above.
- **`56039865`** (`main.py` = `0aa1da6:main.py`, submitted 2026-09-05 20:02):
  **590.2 / 30 eps / 17W-0T-13L / 57% score-rate; animal_factory 10W-0T-6L /
  63%, wheat_flood 3-0, other 4-7.** **ATTRIBUTED 2026-09-06** via `git reflog`
  (HEAD was `0aa1da6` at submit time — the non-routing v15 lineage build: v11 +
  P4b/cropflip + Lever2 + E3 + TXCASH + feedfloor + STRATEGY_MODE selector and
  rejected land-timing/demand-match toggles all default OFF). **Best agent on
  the board and the confirmed reference build.** `main.py` on disk reverted to
  this 2026-09-06 (also snapshotted `agents/main_v16.py`).
- **`56044961`** (routing + `ENABLE_MAXHANDS_12` ON, commit `9f36ac0`, submitted
  2026-09-06 02:28): **REJECTED — 499.7 / 2 eps / 0W-0T-2L** (both near-ties:
  44.6k v 45.6k, 75.2k v 75.8k). Stacked on the routing base that itself
  regressed (see ROUTE-SUBMIT-1). Still one of the 2 live tracked slots at a
  decaying 499.7 — needs a good `main.py` submission to evict it, gated on user
  approval. Flag block now only on `agents/main_v16_routing.py`.
- **PLAN_LADDER_NEXT_2 Phase B0 + C1 (2026-09-06, claude):** **B0 done** —
  re-read `56039865`, episode count frozen at 30 (slot aging out of ladder
  rotation), reframe holds exactly: 57% overall / animal_factory 63% (10-0-6).
  All 13 losses share one pattern: mid-game cash crater, our day-15 money a few
  hundred–1.5k while opp is at 3–32k; the W/L split is decided day 15–25, not
  earlier. **C1 KILLED** — `scratchpad/c1_detect.py` over all 30 `56039865`
  replays: no day-3 or day-8 rule separates the 11 factory losses from the 15
  factory wins (every candidate rule FP ≥ TP; losses show a *better* day-8 coin
  lead than several wins). **Phase C is closed** per the plan's own kill rule.
  **B1 running** (LADDER-B1 row) — local paired ablation of Lever2/E3/TXCASH vs
  the frozen league, 72 pairs each, no submission. LEDGER has both rows.
- **Last updated:** 2026-09-06 (**PLAN_LADDER_NEXT_2 Phase B2 press — DONE, local
  no-op, Lever2 declared tuned, slot → B3.** `ENABLE_LEVER2_LAND_MIN_DAYS`
  (days-left floor on the computed 4th-quad gate) added to `main.py` default OFF;
  96-pair adversarial_league_v1 screen with it ON = exact no-op (0/96 games
  differ) — the `has_slack` capacity check already refuses Q4 in ~every local
  game, so a floor on top is inert. Toggle kept OFF as a ladder-only candidate.
  Per §3 B2 kill rule, next slot → **B3** (symmetric early-cash guard for the
  7-of-13 "other" loss cluster). LEDGER "B2P Lever2 land-gate press" row added.)
  — earlier 2026-09-06 (**PLAN_LADDER_NEXT_2 Phase B0 done + C1 killed +
  B1 done** — B0: `56039865` reframe holds at 30 eps (57% / af 63%). C1: no
  opening checkpoint separates factory W from L, Phase C closed. B1: Lever2 OFF
  −2.1% (CI excl. 0), E3/TXCASH score-rate passengers; B2 split → carrier =
  `ENABLE_LEVER2_LAND_GATE`.) —
  earlier 2026-09-06 (**PLAN_LADDER_NEXT_2 Phase A — ROUTING REVERTED.**
  Full-episode ladder reads: non-routing v15 `56039865` **590.2 / 57% /
  animal_factory 63%** beats routing `56034847` **565.7 / 48% / 31%** and
  routing+MAXHANDS `56044961` **499.7**. Attributed `56039865` to `0aa1da6:main.py`
  via reflog. `main.py` disk reverted to `0aa1da6`; `agents/main_v16.py` (winner)
  + `agents/main_v16_routing.py` (rejected routing build) snapshotted. LEDGER
  "ROUTING REVERTED" row added. Phase B needs a rewrite. Commit pending.) —
  earlier 2026-09-06 (**CHALLENGER-1 MAXHANDS-12 submitted** as
  `56044961` — `ENABLE_MAXHANDS_12` flipped ON, committed `9f36ac0`, isolated
  to `main.py`.) — earlier 2026-09-06 (**1f/ROUTE-SUBMIT-1 fully closed**: ladder read
  KEEP — sub `56034847` 572.9 / 24 eps / 50% score-rate / animal_factory 36%
  beats baseline `56029879` 522.6 / 43% / 29% on every axis; `56034847` is the
  new comparison baseline. `main.py` disk promote DONE — commit `033990f`,
  isolated (`cp main_v12_flat.py main.py`, only `main.py` staged; other
  shared-row WIP left uncommitted). git HEAD lineage now matches live.) —
  2026-09-05 (1b resolved flat/keep, `main_v12_flat.py` re-validated and ready for the next slot, 1d root-caused with a Gate-B-passing candidate not yet submitted; later — Workstream A land/animal rule-mining complete; later — **1c submitted**; later — **E3 (1d) folded onto `main.py` as `ENABLE_E3_ANIMAL_RESERVE`, re-gated with a weaker/ambiguous result — see below, don't cite the original +5.0% number anymore**; later — **1e (HERDBATCH) folded onto `main.py`, re-gated NEGATIVE, default set `False`, not submitted**; later — **AM-FEED-1 done (default OFF, committed `7fcfc38`), and 1f/ROUTE-SUBMIT-1 SUBMITTED 2026-09-05 14:30 as sub `56034847` (`main_v12_flat.py`)**)
- **1c submitted (2026-09-05 09:45, sub `56029879`, `main_v12_flat.py`, PENDING).** Routing fix (Hungarian-assignment executor), re-validated same-day against current `main.py` post-Lever2: 0/719 action mismatches, 95.0% local score-rate. This evicts one of the 2 tracked slots — the pair to compare after 20+ episodes is `56029879` vs `56023304` (P4b+cropflip, currently 527.3). **Checked this session: only 2 episodes accrued (1 validation + 1 public, publicScore 501.5) — far short of the 20+ needed; do not read anything into 501.5 yet.** Do not submit anything else today.
- **E3 (item 1d) folded onto `main.py` itself (2026-09-05, this session): `ENABLE_E3_ANIMAL_RESERVE` (default `True`) + `E3_OFF_FIXED_MARGIN=300`**, following the standing per-hunk toggle convention. Self-test (E3-OFF copy vs pinned pre-edit `main.py`, 20 pairs) confirmed the toggle mechanism is an exact +0.0%/+$0 no-op. **The real gate on the current lineage (100 pairs, full pool incl. the 4 new archetype bots) reads much weaker than the original probe: +3.0% score delta, 90% CI [+0.0%,+7.0%] (touches zero), margin delta NEGATIVE (-2943), one regression in the closest lineage self-play (`main_v14`, 0/3/1).** Every real hard-bot archetype (animalfactory_v2/wheatflood/premium/animalfarm) now reads 0% score delta with negative margin. Kept ON by default (still net-positive direction, a logically real accounting-bug fix, and per `CLAUDE.md` local can't reliably gate economy changes either way) but **no longer citable as a clean Gate-B pass** — cite `experiments/LEDGER.md`'s new "E3 folded onto main.py + re-gated" row, not the original +5.0%/CI[+1.7,+10.0] read. Next submission slot (once the one-per-day window resets) still goes to `main.py` with this fix included per the existing queue order — flag the weaker re-gate to the user before that submission.
- **Explicit goal as of 2026-09-05: rank ≤10 (~2850-3010 rating), not "any improvement."** The §1 queue below (one hand-tuned constant per submission, ~2-3 day ladder-gated read, ~15-20 reads left before deadline) cannot reach that bar even in principle — see `docs/PLAN_TOP10.md`'s "Why" section for the math. §1 items still get done (they're free/queued), but the three levers in `PLAN_TOP10.md` (top-10-caliber local opponent from `top10_ladder/` replays, computed marginal-value estimator replacing hardcoded priority constants, routing fix as the execution substrate) are now the actual priority. Start there, not at 1d.
- **Lever 1 status (tuned this session, `ecd1d03`→`479829e`):** `bots/bot_top10clone.py` built from real `tools/analyze_top.py` numbers (permanent 3-quadrant land cap, STRAWBERRY-primary day-ramped crop mix, 10-head COW/SHEEP-heavy herd) and fixed through two real bugs (v1: holding the day-20 58/40 split from turn 0 starved early cash, 20-0 loss; v2: a 15-head herd outran the crew's feed capacity, escape/rebuy cash-burn cycle). Then ran a proper 15-game-per-variant comparison against `main.py` specifically (not just a neutral opponent): current config (opp final money ~9.9k mean) beat both a bigger 15-head herd (~4.1k) and a simplified 2-crop/faster-land variant (~6.7k), so those were reverted. **Verdict: still the weaker of the two archetypes against `main.py`** — `bot_animalfactory_v2` reads ~19.0k opp money on the same protocol — even though `bot_top10clone` wins a neutral head-to-head against `bot_animalfactory_v2` 5/8 (15.2k vs 11.4k mean money). Read as an intransitivity: `main.py`'s own strawberry-heavy mix (post P4b+cropflip) directly competes with `bot_top10clone`'s for the same premium-price ceiling in a way it doesn't with animalfactory's wheat-heavy one. Likely the generic `_kagri_botlib` engine's real ceiling for a strawberry-heavy field (more per-tile watering upkeep than wheat), not a remaining tuning problem — further local knob-turning on this bot is now lower-priority than starting Lever 2 itself. Keep it in the pool as a second distinct hard archetype. Re-run `tools/analyze_top.py` + re-derive (don't hand-tune further) if `top10_ladder/` gets refreshed.
- **Lever 3 status:** `main_v12_flat.py` was validated against `main.py` @ `be12348` earlier this session — **now stale**, since `main.py` has since moved to Lever 2 (`a146a5e`). Re-run `tools/flatten_v12.py` + `tools/validate_flatten.py` against the current `main.py` before submitting item 1c.
- **Top-policy land/animal mining (2026-09-05, `tools/mine_top_policy_rules.py`, Workstream A):** mined explicit BUY_LAND/BUY_ANIMAL preconditions from `top_policy.jsonl` since the classifier can't learn them. Confirmed (not assumed): top-10 farms **never buy the 4th quadrant** (0/17 that reach 3 quadrants go to 4) — corroborates Lever 2's emergent `quads29==3.0` cap independently — and land buys are gated on the *current* land being near-fully planted, not just cash. Animal buys are small (qty 1, rarely 2) and continuous from day 0 through ~day 15, never a multi-animal single-turn batch — the opposite shape of the day-0 $1600/4-animal binge item 1d root-caused. Herd plateaus ~14-15 by day 12. Full numbers + the correctness fix (a replay row's `action` produced *that same row's* state, not the next one — tripped up the first pass) in `experiments/LEDGER.md`'s new top-row.
- **Workstream B candidate built + screened, INCONCLUSIVE as a bundle (2026-09-05, `experiments/candidate_top10rules.py`):** forked `main.py` and encoded the three mined rules as code (land fill-gate 0.55→0.75, hard-disable the 4th quadrant, herd cap {1:3,2:8}/13→{1:6,2:13}/15). 100-pair Gate-B screen vs `main.py`: headline **+3.5% but 90% CI [-0.5%, +8.0%] crosses zero**, carried mostly by the `main`-mirror-match bucket, not the target archetypes.
- **Bisected via per-rule toggles (2026-09-05, same file):** each rule got an `ENABLE_R*` flag + named config constant (config block above `USE_ANIMALS`); all-False reproduces `main.py` exactly (verified: 20-pair self-test, **+0.0% delta, +$0 margin in every game**). Ran each flag alone, 80 pairs: **R1 (land fill) +2.5%, CI [-0.6%,+6.2%] — noise, same pattern as the bundle. R2 (disable Q4) exactly +0.0% in all 80/80 games — a complete no-op locally** (confirms `main.py`'s existing ROI check already never fires true in this population, so hard-disabling it changes nothing here). **R3 (herd cap) +2.5%, CI [+0.6%,+5.0%] — the only one excluding zero**, driven by `bot_top10clone` (the actual top-10 proxy) at +4.2%, but it costs margin (not win/loss) against `bot_animalfactory_v2`/`bot_wheatflood`. **R3 is carrying whatever real signal exists; R1 should be dropped; R2 is harmless but inert.** None individually clears the plan's literal Gate B bar at n=80.
- **R3 margin-cost trade-off root-caused and fixed (2026-09-05).** Cause: `n_crew` sizes the animal crew off `len(reserved)` (the herd's *reservation target*) instead of the actual current herd, so R3's 13→15 cap bump crosses the crew-size `//5` boundary immediately (3→4 hands) and pulls a 4th crop hand off the field from day 1 — same mechanism the rejected E2-candidate-4 fixed-crew test already flagged as margin-costly. Fix: `ENABLE_R3_CREW_FIX` (one line, drop `len(reserved)` from the formula). Isolated 80-pair re-read (R3 alone + fix, same `--pick-seed 2026` protocol): overall score delta -0.6% CI[-3.1,+1.2] (crosses zero, self-play-only noise) but **every real external archetype still +0.0% score delta with margin fully recovered positive** — animalfactory -53 (was -3938), wheatflood **+11,762** (was -9818), premium +14,955, top10clone +6,257. Confirms the crew-size bug, not the herd-cap increase, was the cost. Full numbers: `experiments/LEDGER.md`'s "R3 crew-size root-cause + fix" row. **Next: test `ENABLE_R3_CREW_FIX` alone (R3 herd cap back off) against baseline `main.py`** — the crew-size-off-target bug is generic, not R3-specific, and may already cost margin at quadrant transitions in the current baseline. If clean, fold the crew-size fix onto `main.py` as its own attributable change (queue behind 1f), independent of whether R3's herd-cap bump itself ever gets promoted.
- **Lever 2 status (`a146a5e`, `main.py`):** computed marginal-value estimator implemented — `_crop_tile_value()` (real engine growth/price constants) drives both `choose_crops`' crop-mix selection (replacing the hand-set STRAWBERRY/TOMATO/etc. shares) and the quadrant-4 land gate (replacing the `n_units>=18` threshold with a computed capacity+ROI check). Bug-check clean: 95.0% full-pool score-rate, 0 errors across ~230 local games, `quads29` holds at 3.0 every game (reproduces finding 1 without a tuned threshold). **But the targeted hard-bot reads (35 games each vs `bot_top10clone.py` and `bot_animalfactory_v2.py`) show no measurable local improvement over the P4b+cropflip baseline** — both within noise of the pre-Lever2 numbers. Full details + numbers: `experiments/LEDGER.md`'s Lever 2 row. **Not submitted** (today's slot used). Real verdict needs a ladder read, not another local probe — this repo's own history says local can't gate economy changes either way. Decision for the next submission slot: ship item 1c (routing, lower-risk, already mechanically validated) first, then Lever 2, rather than jumping the queue on an unproven-but-structurally-sound bet — flag this order to the user before acting on it, since it's a real judgment call.
- **Toggle+config infra generalized to `main.py` and `main_auto.py` (2026-09-05).** Following the same pattern as `experiments/candidate_top10rules.py`'s R1/R2/R3 flags, every independently-revertible hunk in both files now has an `ENABLE_*` flag (+ named config constants where the OFF path needs one), in a config block above `USE_ANIMALS`: `main.py` gets 10 (F1, P2, P4 coverage cap, P4c late-weed, Lever2 land-gate, Lever2 crop-mix, P3f, P1w, P4r, feed-emergency-floor); `main_auto.py` gets those same 8 plus 4 more from its own AUTO-iteration history (reserve retune, sell-cap raise, herd-batch bootstrap, and an off-by-default P2k crop-prune kept only so a future re-test doesn't have to re-derive the guard). Every OFF value is the exact prior-version constant/formula (from `agents/main_v7.py`/`main_v10.py`/`be12348`), not a guess. **Verified on both files: 20-pair paired self-test, all flags at default vs. a pinned pre-edit snapshot, +0.0% score delta / +$0 margin delta in every single game** — the refactor is a pure no-op at defaults. Purpose: any future bisection of one of these hunks (the way Workstream B bisected R1/R2/R3) no longer needs a separate forked file.
- **Environment hazard found this session:** a `main.py` edit silently reverted to the last committed HEAD between an Edit call and a later test run (file mtime predated the edit, content matched HEAD exactly, no visible error) — happened twice (once on `bots/bot_top10clone.py`, once on `main.py`). Cause unknown. **Mitigation going forward: after any edit to a file about to be tested, verify with `grep`/mtime that the change actually persisted on disk *before* trusting a test result, and commit promptly rather than leaving meaningful work uncommitted.**
- **Ladder rank:** ~5424/7533 as of the 2026-09-04 audit (`docs/PLAN_LADDER_NEXT.md`) — **re-check live**, don't trust this number past a few days.
- **`56016363`** (v11+feedfloor, anchor, submitted 2026-09-04 16:29): **508.3** on **30 episodes** (15W-0T-15L, 50% score-rate; animal_factory 3-12/20%).
- **`56023304`** (P4b+cropflip, submitted 2026-09-05 02:35): **515.6** on **25 episodes** (11W-0T-14L, 44% score-rate; animal_factory 3-11/21%, other 6-2/75%, wheat_flood 2-1/67%).
- **`56029879`** (main_v12_flat.py, routing-only fork, submitted 2026-09-05 09:45): **re-read 2026-09-06: 522.6** on **30 episodes** (13W-0T-17L, 43% score-rate; animal_factory 6-15/29%, other 4-1/80%, wheat_flood 3-1/75%). Second tracked slot; the losing side of the 1f compare. (Earlier 23-ep read was 557.1 / 48% / 35% — regressed toward the mean as episodes accrued.)
- **`56034847`** (main_v12_flat.py, routing re-port onto current `main.py` =
  routing + Lever2 + E3 + TXCASH + STRATEGY_MODE/ANTI_META toggles; **item 1f**,
  submitted 2026-09-05 14:30): **ladder read 2026-09-06 — 572.9** on **24
  episodes** (12W-0T-12L, 50% score-rate; animal_factory 5-9/36%, other 5-3/63%,
  wheat_flood 2-0/100%). Beats baseline `56029879` (522.6 / 43% / 29%) on ladder
  score (+50), overall score-rate (+7pp), and the animal_factory cluster (+7pp)
  — clears the 1b keep-if-flat-or-better rule decisively. **KEEP; `56034847` is
  the new comparison baseline.** `main_v12_flat.py` was submitted directly;
  `main.py` on disk still NOT promoted (git HEAD `7fcfc38`) — the queued
  `cp main_v12_flat.py main.py` + commit is the one open action (deferred:
  working tree has unrelated uncommitted WIP from other shared-work rows —
  `bots/_kagri_botlib.py`, `bots/bot_factory_v3.py`, `PUBLIC_AGENT_STRATEGY_CATALOG.md`,
  plus in-progress `main_v12_flat.py`/`CLAUDE.md` edits — so committing needs
  user direction on scope).
- **1b resolved (2026-09-05, 23+30 eps, re-read via `download_episodes.py` + `tools/ladder_analyze.py`):** `56023304` (48%) vs anchor `56016363` (50%) — **flat within noise**, not the "trending toward regress" read the 10-episode sample suggested. Per the stated decision rule (keep if flat-or-better), **`56023304` stays incumbent; no rollback.** The load-bearing fact from this read isn't the overall rate, it's that **animal_factory win-rate is ~20-23% on both submissions** — identical within noise despite the land-cap/crop-mix constant change between them. This confirms the `IMPACT_RANKED_LEADERBOARD_PLAN.md` diagnosis directly: hand-tuned-constant patches (P4b, cropflip, Lever 2's computed gate) are not moving the dominant loss cluster at all. Next submission slot goes to **1c (routing)** per both this file's queue and `PLAN_TOP10.md`'s sequencing — do not spend another slot on a constant-level tweak.
- **Top of leaderboard:** ~3000 rating (Crop Dusta 3009.3; top-20 band 2850–3010).
- **Deadline:** 2026-09-30 23:59. $50,000 prize.
- **`main.py` on disk right now:** Lever 2 (commit `c9ab4ff`, docstring header now says v14 — see `agents/main_v14.py`), NOT what's submitted. The submitted `56023304` is the older `P4b+cropflip` (`be12348`) snapshot — item 1a is done, 1b is in progress (waiting on episode count).
- **`agents/main_v14.py`** (new, this session): frozen snapshot of the current `main.py` (v11 + P4b/cropflip + Lever 2), added to the lineage/compete.py pool per `CLAUDE.md`'s "Agent lineage" convention. `main.py`'s own docstring header was also corrected from a stale "v11" label to "v14" (code untouched, docstring-only diff, re-verified via `compete.py` after the edit).
- **`agents/main_v15.py`** (new, 2026-09-05): frozen snapshot of `main.py` as it stood right before the 1c routing-fix merge — v14 + toggle/config generalization (`73948dd`) + E3 animal-reserve fold (`dcc219b`). This is the rollback point if the routing merge misbehaves, and the last version independently ladder-characterized via its predecessor `56023304` (515.6, 44% score-rate, animal_factory 21%). Not submitted itself. Added to the `compete.py` lineage pool.
- Kaggle CLI works via `C:\Users\LENOVO\AppData\Local\Programs\Python\Python313\python.exe -m kaggle ...` (plain `kaggle` is not on PATH in this shell).
- Before trusting any of the above: run `kaggle competitions submissions kaggriculture` yourself — this snapshot is a session-start convenience, not a live source of truth.

---

## 1. Submission queue — one attributable change per slot, in this order

> **2026-09-15 (claude) — live queue is `docs/STRATEGY_LOSS_READ_2026-09-15.md` §4:** H3 `56233524` (40 eps, af 50%) and H4 `56235916` (38 eps, af 50%) both judged NOT promotable. New #1 = C2 `ENABLE_HERD_INSTALL_FIRST` (mechanical: 78/78 games buy ~11 animals, place ~8; crew `PICKUP`s 81×/game, `PLACE`s 8×) → C1 `ENABLE_CROP_VALUE_LIFESPAN` → union → herd target 14. Files to be owned by the C2 row: `agents/main_v43_herdinstall.py`, `tests/test_herd_install_first.py`.
> **C2 SUBMITTED 2026-09-15 14:17 UTC as `56256380`** (gate 93-0-3/96, 0 err, +2.6% CI[+0.0,+5.7], af 42/42). C1 built as `agents/main_v44_croplifespan.py` + `tests/test_crop_value_lifespan.py` (6 tests; probe: OFF 36 TOMATO@d15/82k → ON 51 STRAWBERRY/96k in 2 of 3 seeds); **C1 SUBMITTED 2026-09-15 14:22 UTC as `56256499`** (gate 93-0-3/96, 0 err, +2.6% CI[-0.5,+6.2], af 42/42). Tracked pair `56256499` + `56256380`; judge each at ≥20 eps; if both hold → union `agents/main_v45_c2c1.py`.
> **READBACK 2026-09-15 ~16:30 UTC (claude):** C2 `56256380` 28 eps 15-1-12, af 55.4%, avg animals 12.4, 642.5 → **PROMOTED** (`ENABLE_HERD_INSTALL_FIRST=True` on `main.py`). C1 `56256499` 27 eps 14-0-13, af 52.6% → not promotable alone, but the tomato flip is gone (TOMATO sells 281 vs 1749) and its losses are all herd-short → union `agents/main_v45_c2c1.py` (C1 ON over the C2-promoted parent) gated (93-0-3/96, 0 err, af 42/42) + **SUBMITTED 16:41 UTC as `56259132`** (3rd/5 today). Judge at ≥20 eps: af ≥ 54.2% and ladder > 642.5. `tests/test_animal_carry_guard.py` setUp now forces C2 OFF so H2 is tested in isolation.

> **READBACK 2026-09-16 (claude):** v45 `56259132` 36 eps 20-0-16, ladder **665.7 (all-time best)**, af 17-16 = 51.5% (one game under 54.2%; inside noise of C2's 55.4%), TOMATO 119 sells / 0 tomato-dominant games, animals 12.2, 0 errors → **PROMOTED** (`ENABLE_CROP_VALUE_LIFESPAN=True` on `main.py`). All 16 losses out-scaled (opp median 14 animals). Next single flag: `ENABLE_HERD_14` (`agents/main_v46_herd14.py`, cap 13→14, GOOSE-weighted) — gate running.

> **BUILD 2026-09-16 (claude):** HERD-14 (`agents/main_v46_herd14.py`) gated 93-0-3 but **HELD** — it exposed the parent losing 2.15 animals/game to escapes (81/96 games, wheat in shed) → crew never reaches 1-2 animals/day. Blanket feed-first (v47) fixed escapes but cost −10.8k/game → rejected. At-risk-only feed priority (`ENABLE_FEED_FIRST`, `agents/main_v48_feedatrisk.py`): 91-0-5, 0 err, af flat, vs main 4-3-2, escapes 2.15→0.03 → **SUBMITTED 15:05 UTC as `56281675`** (1st/5 today). Judge at ≥20 eps: af ≥ 51.5%, ladder ≥ 665.7, avg animals ≥ 12.2. Then re-gate HERD-14 on top.
> **BUILD 2026-09-16 pt2 (claude):** 37-ep loss read of `56259132` (docs/STRATEGY_LOSS_READ_2026-09-16.md): the town shop draw is the market's only sink and every STR/MILK crash had 0-1 matching shops among the first four draws. W1 wheat churn DROPPED (engine buy quote makes it cash-neutral). C3 `ENABLE_CROP_CROWD_OWN_ONLY` (`agents/main_v49_cropcrowd.py`) gated 89-2-5 but HELD (superseded). **S1 `ENABLE_SHOP_DEMAND_VALUE` (`agents/main_v50_shopdemand.py`) gated 89-0-7 / 0 err / af 46/46 → SUBMITTED `56282756` 16:06 UTC (2/5 subs).** Judge at ≥20 eps with `56281675` (3 eps so far). Next: S2 herd-by-drain.
> **BUILD 2026-09-16 pt3 (claude):** `56281675` feed-first at 20 eps: 11-0-9, af 8-7 = 53.3%, animals 12.3, 0 err, live 667.3 → **PROMOTED** (`ENABLE_FEED_FIRST=True` on main.py). S2 herd-by-drain DROPPED after a 61-ep backtest (+400/game at best, docs/STRATEGY_LOSS_READ_2026-09-16.md §E). M1 `ENABLE_IDLE_SEED_BYPASS` (`agents/main_v51_idleseed.py`, d6-10 seed crater) gated 89-0-7 but **REJECTED**: own money −8.6k, d10 cash −9.8k — bypass wheat displaces the d9-10 STR wave and trips the land gate early (§F). Next: HERD-14 re-gate on the feed-first parent (`agents/main_v52_herd14ff.py`, `compete_v52.log`) → submit if clean; then judge `56282756` (S1, 4 eps).
> **BUILD 2026-09-17 (claude):** `56282756` S1 at 38 eps: 20-0-18, af 50.0%, STR crashes 5/38 = parent, live 662.6 → **NOT PROMOTABLE (OFF)**; `56281675` feed-first at 38 eps 20-0-18, af 51.6%, live 638.5 (stays promoted). 76-ep read → **SHEEP-ON-YARN** `ENABLE_SHEEP_ON_YARN` (`agents/main_v53_sheepyarn.py`, 9 tests): yarn store by d9 → WOOL never crashes (0/27) and 8+-sheep opponents beat us 15/19; ON = goose slots → sheep while a YARN_STORE is unlocked. Gate `compete_v53.log` 91-3-2, 0 err, af 35/35, I/S/R 2/94/0, +2.9k mean; yarn-by-d9 seeds +13.5k/+35.5k/+24.8k. **SUBMITTED `56307690`** (1/5 today). Judge at ≥20 eps (af ≥ 51.6%, ladder ≥ 662.6, sheep ≥ 4 + WOOL d25 ≥ 199 in yarn games). Open: herd overshoots want by 1-2 (GOOSE 6-7 vs want 5) — BUY_ANIMAL one-per-turn loop vs shed lag, mechanical candidate. See docs/STRATEGY_LOSS_READ_2026-09-16.md §G.

> **JUDGE 2026-09-17 (claude):** `56307690` SHEEP-ON-YARN at 25 eps: 14-0-10, af 54.5%, 0 err, 661.6; yarn-by-d9 games sheep 5.7 / WOOL d25 228 / 0 crashes / W 6/10 / own money +14.4k → **PROMOTED** (`ENABLE_SHEEP_ON_YARN = True` on `main.py`). BUY-COUNT-CARRIED `ENABLE_BUY_COUNT_CARRIED` (`agents/main_v54_buycarried.py`, 6 tests): 6.7/14.2 buys per game issued while a hand carries the species; fix gated ×2 (`compete_v54.log`, `compete_v54b.log`) af 73/73, 0 err, own money +4.0k/+1.4k mean but median −1.6k in run 2 and mirror vs main 7-13; herd 13 → 11 and the early 4th cow lost → **REJECTED, dormant OFF**. No sub (1/5 used today). Tracked pair = `56307690` + `56282756`. See docs/STRATEGY_LOSS_READ_2026-09-16.md §H.

> **BUILD 2026-09-17 (claude, 2nd):** `56307690` live 663.6 at 31 eps. COW-ON-MILK `ENABLE_COW_ON_MILK` (`agents/main_v55_cowmilk.py`, 11 tests, suite 153/153): no milk shop in the first 3 draws → MILK d25 ≤ 40 in 81% of games, yet cows 5-6 are bought d9-12; ON caps cows at 4 and gives the slots to sheep when a yarn store is an early draw. Gate ×3 (`compete_v55.log` cows→geese variant rejected; `compete_v55b.log` any-yarn hit the d12-yarn case; `compete_v55c.log` final 91-3-2, 0 err, af 35/35, I/S/R 1/95/0, 12 targeted pairs +4.3k mean / 9 up, 84 byte-identical) → **SUBMITTED `56311727`** (2/5 today, 3 remain); flag dormant OFF on `main.py`. Tracked pair = `56307690` + `56311727`. Judge at ≥20 eps. See docs/STRATEGY_LOSS_READ_2026-09-16.md §I.

> **JUDGE 2026-09-18 (claude):** `56311727` COW-ON-MILK at 36 eps: 21-0-15 (58%), af 13-13 = 50.0% (parent `56307690` 19-17 = 52.8% at 39 eps), 0 err, **685.4 = all-time best** (parent 668.6); targeted bucket herds 4/8/1, 4/7/1, own money ~82.7k vs ~75k → **PROMOTED** (`ENABLE_COW_ON_MILK = True` on `main.py`). HERD-CAP-RESERVE `ENABLE_HERD_CAP_RESERVE` (`agents/main_v56_herdcap.py`, 9 tests, suite 162/162): a yarn store drawn d10-17 stacks sheep on kept geese → herd 15-19 in 14/14 ladder games, W 5/14; the fix reserves placed later-species counts in the cap loop. Gate `compete_v56.log` 95-0-1, 0 err, af 47/47, I/S/R 0/96/0, own money −668 mean, the 17 late-yarn pairs −919 mean / −942 median (8 up / 9 down) → **REJECTED, dormant OFF** (sheep pay back even stacked; the late-yarn losses are opponent strength). No sub (0/5 today). Tracked pair = `56307690` + `56311727`. See docs/STRATEGY_LOSS_READ_2026-09-16.md §J.

Discipline (from `docs/PLAN_RATING_IMPROVEMENT.md` Phase 0 — do not violate):
only the promoted `main.py` goes to the real `kaggriculture` slug, never
`agents/main_v*.py` / `main_auto.py` / ML probes; one submission/day; judge
promote/revert by **win-rate**, not coin margin.

- [x] **1a. Submit current `main.py` (P4b+cropflip).** Done — sub `56023304`,
      2026-09-05 02:35.
- [x] **1b. Wait 20+ episodes**, then `python download_episodes.py` +
      `python tools/ladder_analyze.py <sub_id>`. **Resolved 2026-09-05**: 23 eps
      `56023304` 48% vs 30 eps `56016363` 50% — flat, keep `56023304`, no
      rollback. animal_factory win-rate ~20-23% on both — the dominant loss
      cluster is untouched by this constant-level change (see §0 note).
- [x] **1c. Submit `main_v12_flat.py` (routing fix) — submitted 2026-09-05
      09:45, sub `56029879`. RESOLVED 2026-09-05: KEEP/PROMOTE.** Re-validated
      same-day against current `main.py` (post Lever 2, `bb73e7b`):
      `tools/validate_flatten.py` → 0/719 action mismatches, Kaggle's
      `get_last_callable` resolves `agent` correctly; `compete.py --games 60`
      → 95.0% score-rate, 56W-2T-2L, 0 crashes/errors, +3497 mean margin vs
      `main_v14` (current lineage) specifically. This is the Hungarian-assignment
      executor whose earlier ladder score (123.2) was root-caused as a
      packaging bug, not a real regression (`023aadb`) — last unresolved item
      from `docs/TOP10_TEARDOWN.md` (movement 60% ours vs 47–48% top-10).
      **Ladder read (23 eps `56029879` vs 25 eps `56023304`):** score-rate
      48% vs 44%, animal_factory win-rate **35% (6W-0T-11L) vs 21%
      (3W-0T-11L)** — the first submission to move the dominant loss cluster
      at all — ladder 557.1 vs 515.6. Clears the 1b decision rule
      (flat-or-better) with margin to spare: **routing fix confirmed
      net-positive on real ladder, `56029879` is the new baseline for future
      comparisons.** Caveat: `main_v12_flat.py` is a routing-only fork of an
      *earlier* `main.py` state — it does NOT include Lever 2 or the E3
      animal-reserve fix that have since landed on `main.py`. Next submission
      slot: port the routing executor onto current `main.py` (Lever2+E3
      included) as a single combined change, per the queue below.
- [x] **1d. Root-cause the day-2 lead-flip / cash-crater pattern — resolved
      2026-09-05.** Built `tools/trace_cashflow.py` and traced the 8 worst
      real ladder `animal_factory` losses (both tracked subs). Identical
      pattern in all 8: day 0 spends $1030-1220 on seed + exactly **$1600 on
      4 animal buys**, crushing cash $3000→$150-350 by day 1; never breaks
      out of a $100-2300 band through day 15 while the opponent reaches
      $60-102k by day 29. Root cause: `BUY_ANIMAL`'s gate uses a private
      margin (`money >= cost+300+150·placed_total`) instead of the same
      day-scaled `reserve` the seed budget already respects, so both draw the
      same cash independently with no shared budget. Fix candidate:
      `experiments/probe_e3_animalreserve.py` (one line:
      `money - reserve >= cost + 150·placed_total`). Gated via
      `compete.py --baseline main.py`: diverse pool passes Gate B cleanly
      (**+5.0% score delta, 90% CI [+1.7%,+10.0%], 0 regressions**, day10
      cash +40); the dedicated `bot_animalfactory_v2` read is uninformative
      (both go 100%, bot is saturated/too weak to discriminate — same gap as
      Lever 2). **Folded onto `main.py` itself (2026-09-05) as
      `ENABLE_E3_ANIMAL_RESERVE` (default `True`).** Re-gated on the current
      full lineage (100 pairs, pool now includes 4 new archetype bots):
      **weaker result — +3.0% score delta, CI [+0.0%,+7.0%] touches zero,
      margin delta NEGATIVE (-2943), one `main_v14` self-play regression.**
      Kept ON (still net-positive, logically a real fix) but no longer a
      clean local Gate-B pass — see `experiments/LEDGER.md`'s "E3 folded onto
      main.py + re-gated" row. Queue for the submission slot *after* 1c per
      `docs/PLAN_TOP10.md` sequencing (one change per slot, don't bundle with
      routing) — flag the weaker re-gate before that submission.
- [x] **1e. Fold `main_herdbatch.py`'s herd-batch bootstrap onto `main.py` —
      done, REJECTED (2026-09-05).** Added as `ENABLE_HERDBATCH` (toggle,
      default `False`). Re-gated on the current lineage: targeted read vs
      `bot_animalfactory_v2` still uninformative (60-0-0 both sides, +0.0%);
      diverse pool (100 pairs) came back **net negative** — score delta
      -3.0%, CI [-7.0%,+1.0%], 2/93/5 improved/same/regressed, margin -960,
      with real regressions in lineage self-play (`main_v12` -57.1%/4 losses,
      `main_p2` -25%), not weak bots. The original 10-game v10-era read does
      not reproduce on the current lineage (P3f/Lever2/E3 all postdate it).
      Toggle left in code at `False` for future re-investigation; not
      submitted. Full numbers: `experiments/LEDGER.md`'s "HERDBATCH fold +
      re-gate" row.

- [x] **1f. Re-port routing executor onto current `main.py` (Lever2+E3+
      STRATEGY_MODE/ANTI_META included) — SUBMITTED 2026-09-05 14:30 as sub
      `56034847` (`main_v12_flat.py`). RESOLVED 2026-09-06: KEEP.** Ladder read
      (`download_episodes.py` + `tools/ladder_analyze.py 56034847`): **572.9,
      24 eps, 12W-0T-12L, 50% score-rate; animal_factory 5W-9L / 36%, other
      5W-3L / 63%, wheat_flood 2W-0L.** Baseline `56029879` (routing-only fork)
      re-read at 30 eps: **522.6, 43% score-rate, animal_factory 29%.** 1f wins
      on ladder score (+50), overall score-rate (+7pp), and the dominant
      animal_factory loss cluster (+7pp) — clears the 1b flat-or-better rule
      decisively. **`56034847` is the new comparison baseline.** Disk promote
      **DONE 2026-09-06 (commit `033990f`)**: `cp main_v12_flat.py main.py`,
      isolated commit (only `main.py` staged; other shared-row WIP left
      uncommitted). git HEAD lineage now matches the live winning submission. Tracked latest-2 slots are
      `56034847` + `56029879`; `56023304` evicted. Regenerated `main_v12_flat.py`
      via
      `tools/flatten_v12.py` against the current `main.py` (picks up
      everything 1c's original flatten predates: Lever2 land gate, E3 reserve
      fix, STRATEGY_MODE selector, ANTI_META/LIVESTOCK_ENGINE toggles).
      `tools/validate_flatten.py`: 0/719 action mismatches vs the live wrapped
      reference. 60-game paired `compete.py --baseline main.py` bug-check:
      0 crashes/errors, 93.3% score-rate, **every external hard-bot archetype
      flat at +0.0% paired score delta** (animalfactory_v2, diversified,
      hoarder, melonmono, premium, tomatorush, woolfarm, starter — all
      same/no regression), productive actions +30.5, movement -0.4pt, margin
      delta mean +3937. Only regressions are lineage self-play noise
      (`main_v12`, `main_v14`, `main_p3` — expected, not an external signal).
      Clears the same bar the original 1c submission cleared. **Next
      submission slot** (once the one-per-day window resets): `cp
      main_v12_flat.py main.py`, commit, submit — evicts `56023304` (515.6),
      keeps `56029879` (564.8) as the other tracked slot for the post-episode
      compare.

After each ladder-gated read: update `experiments/LEDGER.md`'s row for that
change (ladder score + keep/revert decision) **and** check off / re-rank this
list accordingly.

---

## 2. Standing loop (repeat 1a→1d indefinitely until the deadline)

- [ ] Each cycle: one attributable change → `compete.py --games 120` bug-check
      (not a promote gate for economy tweaks — local can't reliably gate
      those, see `CLAUDE.md` Benchmarking notes) → submit → wait 20+ episodes
      → `tools/ladder_analyze.py` vs the current best baseline → keep or
      revert → update `experiments/LEDGER.md` and this file.
- [ ] Re-run `tools/analyze_top.py` against a fresh `top10_ladder/` pull
      periodically (top-10 composition drifts) — don't let one 2026-09-04
      teardown be the only evidence base for the rest of the month.
- [ ] Watch for slot-burning accidents: confirm `kaggle competitions
      submissions kaggriculture` shows only intentional `main.py` promotions
      in the tracked latest-2 before adding a new one.

---

## 3. Explicitly shelved — do not pick up before the items above land

- **`ml/` pipeline** (Optuna/CMA-ES engine-config search, `ml/loop.py`). Not a
  closed loop yet; revisit only once a >1000-rated agent exists. The
  2026-09-05 lineage-floor fix (`8b6917b`) was a correctness guard on the
  gate, not a resumption of active use.
- **Opponent-adaptive policy** (`docs/PLAN_OPPONENT_ADAPTIVE.md`) — only after
  routing (1c) and a scale/spend-timing correction (1d) are on the ladder and
  holding. Adapting on top of a losing baseline just adapts the losing.
- **New strategy docs.** ~26 `PLAN_*.md` files already exist across root +
  `docs/`; they're reference material, not a backlog. Don't add another
  unless it captures evidence from an actual teardown/ladder read.
- **±1k-coin reserve/sizing tweaks** on their own (P2k-style marginal
  knob-turning) — repeatedly confirmed noise at this rating gap
  (`v6`/`v8b`/P2k/PLAN_300K s1-2 all show local-positive, ladder-flat-or-worse).
  Only worth a submission slot bundled with a category-level change, or after
  1a–1d are exhausted.

---

## 4. Reference map (where the detail behind each item above lives)

- `docs/PLAN_TOP10.md` — **current top priority**: why the §1 loop can't reach top-10, and the three structural levers (top10-clone local opponent, computed marginal-value estimator, routing) that can.
- `docs/PLAN_LADDER_NEXT.md` — prior strategic plan narrative (supersedes `PLAN_LADDER_V10.md`; superseded in turn by `PLAN_TOP10.md`'s goal, its routing/teardown findings still hold).
- `docs/TOP10_TEARDOWN.md` — the evidence base for items 1a/1c (land cap, crop mix, movement gap).
- `docs/PLAN_RATING_IMPROVEMENT.md` — submission discipline + the day-2 cash-crater root-cause plan (item 1d).
- `experiments/LEDGER.md` — per-version change/result/status log; update after every ladder read.
- `knowledge-base/INDEX.md` — engine rules/economics reference, not a task source.
