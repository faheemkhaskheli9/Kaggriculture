# PLAN_ML_IMPROVE.md — making the `ml/` pipeline produce a promotable agent

Written 2026-09-02. Follow-on to `PLAN_ML_MODELS.md` (the survey) and the built
`ml/` pipeline. This plan is about **closing the gap between what the pipeline
produces and what `main.py` already is**, then pushing past it.

---

## Progress (2026-09-02)

- **A1 DONE.** `ml/engine_v7.py` = a faithful, parameterised fork of `main.py`
  v7. `ml/spec_v7.py` exposes 65 knobs (16 in `PHASE1_V7` = the L1-L5 economy
  levers); every default equals v7's hard-coded value. **Verified byte-identical
  to `main.py`**: 0 action mismatches over 719 steps on 3 seeds vs
  starter/animalfarm/wheatflood.
- **B1 DONE.** `ml/league.py`: `animalfactory_v2` added; `gate` = `[animalfactory_v2,
  animalfarm, wheatflood, premium, v4, main]`; new `ladder_econ` (PLAN_LADDER_ECON
  §4) and `heldout` (`[melonmono, v6, premium, starter]`, never optimised) groups.
- **B2 DONE.** `ml/evaluate.py::fitness` is now the promote rule: disqualify on
  errors, `score_rate < 0.45` vs any `*animal*` opponent, mean terminal unsold
  > 3, ms/step > 4, or p10 below `--baseline-p10`. Survivors ranked by
  `0.5·worst_sr + 0.3·mean_sr + 0.2·coin_bonus`. `terminal_unsold` now measured.
- **B3/B4 DONE.** `ml/optimize.py --heldout <league>` scores (never optimises) a
  held-out set each generation → `history.csv` (`heldout_fitness`/`heldout_sr`).
  `--rotate-seed` gives a fresh map-seed block per generation.
- **C1 DONE.** CMA-ES already warm-starts at the spec default; `--sigma0`
  default lowered 0.25 → 0.15. `--engine {v7,legacy}` selects the stack;
  `ml/export_main.py --engine v7` bundles the v7 fork (34 KB, stdlib-only).
- **Measured v7 baseline vs `gate`** (engine v7, defaults, 8 games/opp, seed
  10M): **DISQUALIFIED** — `mean_sr 0.438`, `animalfactory_v2 0.38`, `animalfarm
  0.12`, `v4 0.00` (−36k), `premium 1.00`, `main 0.50`. `mean_coins 24.7k`, p10
  6120, 0 err, 0.47 ms. This is the bar: the optimiser must lift the animal
  matchups over 0.45 without breaking `premium`/`main`.
- **TODO:** C2 multi-fidelity successive-halving; C3 surrogate; C6 the
  `ml/optimize` driver still accumulates per-gen JSON (fine) — `test.py` OOM is
  already fixed on disk. D (predictor) and E (policy net) unstarted.

---

## 0. Where the pipeline stands (measured)

`ml/` runs end to end: Phase-0 probe, Phase-1/2 CMA-ES over a parameterised
engine (`ml/engine.py` + `ml/spec.py`), paired league eval with a
fragility-weighted `fitness` (`ml/evaluate.py`), `ml/export_main.py` →
stdlib-only submission, plus an opponent-sell predictor (`ml/predictor/`,
+62 % MAE lift on 58 replays). `ml/clone/` and `ml/rl/` are scaffolds.

**The blocking problem:** `ml/engine.py` is a fork of `bots/_kagri_botlib.py`,
**not** `main.py`. With default knobs it beats the `bots/` archetypes but
**loses 0-4 / ~28-36k coins to `main.py` (v5/v7)**. So the optimiser is
polishing a base that starts ~30k behind the thing we ship. No amount of CMA-ES
on the wrong engine produces a promotable artifact.

Everything below is ranked by **expected value per unit effort**, not by
research interest.

---

## 1. Lever A — Re-base the engine on `main.py` v7  *(do this first)*

The optimiser can only be as good as the engine it parameterises. Forking
`_kagri_botlib` was convenience; it has to be redone off the strong base.

- **A1 (recommended):** create `ml/engine_v7.py` — a faithful fork of
  `main.py` (the v7 zoned core, ~860 lines) with its real constants and the
  L1–L5 economy levers from `docs/PLAN_LADDER_ECON.md` exposed as a `config`
  dict:
  - existing constants: `reserve`, hire curve, land day/fill gates, crop
    schedule (`choose_crops` weights), `animal_targets`, sell keep-fractions
    and caps, endgame hours;
  - new economy knobs: working-capital floor curve `max(a, b - c*day)`,
    `seed_cap`, `seed_lookahead`, herd pace (animals/turn, buffer base +
    per-head), FERTILIZER/WOOL/MILK sell cadence, planted-area cap vs crew
    size.
  - Engine math must stay line-identical; every knob **defaults to v7's
    current value** so `default_params()` reproduces `main.py` exactly.
- **A2 (alternative):** fork `contenders/_engine.py` instead — it already has
  `seed_cap` / `seed_lookahead` / day-ramped `_animal_target_fn` and powers
  the `c_*` contenders. Cleaner parameterisation, but one step removed from
  what we submit. Use only if A1's constant-extraction proves too invasive.
- Keep `ml/engine.py` (`_kagri_botlib` fork) as the **fast smoke target** only.

**Exit criterion:** `python -m ml.evaluate --default --league gate` with the new
engine scores ~50 % vs `main.py`, mean-diff ≈ 0, 0 errors, ≤ 4 ms/step —
i.e. the fork is behaviourally v7 before any optimisation runs.

---

## 2. Lever B — Fix the gate and the fitness  *(do this with A)*

Without this, evolution overfits the local league harder than the hand-tuning
did — this is the **477 wall** (`knowledge-base/06 §6`, `experiments/LEDGER.md`:
48-0-0 local has coexisted with 6-0-7 ladder).

- **B1 — real opponents.** Add `animalfactory_v2` →
  `bots/bot_animalfactory_v2.py` to `ml/league.py::BOTS`. Redefine:
  - `gate = [animalfactory_v2, animalfarm, wheatflood, premium, v4, main]`
  - new `ladder_econ = [animalfactory_v2, animalfarm, v4, main, wheatflood,
    premium, starter]` (the `PLAN_LADDER_ECON §4` promote gate, verbatim).
- **B2 — fitness = the promote rule, not a weighting.** In
  `ml/evaluate.py::fitness`, **disqualify** (return ≈ −1) any config that:
  score-rate < 0.45 vs *any* animal opponent · OR p10_coins < v7 baseline p10
  · OR terminal_unsold > 3 · OR ms_step > 4 · OR errors > 0.
  Among survivors only, maximise
  `0.5·worst_sr + 0.3·mean_sr + 0.2·norm(mean_coins vs animal opps)`.
  A high-fitness config is then promotable *by construction*.
  (Needs `terminal_unsold` surfaced into the report — port `test.py`'s
  `analyze_replay` unsold count, or recompute from the final obs.)
- **B3 — held-out opponents.** Reserve a set never used in search
  (`melonmono`, `v6`, a 2nd animal-factory variant). Report fitness on it every
  generation. Train-fitness rising while held-out flat = overfit → stop, take
  the last checkpoint where both moved together.
- **B4 — seed hygiene.** Rotate the map-seed base per generation so the search
  can't memorise maps; use a larger fixed seed **bank** for the final
  expensive eval and for `test.py` promotion.

---

## 3. Lever C — Search efficiency and robustness

More signal per CPU-hour; insurance against premature convergence on ~55 dims.

- **C1 — warm-start.** Init the CMA-ES mean at `to_unit(default_params())`
  (v7's real constants), `sigma0 ≈ 0.15`. Today it starts at the spec midpoint
  and throws the best prior away.
- **C2 — multi-fidelity / successive halving.** Per generation: screen at
  4 games × 3 cheap opponents → keep top ⅓ → re-eval survivors at 12 games ×
  full gate → only those feed `tell()`. ≈ 3× throughput.
- **C3 — surrogate pre-ranking.** Log every `(genes → fitness)` to
  `ml/artifacts/evals.jsonl`. After ~300 rows fit a LightGBM regressor; each
  generation `ask()` 4× popsize, predict, simulate only the top popsize.
  Re-fit every few gens. (Reuses the predictor stack.)
- **C4 — islands.** 3 CMA-ES instances, `sigma0 ∈ {0.08, 0.15, 0.30}`,
  migrate the best genome every ~10 gens.
- **C5 — diagonal covariance for the 55-dim run.** Full covariance needs
  ~dim² well-placed samples to condition; sep-/diagonal-CMA-ES converges faster
  at this budget. Phase-1 (14 dims) can stay full-covariance.
- **C6 — fix the eval OOM.** The `--gate` baseline run died with `MemoryError`
  holding 42 `env.toJSON()` replays. `ml/evaluate.py` already drops replays;
  make sure the driver (`ml/optimize.py`) and `test.py --gate` stream results
  to disk instead of accumulating. Needed before the full-gate v7 baseline can
  even be recorded.

---

## 4. Lever D — Predictor: grow it, wire it, prove it earns its bytes

- **D1 — corpus.** `python download_episodes.py` → pull 100+ recent ladder
  replays (current 58, ~half self-play). Retrain; the +62 % lift is on thin,
  biased data.
- **D2 — wire it as a knob.** Feed `Predictor.predict()` into the engine's
  sell sizing as tunable `pred_shade ∈ [0,1]`: shrink each SELL line by
  `pred_shade · predicted_opp_units_5d / market_inv`. Let the optimiser choose
  how much to trust it — `pred_shade ≈ 0` is a valid, informative outcome.
- **D3 — ablation.** Same optimise config, `pred_shade` frozen at 0 vs free.
  If free doesn't beat frozen beyond noise, **cut the predictor from the
  submission** (~2 MB + feature code saved).

---

## 5. Lever E — Phase 3 policy net  *(parked; de-risk only)*

Do **not** start unless A+B+C plateau below a ladder win vs animal_factory.

- **E1 — finish the clone.** Implement the 4 `NotImplementedError` methods in
  `ml/clone/engine_np.py`. Gate: `validate_clone.py --replay` reproduces 20
  ladder replays' money trajectory to < 1 %.
- **E2 — only then:** BC-warm-start the hybrid-action net
  (`ml/rl/hybrid_action.py`) from the best evolved-engine traces, PFSP
  self-play league, NumPy-only `.npz` export. Weeks of work for uncertain gain
  over a well-tuned A1 engine.

---

## 6. Rule compliance (unchanged — restate for the record)

Offline training only. **NumPy-only inference**, **stdlib-only** exported
`main.py` (A1 export = forked v7 source + a config dict). Top-level
`try/except` → scripted fallback. ≤ 100 MiB submission, ~4 ms/step both seats,
≤ 10 market orders/turn. Predictor ships as the dep-free JSON tree-walk.

---

## 7. Sequencing

| # | Lever | Exit criterion |
|---|---|---|
| 1 | C6 | full `--gate` v7 baseline recorded, no OOM |
| 2 | A1 | `ml/engine_v7.py` + knobs; `evaluate(default)` ≈ v7 (±1 game, diff ≤ 0, 0 err, ≤ 4 ms) |
| 3 | B1–B4 | new `gate`/`ladder_econ` groups; `fitness` = promote rule; held-out reporting wired |
| 4 | C1–C2 | warm-started multi-fidelity run, ~40 gens vs `ladder_econ` |
| 5 | **promote** | `best.json`: `test.py --gate` ≥ v7 mean & p10, ≥ 45 % vs both animal bots, 0 err / 0 unsold, ≤ 4 ms → submit → **ladder read** |
| 6 | D1–D3 | predictor retrained on 150+ replays; ablation decides in/out |
| 7 | C3–C5 | surrogate + islands, only if step 4 is CPU-bound |
| 8 | E1 | clone validated < 1 %, only if steps 1–6 give no ladder win |

Each promoted `best.json` is copied to `main.py`, submitted, and **read on the
ladder before the next search** — same discipline as `experiments/LEDGER.md`.

---

## 8. Risks

1. **Overfitting the local gate = the 477 wall again.** Evolution overfits a
   fixed opponent set harder than hand-tuning. Mitigation: B2 hard constraints
   mirror the real promote rule; B3 held-out set; mandatory ladder read after
   every promote.
2. **A1 knob extraction drifts behaviour** so `default_params()` ≠ v7.
   Mitigation: step-2 exit is a paired equivalence check, not a vibe.
3. **Search cost:** ~40 gens × 16 pop × 12 games × 6 opp ≈ 46k games.
   Mitigation: C2 multi-fidelity, `--resume` exists, cap wall-clock, take
   best-so-far.
4. **Predictor corpus stays self-play-heavy** if the ladder isn't feeding new
   episodes. Mitigation: keep it advisory (D2 knob); gate nothing on it.

---

## 9. Effort / EV

| Lever | Effort | EV | Verdict |
|---|---|---|---|
| A1 re-base on v7 | M (~1 session) | High — unblocks everything | **first** |
| B fitness/gate rewrite | S | High — stops wasted search | **with A1** |
| C1–C2 warm-start + multi-fidelity | S | Med-High | yes |
| C6 eval OOM fix | S | Med (unblocks baseline) | yes, step 1 |
| D1–D3 predictor grow/wire/ablate | M | Low-Med | after a promote |
| C3–C5 surrogate / islands / diag-CMA | M | Med (only if CPU-bound) | conditional |
| E policy net | XL | Uncertain | only if A+B+C plateau |

**Bottom line:** the pipeline's problem is not the optimiser — it's that the
optimiser is pointed at the wrong engine and scored by the wrong gate. Fix
those two (A1 + B) and it can, for the first time, produce something worth
submitting.
