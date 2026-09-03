# `ml/` — the PLAN_ML_MODELS pipeline

Implements [PLAN_ML_MODELS.md](../PLAN_ML_MODELS.md). Runnable today: **Phase 0**
(runtime probe), **Phase 1** (cheap knob search), **Phase 2** (CMA-ES over the
full engine config), and the **opponent-production predictor**. **Phase 3**
(learned policy) and the **vectorised engine clone** are scaffolds with a build
order.

Everything trains offline on this machine; only a tiny config (or, later, a
`.npz`) ships. No new runtime deps — `ml/engine.py` and the exported `main.py`
are stdlib-only.

```
ml/
  engine_v7.py       PRIMARY: faithful parameterised fork of main.py v7 (PLAN_ML_IMPROVE A1)
  spec_v7.py         search space for engine_v7 — 65 knobs, defaults == v7 exactly
  engine.py          legacy: fork of bots/_kagri_botlib.py (loses to main.py; smoke only)
  spec.py            legacy search space for engine.py
  league.py          opponent groups (floor / gate / ladder_econ / heldout / lineage / all)
  evaluate.py        paired eval -> per-opponent metrics + fitness (= the promote rule)
  optimize.py        CMA-ES / random driver; --engine {v7,legacy}, --heldout, --rotate-seed
  export_main.py     bundle an engine + a tuned config -> a single submission main.py
  run_phase0_probe.py  generate + parse the runtime-probe submission
  optim/             cmaes.py (pure numpy), random_search.py
  predictor/         features.py, build_dataset.py, train.py (lightgbm), infer.py (dep-free)
  clone/             engine_np.py + validate_clone.py   [scaffold — see clone/README.md]
  rl/                hybrid_action.py + README            [scaffold — see rl/README.md]
  artifacts/         all run outputs land here
```

## v7 engine (PLAN_ML_IMPROVE.md — the current path)

`ml/engine_v7.py` is a faithful, knob-for-knob fork of `main.py` v7 — verified
byte-identical (0 action mismatches / 719 steps / 3 seeds). Optimise **this**,
not `ml/engine.py`.

```bash
# 0. confirm the fork still == main.py, and read v7's bar vs the gate
python -m ml.evaluate --engine v7 --default --league gate --games 8 --workers 12
#    note mean_coins / p10 -> pass p10 as --baseline-p10 below

# 1. Phase 1 — the 16 L1-L5 economy knobs, vs the animal-heavy gate
python -m ml.optimize --engine v7 --knobs phase1 --league gate \
  --games 10 --generations 25 --workers 14 --rotate-seed \
  --baseline-p10 <v7 p10> --out ml/artifacts/v7_phase1

# 2. Phase 2 — all 65 knobs (hours; resumable)
python -m ml.optimize --engine v7 --knobs phase2 --league ladder_econ \
  --games 8 --generations 60 --popsize 18 --workers 16 --rotate-seed \
  --baseline-p10 <v7 p10> --out ml/artifacts/v7_phase2 --resume

# 3. promote
python -m ml.export_main --engine v7 ml/artifacts/v7_phase2/best.json -o main_ml.py
python test.py --gate --games 40 --candidate main_ml.py --incumbent main.py
#    gate: OVERALL mean & p10 >= v7, score-rate >= 45% vs BOTH animal opponents,
#          0 err, 0 terminal-unsold, <= 4 ms/step, both seats. Then submit + ladder read.
```

`history.csv` carries `heldout_fitness` / `heldout_sr` (scored on `heldout`,
never optimised): if train fitness climbs while held-out stalls, stop and take
the last checkpoint where both moved — that's the 477-wall overfit signal.

## Run order

### Phase 0 — what does the Kaggle runner have? (~10 min + one submission)
```bash
python -m ml.run_phase0_probe
kaggle competitions submit kaggriculture -f ml/artifacts/probe/main.py -m "env probe"
# once it has a validation episode:
kaggle competitions episodes <SUBMISSION_ID> -v
kaggle competitions logs <EPISODE_ID> 0 -p ml/artifacts/probe/logs
python -m ml.run_phase0_probe --parse ml/artifacts/probe/logs/<file>.json
```
Write the available-libs list into `PLAN_ML_MODELS.md` §2. Governs whether Phase 3
inference can use anything beyond numpy.

### Sanity — the forked engine still plays
```bash
python -m ml.evaluate --default --league gate --games 8 --workers 10
```
Expect it in the same ballpark as `main.py` v5 (it is the `_kagri_botlib`
lineage, not a v5 fork — see caveat below).

### Phase 1 — cheap knob search (~30–90 min)
```bash
python -m ml.optimize --knobs phase1 --optimizer cmaes --league gate \
  --games 10 --generations 25 --workers 14 --out ml/artifacts/phase1
# also run a random-search baseline to check CMA-ES is earning its keep:
python -m ml.optimize --knobs phase1 --optimizer random --league gate \
  --games 10 --generations 12 --workers 14 --out ml/artifacts/phase1_rand
```

### Phase 2 — full engine config (hours; resumable)
```bash
python -m ml.optimize --knobs phase2 --optimizer cmaes --league floor \
  --games 8 --generations 60 --popsize 16 --workers 16 \
  --out ml/artifacts/phase2 --resume
```

### Promote (never skip)
```bash
python -m ml.export_main ml/artifacts/phase2/best.json -o main_ml.py
python test.py --games 40 --candidate main_ml.py --incumbent main.py
python test.py --games 30 --suite --candidate main_ml.py
# gate: higher paired mean AND non-worse p10 AND 0 errors AND 0 terminal-unsold
#       AND <=4 ms/step, BOTH seats. Then:
kaggle competitions submit kaggriculture -f main_ml.py -m "ml phase2 cfg"
# add the row (report.md has a template) to experiments/LEDGER.md after a ladder read.
```

### Opponent-production predictor (Phase 1C)
```bash
python -m ml.predictor.build_dataset --replays replays
python -m ml.predictor.train                 # writes ml/artifacts/opppred.json (dep-free)
python -m ml.predictor.infer                  # self-test the pure-python walk
```
Then wire `Predictor.load(...).predict(opp_farm, market, town, day, dmoney)` into
`main.py`'s sell sizing (shade sells away from products the opponent is about to
flood). Copy `predictor/features.py` + `predictor/infer.py` + `opppred.json` into
the submission tar.gz. **The replay corpus is small and half self-play** — check
`train.py`'s "MAE lift over baseline"; if it's weak, keep the predictor advisory
and pull more ladder replays first.

## Caveat — the pipeline league is not the ladder

`experiments/LEDGER.md` and the strategy playbook both record local dominance
coexisting with a 477 ladder score. `ml/evaluate.py`'s `fitness` deliberately
weights **worst-opponent score-rate** and p10, not mean coins, to fight this —
but the only real gate is a Kaggle submission. Treat every `best.json` as a
*hypothesis*, run it through `test.py` vs `main.py`, submit, and read the ladder
before touching `experiments/LEDGER.md` or `main.py`.

`ml/engine.py` is forked from `bots/_kagri_botlib.py` (a competent zoned
multi-unit engine), **not** from `main.py` v5. Measured starting gap: with
default knobs it beats the `bots/` archetypes but **loses ~28–36k coins / 0–4 to
`main.py` v5** (`python -m ml.evaluate --default --league gate`). So:

- **Always optimise against `--league gate`** (it contains `main.py` + `v5`), not
  just `floor` — that's the only way `fitness` pushes toward closing the gap.
- If Phase 2 closes it: `export_main` → `test.py` → submit.
- If it doesn't: port only the winning *sub-decision* (price-aware sell sizing,
  per-quadrant land days, hire curve) into `main.py` by hand.
- **Phase 2b (bigger, optional):** re-fork `ml/engine.py` from `main.py` itself
  (836 lines, the v5 zoned core) so the search starts from the strong baseline.
  That's the "v5-fork engine lib" the memory / `PLAN_CONTENDERS` calls for; do it
  if the sub-decision harvest proves too limited.
