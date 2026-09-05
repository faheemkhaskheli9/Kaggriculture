# TASKS — path to the top of the leaderboard

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

- **Last updated:** 2026-09-05 (evening — target changed to top-10, see `docs/PLAN_TOP10.md`)
- **Explicit goal as of 2026-09-05: rank ≤10 (~2850-3010 rating), not "any improvement."** The §1 queue below (one hand-tuned constant per submission, ~2-3 day ladder-gated read, ~15-20 reads left before deadline) cannot reach that bar even in principle — see `docs/PLAN_TOP10.md`'s "Why" section for the math. §1 items still get done (they're free/queued), but the three levers in `PLAN_TOP10.md` (top-10-caliber local opponent from `top10_ladder/` replays, computed marginal-value estimator replacing hardcoded priority constants, routing fix as the execution substrate) are now the actual priority. Start there, not at 1d.
- **Ladder rank:** ~5424/7533 as of the 2026-09-04 audit (`docs/PLAN_LADDER_NEXT.md`) — **re-check live**, don't trust this number past a few days.
- **`56016363`** (v11+feedfloor, anchor, submitted 2026-09-04 16:29): now reads **500.3** on 27 episodes (13W-0T-14L, 48% score-rate; animal_factory 3-11/21%). The 574.6 figure was an early-sample read on ~13 eps and has since converged down — don't cite 574.6 again.
- **`56023304`** (P4b+cropflip, submitted 2026-09-05 02:35): **503.6** on **12 episodes** (5W-0T-7L, 42% score-rate; animal_factory 1-5/17%) — worse than the anchor on both overall and animal_factory, and the land-starvation symptom is now consistent across every game, not scattered noise: avg quads29 3.0 (anchor 3.9, no game past 3) and avg plants29 14 (anchor 26). Still under the 20-ep call threshold, but trending toward **regress**, not flat-or-better. Already used today's one submission slot (`56023304`), so no action until tomorrow regardless — **next session: re-read at 20+ eps first; if it holds <48%/animal_factory<21%, revert to `0c2123d` (v11+feedfloor+P?f3) as tomorrow's single submission and loosen the Q4-gate threshold rather than re-deriving 1d from scratch.**
- **Top of leaderboard:** ~3000 rating (Crop Dusta 3009.3; top-20 band 2850–3010).
- **Deadline:** 2026-09-30 23:59. $50,000 prize.
- **`main.py` on disk right now:** `P4b+cropflip` (commit `be12348`), already submitted as `56023304` above — item 1a is done, 1b is in progress (waiting on episode count).
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
- [ ] **1b. Wait 20+ episodes**, then `python download_episodes.py` +
      `python tools/ladder_analyze.py <sub_id>`. Compare overall win-rate and
      the `animal_factory` row specifically against the anchor `56016363`
      (converged read: 500.3/48%, animal_factory 21% — **not** 574.6, that was
      an early-sample noise figure). **In progress**: at 10 episodes (2026-09-05
      mid-day) `56023304` reads 498.8/40%, animal_factory 20% (unmoved, as
      expected), but day-29 plant count is nearly half the anchor's (15 vs 26)
      and quads29 down (3.0 vs 3.9) — land-cap gate is shrinking the farm more
      than intended-looking; flag but don't act until 20+ eps. Keep if
      flat-or-better on score-rate; if it regressed, roll back to `56016363`'s
      commit on the next day's single submission and re-diagnose locally
      first.
- [ ] **1c. Submit `main_v12_flat.py` (routing fix)** once 1b reads clean.
      This is the Hungarian-assignment executor whose earlier ladder score
      (123.2) was root-caused as a packaging bug, not a real regression
      (`023aadb`) — `tools/validate_flatten.py` confirms 0/719 action
      mismatches vs the reference through Kaggle's actual loader path, and
      `compete.py --games 60` reads 96.7% score-rate. This is the last
      unresolved item from `docs/TOP10_TEARDOWN.md` (movement 60% ours vs
      47–48% top-10). Re-run `tools/flatten_v12.py` + `validate_flatten.py`
      first if `main.py`/`agents/main_v12.py` have changed since 2026-09-05.
      Ladder-gate it the same way as 1b before keeping.
- [ ] **1d. Root-cause the day-2 lead-flip / cash-crater pattern**
      (`docs/PLAN_RATING_IMPROVEMENT.md` Phase 3) — the recurring signature
      across worst-game losses (money pinned ~$100–1500 through day 15–20,
      lead flips day 2) that P1/P3f/feed-floor have patched around but never
      root-caused. Trace 8–10 worst-game day-1–3 spend order from
      `tools/analyze_runs.py`, form one falsifiable hypothesis, implement the
      smallest targeted fix, gate on `compete.py --games 120` (animal_factory/
      wheatflood/v5clone rows must not regress, lead-flip rate must visibly
      drop), then queue as the next submission slot.
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
