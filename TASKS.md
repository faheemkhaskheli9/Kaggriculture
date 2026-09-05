# TASKS — path to the top of the leaderboard

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

- **Last updated:** 2026-09-05 (later — 1b resolved flat/keep, `main_v12_flat.py` re-validated and ready for the next slot, 1d root-caused with a Gate-B-passing candidate not yet submitted)
- **Next submission slot: `main_v12_flat.py` (item 1c, routing).** Ready now — 0 mismatches, 95.0% local score-rate. The slot *after* that: fold `experiments/probe_e3_animalreserve.py`'s one-line fix (item 1d) onto whatever `main.py` is current post-routing, re-gate, submit. Do not bundle the two into one submission.
- **Explicit goal as of 2026-09-05: rank ≤10 (~2850-3010 rating), not "any improvement."** The §1 queue below (one hand-tuned constant per submission, ~2-3 day ladder-gated read, ~15-20 reads left before deadline) cannot reach that bar even in principle — see `docs/PLAN_TOP10.md`'s "Why" section for the math. §1 items still get done (they're free/queued), but the three levers in `PLAN_TOP10.md` (top-10-caliber local opponent from `top10_ladder/` replays, computed marginal-value estimator replacing hardcoded priority constants, routing fix as the execution substrate) are now the actual priority. Start there, not at 1d.
- **Lever 1 status (tuned this session, `ecd1d03`→`479829e`):** `bots/bot_top10clone.py` built from real `tools/analyze_top.py` numbers (permanent 3-quadrant land cap, STRAWBERRY-primary day-ramped crop mix, 10-head COW/SHEEP-heavy herd) and fixed through two real bugs (v1: holding the day-20 58/40 split from turn 0 starved early cash, 20-0 loss; v2: a 15-head herd outran the crew's feed capacity, escape/rebuy cash-burn cycle). Then ran a proper 15-game-per-variant comparison against `main.py` specifically (not just a neutral opponent): current config (opp final money ~9.9k mean) beat both a bigger 15-head herd (~4.1k) and a simplified 2-crop/faster-land variant (~6.7k), so those were reverted. **Verdict: still the weaker of the two archetypes against `main.py`** — `bot_animalfactory_v2` reads ~19.0k opp money on the same protocol — even though `bot_top10clone` wins a neutral head-to-head against `bot_animalfactory_v2` 5/8 (15.2k vs 11.4k mean money). Read as an intransitivity: `main.py`'s own strawberry-heavy mix (post P4b+cropflip) directly competes with `bot_top10clone`'s for the same premium-price ceiling in a way it doesn't with animalfactory's wheat-heavy one. Likely the generic `_kagri_botlib` engine's real ceiling for a strawberry-heavy field (more per-tile watering upkeep than wheat), not a remaining tuning problem — further local knob-turning on this bot is now lower-priority than starting Lever 2 itself. Keep it in the pool as a second distinct hard archetype. Re-run `tools/analyze_top.py` + re-derive (don't hand-tune further) if `top10_ladder/` gets refreshed.
- **Lever 3 status:** `main_v12_flat.py` was validated against `main.py` @ `be12348` earlier this session — **now stale**, since `main.py` has since moved to Lever 2 (`a146a5e`). Re-run `tools/flatten_v12.py` + `tools/validate_flatten.py` against the current `main.py` before submitting item 1c.
- **Lever 2 status (`a146a5e`, `main.py`):** computed marginal-value estimator implemented — `_crop_tile_value()` (real engine growth/price constants) drives both `choose_crops`' crop-mix selection (replacing the hand-set STRAWBERRY/TOMATO/etc. shares) and the quadrant-4 land gate (replacing the `n_units>=18` threshold with a computed capacity+ROI check). Bug-check clean: 95.0% full-pool score-rate, 0 errors across ~230 local games, `quads29` holds at 3.0 every game (reproduces finding 1 without a tuned threshold). **But the targeted hard-bot reads (35 games each vs `bot_top10clone.py` and `bot_animalfactory_v2.py`) show no measurable local improvement over the P4b+cropflip baseline** — both within noise of the pre-Lever2 numbers. Full details + numbers: `experiments/LEDGER.md`'s Lever 2 row. **Not submitted** (today's slot used). Real verdict needs a ladder read, not another local probe — this repo's own history says local can't gate economy changes either way. Decision for the next submission slot: ship item 1c (routing, lower-risk, already mechanically validated) first, then Lever 2, rather than jumping the queue on an unproven-but-structurally-sound bet — flag this order to the user before acting on it, since it's a real judgment call.
- **Environment hazard found this session:** a `main.py` edit silently reverted to the last committed HEAD between an Edit call and a later test run (file mtime predated the edit, content matched HEAD exactly, no visible error) — happened twice (once on `bots/bot_top10clone.py`, once on `main.py`). Cause unknown. **Mitigation going forward: after any edit to a file about to be tested, verify with `grep`/mtime that the change actually persisted on disk *before* trusting a test result, and commit promptly rather than leaving meaningful work uncommitted.**
- **Ladder rank:** ~5424/7533 as of the 2026-09-04 audit (`docs/PLAN_LADDER_NEXT.md`) — **re-check live**, don't trust this number past a few days.
- **`56016363`** (v11+feedfloor, anchor, submitted 2026-09-04 16:29): **508.3** on **30 episodes** (15W-0T-15L, 50% score-rate; animal_factory 3-12/20%).
- **`56023304`** (P4b+cropflip, submitted 2026-09-05 02:35): **541.0** on **23 episodes** (11W-0T-12L, 48% score-rate; animal_factory 3-10/23%, other 6-2/75%, wheat_flood 2-0/100%).
- **1b resolved (2026-09-05, 23+30 eps, re-read via `download_episodes.py` + `tools/ladder_analyze.py`):** `56023304` (48%) vs anchor `56016363` (50%) — **flat within noise**, not the "trending toward regress" read the 10-episode sample suggested. Per the stated decision rule (keep if flat-or-better), **`56023304` stays incumbent; no rollback.** The load-bearing fact from this read isn't the overall rate, it's that **animal_factory win-rate is ~20-23% on both submissions** — identical within noise despite the land-cap/crop-mix constant change between them. This confirms the `IMPACT_RANKED_LEADERBOARD_PLAN.md` diagnosis directly: hand-tuned-constant patches (P4b, cropflip, Lever 2's computed gate) are not moving the dominant loss cluster at all. Next submission slot goes to **1c (routing)** per both this file's queue and `PLAN_TOP10.md`'s sequencing — do not spend another slot on a constant-level tweak.
- **Top of leaderboard:** ~3000 rating (Crop Dusta 3009.3; top-20 band 2850–3010).
- **Deadline:** 2026-09-30 23:59. $50,000 prize.
- **`main.py` on disk right now:** Lever 2 (commit `c9ab4ff`, docstring header now says v14 — see `agents/main_v14.py`), NOT what's submitted. The submitted `56023304` is the older `P4b+cropflip` (`be12348`) snapshot — item 1a is done, 1b is in progress (waiting on episode count).
- **`agents/main_v14.py`** (new, this session): frozen snapshot of the current `main.py` (v11 + P4b/cropflip + Lever 2), added to the lineage/compete.py pool per `CLAUDE.md`'s "Agent lineage" convention. `main.py`'s own docstring header was also corrected from a stale "v11" label to "v14" (code untouched, docstring-only diff, re-verified via `compete.py` after the edit).
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
- [ ] **1c. Submit `main_v12_flat.py` (routing fix) — re-validated 2026-09-05,
      ready for the next submission slot.** Was stale (generated 08:48, before
      Lever 2 landed at 10:35); regenerated via `tools/flatten_v12.py` against
      current `main.py` (post Lever 2, `bb73e7b`) and re-checked:
      `tools/validate_flatten.py` → 0/719 action mismatches, Kaggle's
      `get_last_callable` resolves `agent` correctly; `compete.py --games 60`
      → 95.0% score-rate, 56W-2T-2L, 0 crashes/errors, +3497 mean margin vs
      `main_v14` (current lineage) specifically. This is the Hungarian-
      assignment executor whose earlier ladder score (123.2) was root-caused
      as a packaging bug, not a real regression (`023aadb`) — last unresolved
      item from `docs/TOP10_TEARDOWN.md` (movement 60% ours vs 47–48%
      top-10). **Action: submit as the next slot**, then ladder-gate it the
      same way as 1b (20+ eps, compare score-rate + animal_factory row vs
      `56023304`).
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
      Lever 2). Full writeup: `experiments/LEDGER.md`'s "E3 animal-reserve"
      row. **Not yet on `main.py`** — queue for the submission slot *after*
      1c per `docs/PLAN_TOP10.md` sequencing (one change per slot, don't
      bundle with routing).
- [ ] **1e. Submit `main_herdbatch.py`'s F1 herd-match** (dawn herd BATCH
      bootstrap, gated on a visible animal opponent) — local-clean vs v10
      (`bot_animalfarm` 2-0-8 → 9-0-1, other rows byte-identical), targets
      `animal_factory` (~56% of the ladder pool). Fold onto whatever `main.py`
      is current at that point rather than submitting the standalone file.

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
