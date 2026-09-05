# TASKS — path to the top of the leaderboard

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

> **Current operating plan (2026-09-05):** use
> `docs/IMPACT_RANKED_LEADERBOARD_PLAN.md`. It supersedes the ordering in this
> file where they conflict. The next implementation task is E0: paired A/B
> evaluation; no strategy candidate should be promoted from unpaired coin
> results.

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

---

## 0. Snapshot (update the date whenever you touch this file)

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
- **Last updated:** 2026-09-05 (later — 1b resolved flat/keep, `main_v12_flat.py` re-validated and ready for the next slot, 1d root-caused with a Gate-B-passing candidate not yet submitted; later still — Workstream A land/animal rule-mining complete; later still — **1c submitted**; later still — **E3 (1d) folded onto `main.py` as `ENABLE_E3_ANIMAL_RESERVE`, re-gated with a weaker/ambiguous result — see below, don't cite the original +5.0% number anymore**; later still — **1e (HERDBATCH) folded onto `main.py`, re-gated NEGATIVE, default set `False`, not submitted**)
- **1c submitted (2026-09-05 09:45, sub `56029879`, `main_v12_flat.py`, PENDING).** Routing fix (Hungarian-assignment executor), re-validated same-day against current `main.py` post-Lever2: 0/719 action mismatches, 95.0% local score-rate. This evicts one of the 2 tracked slots — the pair to compare after 20+ episodes is `56029879` vs `56023304` (P4b+cropflip, currently 527.3). **Checked this session: only 2 episodes accrued (1 validation + 1 public, publicScore 501.5) — far short of the 20+ needed; do not read anything into 501.5 yet.** Do not submit anything else today.
- **E3 (item 1d) folded onto `main.py` itself (2026-09-05, this session): `ENABLE_E3_ANIMAL_RESERVE` (default `True`) + `E3_OFF_FIXED_MARGIN=300`**, following the standing per-hunk toggle convention. Self-test (E3-OFF copy vs pinned pre-edit `main.py`, 20 pairs) confirmed the toggle mechanism is an exact +0.0%/+$0 no-op. **The real gate on the current lineage (100 pairs, full pool incl. the 4 new archetype bots) reads much weaker than the original probe: +3.0% score delta, 90% CI [+0.0%,+7.0%] (touches zero), margin delta NEGATIVE (-2943), one regression in the closest lineage self-play (`main_v14`, 0/3/1).** Every real hard-bot archetype (animalfactory_v2/wheatflood/premium/animalfarm) now reads 0% score delta with negative margin. Kept ON by default (still net-positive direction, a logically real accounting-bug fix, and per `CLAUDE.md` local can't reliably gate economy changes either way) but **no longer citable as a clean Gate-B pass** — cite `experiments/LEDGER.md`'s new "E3 folded onto main.py + re-gated" row, not the original +5.0%/CI[+1.7,+10.0] read. Next submission slot (once the one-per-day window resets) still goes to `main.py` with this fix included per the existing queue order — flag the weaker re-gate to the user before that submission.
- **Explicit goal as of 2026-09-05: rank ≤10 (~2850-3010 rating), not "any improvement."** The §1 queue below (one hand-tuned constant per submission, ~2-3 day ladder-gated read, ~15-20 reads left before deadline) cannot reach that bar even in principle — see `docs/PLAN_TOP10.md`'s "Why" section for the math. §1 items still get done (they're free/queued), but the three levers in `PLAN_TOP10.md` (top-10-caliber local opponent from `top10_ladder/` replays, computed marginal-value estimator replacing hardcoded priority constants, routing fix as the execution substrate) are now the actual priority. Start there, not at 1d.
- **Lever 1 status (tuned this session, `ecd1d03`→`479829e`):** `bots/bot_top10clone.py` built from real `tools/analyze_top.py` numbers (permanent 3-quadrant land cap, STRAWBERRY-primary day-ramped crop mix, 10-head COW/SHEEP-heavy herd) and fixed through two real bugs (v1: holding the day-20 58/40 split from turn 0 starved early cash, 20-0 loss; v2: a 15-head herd outran the crew's feed capacity, escape/rebuy cash-burn cycle). Then ran a proper 15-game-per-variant comparison against `main.py` specifically (not just a neutral opponent): current config (opp final money ~9.9k mean) beat both a bigger 15-head herd (~4.1k) and a simplified 2-crop/faster-land variant (~6.7k), so those were reverted. **Verdict: still the weaker of the two archetypes against `main.py`** — `bot_animalfactory_v2` reads ~19.0k opp money on the same protocol — even though `bot_top10clone` wins a neutral head-to-head against `bot_animalfactory_v2` 5/8 (15.2k vs 11.4k mean money). Read as an intransitivity: `main.py`'s own strawberry-heavy mix (post P4b+cropflip) directly competes with `bot_top10clone`'s for the same premium-price ceiling in a way it doesn't with animalfactory's wheat-heavy one. Likely the generic `_kagri_botlib` engine's real ceiling for a strawberry-heavy field (more per-tile watering upkeep than wheat), not a remaining tuning problem — further local knob-turning on this bot is now lower-priority than starting Lever 2 itself. Keep it in the pool as a second distinct hard archetype. Re-run `tools/analyze_top.py` + re-derive (don't hand-tune further) if `top10_ladder/` gets refreshed.
- **Lever 3 status:** `main_v12_flat.py` was validated against `main.py` @ `be12348` earlier this session — **now stale**, since `main.py` has since moved to Lever 2 (`a146a5e`). Re-run `tools/flatten_v12.py` + `tools/validate_flatten.py` against the current `main.py` before submitting item 1c.
- **Top-policy land/animal mining (2026-09-05, `tools/mine_top_policy_rules.py`, Workstream A):** mined explicit BUY_LAND/BUY_ANIMAL preconditions from `top_policy.jsonl` since the classifier can't learn them. Confirmed (not assumed): top-10 farms **never buy the 4th quadrant** (0/17 that reach 3 quadrants go to 4) — corroborates Lever 2's emergent `quads29==3.0` cap independently — and land buys are gated on the *current* land being near-fully planted, not just cash. Animal buys are small (qty 1, rarely 2) and continuous from day 0 through ~day 15, never a multi-animal single-turn batch — the opposite shape of the day-0 $1600/4-animal binge item 1d root-caused. Herd plateaus ~14-15 by day 12. Full numbers + the correctness fix (a replay row's `action` produced *that same row's* state, not the next one — tripped up the first pass) in `experiments/LEDGER.md`'s new top-row.
- **Workstream B candidate built + screened, INCONCLUSIVE as a bundle (2026-09-05, `experiments/candidate_top10rules.py`):** forked `main.py` and encoded the three mined rules as code (land fill-gate 0.55→0.75, hard-disable the 4th quadrant, herd cap {1:3,2:8}/13→{1:6,2:13}/15). 100-pair Gate-B screen vs `main.py`: headline **+3.5% but 90% CI [-0.5%, +8.0%] crosses zero**, carried mostly by the `main`-mirror-match bucket, not the target archetypes.
- **Bisected via per-rule toggles (2026-09-05, same file):** each rule got an `ENABLE_R*` flag + named config constant (config block above `USE_ANIMALS`); all-False reproduces `main.py` exactly (verified: 20-pair self-test, **+0.0% delta, +$0 margin in every game**). Ran each flag alone, 80 pairs: **R1 (land fill) +2.5%, CI [-0.6%,+6.2%] — noise, same pattern as the bundle. R2 (disable Q4) exactly +0.0% in all 80/80 games — a complete no-op locally** (confirms `main.py`'s existing ROI check already never fires true in this population, so hard-disabling it changes nothing here). **R3 (herd cap) +2.5%, CI [+0.6%,+5.0%] — the only one excluding zero**, driven by `bot_top10clone` (the actual top-10 proxy) at +4.2%, but it costs margin (not win/loss) against `bot_animalfactory_v2`/`bot_wheatflood`. **R3 is carrying whatever real signal exists; R1 should be dropped; R2 is harmless but inert.** None individually clears the plan's literal Gate B bar at n=80. Next: either a bigger dedicated R3-only read + investigate the margin cost, or fold this into a real ladder read once a slot is free. Full numbers: `experiments/LEDGER.md`'s "Workstream B bisection" row.
- **Lever 2 status (`a146a5e`, `main.py`):** computed marginal-value estimator implemented — `_crop_tile_value()` (real engine growth/price constants) drives both `choose_crops`' crop-mix selection (replacing the hand-set STRAWBERRY/TOMATO/etc. shares) and the quadrant-4 land gate (replacing the `n_units>=18` threshold with a computed capacity+ROI check). Bug-check clean: 95.0% full-pool score-rate, 0 errors across ~230 local games, `quads29` holds at 3.0 every game (reproduces finding 1 without a tuned threshold). **But the targeted hard-bot reads (35 games each vs `bot_top10clone.py` and `bot_animalfactory_v2.py`) show no measurable local improvement over the P4b+cropflip baseline** — both within noise of the pre-Lever2 numbers. Full details + numbers: `experiments/LEDGER.md`'s Lever 2 row. **Not submitted** (today's slot used). Real verdict needs a ladder read, not another local probe — this repo's own history says local can't gate economy changes either way. Decision for the next submission slot: ship item 1c (routing, lower-risk, already mechanically validated) first, then Lever 2, rather than jumping the queue on an unproven-but-structurally-sound bet — flag this order to the user before acting on it, since it's a real judgment call.
- **Toggle+config infra generalized to `main.py` and `main_auto.py` (2026-09-05).** Following the same pattern as `experiments/candidate_top10rules.py`'s R1/R2/R3 flags, every independently-revertible hunk in both files now has an `ENABLE_*` flag (+ named config constants where the OFF path needs one), in a config block above `USE_ANIMALS`: `main.py` gets 10 (F1, P2, P4 coverage cap, P4c late-weed, Lever2 land-gate, Lever2 crop-mix, P3f, P1w, P4r, feed-emergency-floor); `main_auto.py` gets those same 8 plus 4 more from its own AUTO-iteration history (reserve retune, sell-cap raise, herd-batch bootstrap, and an off-by-default P2k crop-prune kept only so a future re-test doesn't have to re-derive the guard). Every OFF value is the exact prior-version constant/formula (from `agents/main_v7.py`/`main_v10.py`/`be12348`), not a guess. **Verified on both files: 20-pair paired self-test, all flags at default vs. a pinned pre-edit snapshot, +0.0% score delta / +$0 margin delta in every single game** — the refactor is a pure no-op at defaults. Purpose: any future bisection of one of these hunks (the way Workstream B bisected R1/R2/R3) no longer needs a separate forked file.
- **Environment hazard found this session:** a `main.py` edit silently reverted to the last committed HEAD between an Edit call and a later test run (file mtime predated the edit, content matched HEAD exactly, no visible error) — happened twice (once on `bots/bot_top10clone.py`, once on `main.py`). Cause unknown. **Mitigation going forward: after any edit to a file about to be tested, verify with `grep`/mtime that the change actually persisted on disk *before* trusting a test result, and commit promptly rather than leaving meaningful work uncommitted.**
- **Ladder rank:** ~5424/7533 as of the 2026-09-04 audit (`docs/PLAN_LADDER_NEXT.md`) — **re-check live**, don't trust this number past a few days.
- **`56016363`** (v11+feedfloor, anchor, submitted 2026-09-04 16:29): **508.3** on **30 episodes** (15W-0T-15L, 50% score-rate; animal_factory 3-12/20%).
- **`56023304`** (P4b+cropflip, submitted 2026-09-05 02:35): **515.6** on **25 episodes** (11W-0T-14L, 44% score-rate; animal_factory 3-11/21%, other 6-2/75%, wheat_flood 2-1/67%).
- **`56029879`** (main_v12_flat.py, routing fix, submitted 2026-09-05 09:45): **557.1** on **23 episodes** (11W-0T-12L, 48% score-rate; animal_factory 6-11/35%, other 4-1/80%, wheat_flood 1-0/100%). **New baseline (1c resolved KEEP, see §1).**
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

- [ ] **1f. Re-port routing executor onto current `main.py` (Lever2+E3+
      STRATEGY_MODE/ANTI_META included) — re-flattened & re-validated
      2026-09-05, READY, NOT YET SUBMITTED (today's slot already used by
      1c/`56029879`).** Regenerated `main_v12_flat.py` via
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
