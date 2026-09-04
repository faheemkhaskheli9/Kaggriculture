> **Status: the §3 minimal first cut is implemented** (2026-09-04) — rotating
> search seed, `compete.py --workers` sharding, worst-opponent-first
> `score_key`, the multi-change "combo" prompt exception, `--focus-pool` /
> `--curriculum-at`, `--reseed-pool` auto-reseed, and the driver
> preflight/backoff. See `tools/AUTO_IMPROVE.md` for the current flags. Not
> implemented: bootstrap-CI promotion gating (P0-#3), the snapshot beam
> (P1-#7), the structured hypothesis backlog / in-iteration self-check
> (P3-#12/#13), and the eval cache (P4-#18) — left for a follow-up pass; see
> §5 below.

# PLAN — break `tools/auto_improve.py` past the 79% plateau

Two runs so far (`tools/auto_improve_runs/20260904-052919`, `-090242`). Run 1
did the work: iter‑0 jumped **50% → 79.2%** with one reserve‑ramp fix, then
iters 1–6 produced **zero net progress** and the run died on `--patience`.
Run 2 was claude‑usage‑limited into a dead OpenAI fallback and did nothing for
~90 min. This plan is about the *loop*, not the agent.

---

## 1. Why it plateaus at 79% (evidence from run 1)

### 1.1 The 79% is "wins the easy half, loses the hard half" — one structural cluster
Per‑opponent from `iter_06/analysis.txt` (and identical shape in every iter):

| bucket | opponents | score‑rate |
|---|---|---|
| easy | bots (wheatflood/premium/melonmono/animalfarm), starter, main_v1‑v3, c_premium, c_wheatflood | ~100% |
| **hard** | **c_v5clone, main_p3, main_p2, main_v4/5/6/7/v11, c_animalfactory** — the crop+animal lineage/clones | **~0%** |

79% ≈ 100% × easy + ~0% × hard. Overall score‑rate **hides** this — it looks
like "a bit more tuning" when it is actually "one matchup class is a shutout."

### 1.2 The hard cluster is a *coordinated multi‑lever* deficit, not one knob
Worst‑game money curves are near‑identical across seeds and opponents:

```
me  d5/10/15/20/25/29 ≈  400 / 450 / 400 / 1.9k / 14k / 30k
op  d5/10/15/20/25/29 ≈  200 / 300 / 500 / 13k  / 45k / 65k
anim 3 (opp 8–11)   quads29 2 (opp 3–4)   our premium sells ≈ ⅓ of opp's
```

The opponent's cash goes 8–16× between day 15 and 20; ours does the same thing
**one cycle later** on a smaller herd and smaller field. Herd size **and** land
count **and** premium production **and** the timing of all three are behind
together. No single change can close that:

- iter 1 (sell caps 6→12/8→14): +0.9%, then never moved again
- iter 4 (contested `keep` 0.80→0.58): **byte‑for‑byte identical metrics to iter 2** (95/0/25, margin 18279) — a no‑op on the paired seed
- iter 3 (flat $200 reserve) and iter 6 (land window day≤24): **regressed to 73% / 53%** — each unbalanced the build because the complementary lever wasn't moved with it, both reverted

`LESSONS.md` itself concludes every individual lever (reserve, seed‑floor,
sell‑cadence, anti‑mirror, land‑timing) is "exhausted." That is the signature of
a search space where the optimum needs **several changes applied together**, and
the loop is architecturally forbidden from doing that ("make exactly ONE
attributable change").

### 1.3 Past iter 1 the loop is optimising noise
- **Fixed `--pick-seed 20260904` every iteration** → the exact same 120 matchups
  forever. `regress-tol 0.02` ≈ 2.4 games. iter‑to‑iter deltas (78.3 ↔ 79.2)
  are a **1‑game swing**. The accept/reject decision is inside the noise band.
- Per‑opponent cells are `0/0/4`, `2/0/5` — no power to tell a 5% real change
  from variance.
- `verify` (fresh seed) only runs *on success*, so the search is free to
  overfit the 120 games and call it 79%.
- The next fix is always forked from `best.py` / `auto` — i.e. the same 79.2%
  file — so consecutive iterations explore the same basin from the same point.

### 1.4 Continuity is lossy
- `ledger_digest(keep_iters=4)` → by iter 6 the driver can't see iter 0–1's
  reasoning.
- `analysis[:12000]`, `auto_diff[:8000]` truncation.
- The driver edits **blind**: cost of a bad hypothesis is a full ~25‑min
  iteration before the loop discovers it regressed.

### 1.5 Robustness
- Run 2: `claude` usage‑limited → `--fallback-driver openai` → `OPENAI_API_KEY
  not set` → 5 iterations of `FAILED (no change applied)`, `it += 1` each time,
  run burns its budget doing nothing. No preflight, no backoff.

### 1.6 The metric can't gate the target anyway
`CLAUDE.md` (Benchmarking notes) is explicit and repeatedly confirmed: local
`compete.py` **cannot gate a `main.py` economy change**. `best.py` at 79% is a
*candidate signal*, not a promotable result. The loop's success banner implies
otherwise.

---

## 2. The fix — priority order

### P0 — Kill the noise floor (enables everything else)
**Problem:** §1.3 — decisions are made inside a ±1‑game band on a frozen matchup set.

1. **Rotate the search seed per iteration:** evaluate the candidate on
   `pick_seed + it` (fresh matchups each round). Keep `pick_seed` (frozen) as a
   **held‑out** set used *only* for best.py promotion and the success gate.
2. **Raise the accept/reject game count to ≥300** (currently 120). Make it
   affordable by **sharding `compete.py`** across processes — games are
   independent; a `--workers N` that splits `--games` and merges manifests is a
   small change and is the single biggest throughput win.
3. **Bootstrap CI on Δscore‑rate vs `best`.** Accept a new best only when the
   2.5th‑percentile of the paired bootstrap delta is `> 0` (not just
   `score_key` strictly greater). Reject noise‑driven "new best" snapshots.
4. **Adaptive budget:** 60 games for the cheap exploration eval, promote to the
   full ≥300 only for a candidate that clears `best - regress_tol` on the cheap
   pass.

### P1 — Give the loop a way out of the basin (§1.2)
**Problem:** the optimum needs coordinated changes; the loop does one at a time
and always restarts from the same file.

5. **Allow a multi‑hunk "combo" iteration.** The driver may declare
   `"interdependent": true` and make 2–4 coordinated changes in one iteration,
   with a larger verify budget attached. Gate it to iterations where the
   diagnosis names ≥2 co‑moving deficits (herd + land + premium…).
6. **Basin‑hopping / stacked replay.** Every `K` iters with no new best, the
   loop itself builds a candidate that **stacks the 2–3 best previously‑reverted
   hunks** (tracked in the backlog, P3‑#12) and evaluates the combination
   before handing back to the driver. Most reverted single levers here were
   *directionally right* and only failed alone.
7. **Snapshot beam, not a single `best.py`.** Keep the top‑M snapshots. Each
   iteration round‑robins the fix *base* across the beam, so the search isn't
   permanently anchored to one 79.2% point.
8. **Auto‑reseed instead of stopping.** When `patience - 1` is hit, reseed
   `main_auto.py` from a different lineage (`agents/main_v11.py`,
   `main_herdbatch.py`) and keep going — a different basin, same budget.

### P2 — Point the objective at what's actually stuck (§1.1)
**Problem:** overall score‑rate averages away the shutout cluster.

9. **Lexicographic objective:** `(worst_archetype_score_rate, overall_score_rate,
   margin_mean)`. A change that lifts c_v5clone from 0% to 25% now *wins* the
   comparison even if overall is flat.
10. **Curriculum.** Once overall ≥ ~0.72, switch the pool to **only the losing
    cluster** (`--pool c_v5clone main_p3 main_v5 main_v6 main_v7 c_animalfactory`)
    so every iteration focus‑fires it; re‑verify the winner on the full pool
    before accepting. Wire a `--focus-pool` / `--curriculum` flag.
11. **Ladder‑weight the pool.** `animal_factory` ≈ 56% of real ladder games
    (`CLAUDE.md`, `docs/PLAN_LADDER_ECON.md`). Add `--pool-weights` so sampling
    (and the reported primary score) matches the distribution that decides the
    ladder, not a flat archetype count.

### P3 — Tighten the driver's inner loop (§1.4)
12. **Structured hypothesis backlog** (`backlog.json`, not prose): one row per
    `{lever, direction, iter_tried, delta_score, ci_low, ci_high, verdict}`.
    The prompt shows it in full; the driver **must** pick an untried lever/direction
    and may not re‑propose a `verdict != promising` row. Replaces the lossy
    4‑iter digest for "don't repeat a reverted change."
13. **In‑iteration self‑check.** Give the driver a restricted `compete.py
    --agent main_auto.py --games 40` it can call on its own edit before
    finalising, plus 2–3 attempts against a per‑iteration mini‑budget. It
    self‑rejects a bad hypothesis in minutes instead of the loop finding a −6%
    a full cycle later.
14. **Pre‑digested diagnosis in the prompt.** Put the money‑curve table +
    per‑opponent sell‑mix deltas (already produced by `analyze_runs.py
    --worst`) into the prompt as structured text. The driver currently
    re‑derives this from `*.replay.json.gz` by hand every iteration.
15. `keep_iters` 4 → all iterations, each summarised to one line once older than
    4; pass full `LESSONS.md`. Raise the `analysis` / `auto_diff` truncation
    caps or switch to a section‑aware trim.

### P4 — Robustness / throughput (§1.5)
16. **Preflight** before the baseline eval: (a) one‑token driver ping;
    (b) if the only driver is `claude` and `--fallback-driver openai` but
    `OPENAI_API_KEY` is unset, abort with a clear message — don't start.
17. **Usage‑limit backoff:** when no working fallback exists, exponential
    sleep‑and‑retry the same iteration; never `it += 1` on a "no change applied"
    failure.
18. **Eval cache** keyed by `sha256(main_auto.py) + pool + seed + games` so
    reverts and no‑op edits (iter 4!) don't re‑pay the game budget.

### P5 — Acceptance realism (§1.6)
19. Success path: loud banner that local score **cannot** gate a `main.py`
    economy change; write the **top‑3** beam snapshots + their per‑archetype
    tables to the run dir; frame the output as "A/B these yourself + submit one,"
    not "promote `best.py`."

---

## 3. Minimal first cut (highest ROI, ~1 day)

Do these four; they address §1.2 and §1.3 directly and are self‑contained:

1. **P0‑#1 + P0‑#2** — rotate search seed, held‑out promotion seed, `--games`
   default 300 with a `compete.py --workers` shard. *(noise)*
2. **P1‑#5** — permit a 2–4 change combo iteration when the diagnosis flags
   co‑moving deficits. *(basin)*
3. **P2‑#9 + P2‑#10** — lexicographic worst‑archetype objective + a
   `--focus-pool` curriculum flag. *(aim)*
4. **P4‑#16 + P4‑#17** — driver preflight + usage‑limit backoff. *(don't waste
   a run)*

Then re‑run:

```bash
python tools/auto_improve.py --games 300 --workers 6 \
  --curriculum --focus-pool c_v5clone main_p3 main_v5 main_v6 main_v7 c_animalfactory \
  --target 0.60 --max-iters 20 --max-hours 14 --patience 8
```

## 4. Sidebar — the fast manual shortcut

The loop's own ledger already contains the ingredients. A hand‑built
`main_auto.py` that **stacks iter‑1 (sell caps) + iter‑5 (premium anti‑mirror
gated to ONE_TIME) + a herd‑and‑land timing pair** and is A/B'd once vs `main.py`
on 300 fresh‑seed games is the quickest test of the "coordinated multi‑lever"
hypothesis in §1.2 — and it needs no tooling change. Worth doing in parallel to
de‑risk the plan.

## 5. Deferred from this pass

Kept out of the first implementation to keep it reviewable; still worth doing
if the v2 flags don't clear the plateau on their own:

- **P0‑#3 bootstrap CI on Δscore vs best.** `compete.py`'s own `rng =
  random.Random(pick_seed)` makes two runs at the same `--pick-seed` genuinely
  paired (identical opponent/seed/seat sequence), which is what a paired
  bootstrap needs — the manifest.json rows already have per-game results, so
  this is a read of two manifests + resampling, no `compete.py` change
  required. Would tighten the "new best" acceptance beyond the current
  lexicographic `score_key`.
- **P1‑#6/#7 stacked-revert replay and a snapshot beam.** The auto-reseed
  (`--reseed-pool`) implemented now escapes a *different* way (a different
  lineage file) rather than stacking this run's own reverted hunks or keeping
  multiple live snapshots; both are bigger, riskier refactors of the
  accept/reject bookkeeping.
- **P3‑#12/#13 structured backlog + in-iteration self-check.** The combo
  exception (P1‑#5) and the fuller ledger digest (`keep_iters` 4→8, higher
  truncation caps) cover part of this; a JSON backlog and letting the driver
  run its own mini `compete.py` A/B before finalizing are still open.
- **P4‑#18 eval cache.** Reverts and no-op edits (iter 4 in run 1) still re-pay
  the full game budget.

## 6. Non‑goals / risks

- **Don't** just raise `--max-iters` / lower `--patience` on the current design —
  §1.3 means it will keep sampling noise.
- **Don't** trust a local `best.py` as promotable (§1.6). Every candidate still
  goes through a manual A/B + single Kaggle submission.
- Curriculum on the loss cluster can **overfit to the clones** and regress the
  easy half — the full‑pool re‑verify in P2‑#10 is mandatory, not optional.
- More `compete.py` parallelism raises peak CPU/RAM; `--workers` should default
  conservative.
