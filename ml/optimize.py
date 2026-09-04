"""Black-box optimiser driver for the engine config (PLAN_ML_MODELS phases 1-2).

Phase 1 (cheap, ~14 knobs, the M1/M4 levers):
    python -m ml.optimize --knobs phase1 --league gate --games 10 \
        --optimizer cmaes --generations 25 --workers 12 --out ml/artifacts/phase1

Phase 2 (full ~55 knobs):
    python -m ml.optimize --knobs phase2 --league floor --games 8 \
        --optimizer cmaes --generations 60 --popsize 16 --workers 16 \
        --out ml/artifacts/phase2 --resume

Outputs in ``--out``:
    gen_XXXX.json     per-generation checkpoint (optimiser state + pop + reports)
    best.json         best params found (flat dict, ready for ml/evaluate/export)
    report.md         human summary + a paste-ready experiments/LEDGER.md row
    history.csv       one row per generation (fitness / score-rate / coins)
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
from pathlib import Path

# On Windows every ProcessPoolExecutor worker imports this module again.  NumPy's
# BLAS backend otherwise creates a full native thread pool in every worker; with
# a dozen evaluators that can exhaust memory before the first game starts.
# ML_NATIVE_THREADS remains available as an explicit escape hatch for profiling.
_native_threads = os.environ.get("ML_NATIVE_THREADS", "1")
for _thread_var in (
        "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_thread_var] = _native_threads

import numpy as np

from ml import league as _lg
from ml.evaluate import evaluate, evaluate_many, fitness
from ml.optim.cmaes import CMAES
from ml.optim.random_search import RandomSearch
from ml import spec as _spec_legacy
from ml import spec_v7 as _spec_v7


class _SpecView:
    """Adapts the two spec modules to one interface the driver uses."""

    def __init__(self, engine: str):
        if engine == "v7":
            self.PHASE1 = _spec_v7.PHASE1_V7
            self.ANIMAL = _spec_v7.ANIMAL_V7
            self.PHASE2 = _spec_v7.PHASE2_V7
            self.default_params = _spec_v7.default_params_v7
            self.params_to_config = _spec_v7.params_to_config_v7
            self.to_unit = _spec_v7.to_unit_v7
            self.from_unit = _spec_v7.from_unit_v7
            self.build_import = "from ml.engine_v7 import build_agent_v7 as build_agent"
        else:
            self.PHASE1 = _spec_legacy.PHASE1_NAMES
            self.PHASE2 = _spec_legacy.PHASE2_NAMES
            self.default_params = _spec_legacy.default_params
            self.params_to_config = _spec_legacy.params_to_config
            self.to_unit = _spec_legacy.to_unit
            self.from_unit = _spec_legacy.from_unit
            self.build_import = "from ml.engine import build_agent"

    def knob_names(self, spec: str) -> list[str]:
        if spec == "phase1":
            return list(self.PHASE1)
        if spec == "phase2":
            return list(self.PHASE2)
        if spec == "animal":
            if not hasattr(self, "ANIMAL"):
                raise ValueError("the focused animal search is available only for --engine v7")
            return list(self.ANIMAL)
        return [s.strip() for s in spec.split(",") if s.strip()]


def _atomic_json(path, data):
    """Never leave a half-written resume checkpoint after interruption."""
    target = Path(path)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(target)


def _write_report(out, names, best_params, best_report, args, elapsed, sv):
    md = [
        f"# {os.path.basename(out)} — engine-config optimisation",
        "",
        f"- optimiser: **{args.optimizer}**  generations: {args.generations}  "
        f"popsize: {args.popsize or 'auto'}",
        f"- league: `{args.league}` = {_lg.expand(args.league)}  games/opp: {args.games}",
        f"- knobs ({len(names)}): {', '.join(names)}",
        f"- wall time: {elapsed/60:.1f} min",
        "",
        "## Best config — evaluation",
        "",
        "```",
        f"fitness      {best_report['fitness']:+.4f}",
        f"mean_sr      {best_report['mean_score_rate']:.3f}",
        f"worst_sr     {best_report['worst_score_rate']:.3f}",
        f"mean_coins   {best_report['mean_coins']:.0f}",
        f"p10_coins    {best_report['p10_coins']:.0f}",
        f"errors       {best_report['errors']}",
        f"ms/step      {best_report['ms_step']:.2f}",
        "```",
        "",
        "| opponent | W/T/L | score | mean coins | p10 | diff |",
        "|---|---|---|---|---|---|",
    ]
    for o, d in best_report["per_opponent"].items():
        md.append(f"| {o} | {d['w']}/{d['t']}/{d['l']} | {d['score_rate']:.2f} "
                  f"| {d['mean_coins']:.0f} | {d['p10_coins']:.0f} | {d['mean_diff']:+.0f} |")
    md += [
        "",
        "## Changed params vs default",
        "",
        "```",
    ]
    dflt = sv.default_params()
    for k in names:
        if abs(float(best_params[k]) - float(dflt[k])) > 1e-6:
            md.append(f"{k:24} {dflt[k]!s:>10}  ->  {best_params[k]!s}")
    md += [
        "```",
        "",
        "## Paste into experiments/LEDGER.md after a `test.py` + ladder read",
        "",
        f"| vN | {time.strftime('%Y-%m-%d')} | vX | ML {os.path.basename(out)} "
        f"({args.optimizer}, {len(names)} knobs, league {args.league}) "
        f"| {best_report['mean_coins']:.0f} / {best_report['p10_coins']:.0f} "
        f"| ? vs main.py | {best_report['errors']} / ? / {best_report['ms_step']:.1f} "
        f"| — | ? | pending |",
        "",
        "> The pipeline league is NOT the ladder. Before promoting: "
        "`python test.py --games 40 --candidate <snapshot> --incumbent main.py`, "
        "confirm 0 errors / 0 terminal-unsold / <=4 ms, then submit for a real read.",
    ]
    with open(os.path.join(out, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))


def _snapshot(out, params, sv):
    """A self-contained runnable agent file (for test.py / compete.py)."""
    path = os.path.join(out, "snapshot_agent.py")
    cfg = sv.params_to_config(params)
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            "\"\"\"Auto-generated by ml/optimize.py. Runnable by test.py/compete.py.\n"
            "For a Kaggle submission run `python -m ml.export_main <this dir>/best.json`.\n\"\"\"\n"
            "import os, sys\n"
            f"sys.path.insert(0, {os.path.dirname(os.path.dirname(os.path.abspath(__file__)))!r})\n"
            f"{sv.build_import}\n"
            f"CONFIG = {cfg!r}\n"
            "agent = build_agent(CONFIG)\n"
        )
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="v7", choices=["v7", "legacy"],
                    help="v7 = faithful main.py fork (default); legacy = _kagri_botlib fork")
    ap.add_argument("--knobs", default="phase1", help="phase1 | animal | phase2 | a,b,c")
    ap.add_argument("--optimizer", default="cmaes", choices=["cmaes", "random"])
    ap.add_argument("--league", default="gate")
    ap.add_argument("--heldout", default="heldout",
                    help="league scored (not optimised) each gen to catch overfit; '' to skip")
    ap.add_argument("--games", type=int, default=10)
    ap.add_argument("--screen-games", type=int, default=0,
                    help="cheap first-stage games per screen opponent; 0 disables successive halving")
    ap.add_argument("--screen-league", default="quick")
    ap.add_argument("--screen-top-fraction", type=float, default=0.34)
    ap.add_argument("--generations", type=int, default=25)
    ap.add_argument("--popsize", type=int, default=0)
    ap.add_argument("--sigma0", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--eval-seed", type=int, default=10_000_000)
    ap.add_argument("--baseline-p10", type=float, default=0.0,
                    help="disqualify configs with p10 coins below this "
                         "(run `ml.evaluate --engine v7 --default --league <L>` to get v7's)")
    ap.add_argument("--rotate-seed", action="store_true",
                    help="B4: use a fresh map-seed block each generation")
    ap.add_argument("--workers", type=int, default=min(4, max(1, (os.cpu_count() or 2) - 1)),
                    help="processes used for official-environment games; start at 2-4 on Windows")
    ap.add_argument("--out", default="ml/artifacts/run")
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    sv = _SpecView(args.engine)
    os.makedirs(args.out, exist_ok=True)
    names = sv.knob_names(args.knobs)
    dim = len(names)
    opponents = _lg.expand(args.league)
    heldout = _lg.expand(args.heldout) if args.heldout else []
    base = sv.default_params()
    x0 = np.array(sv.to_unit(base, names))
    popsize = args.popsize or None

    if args.optimizer == "cmaes":
        opt = CMAES(dim, x0=x0, sigma0=args.sigma0, popsize=popsize,
                    seed=args.seed, maxiter=args.generations)
    else:
        opt = RandomSearch(dim, popsize=popsize or 16, seed=args.seed,
                           maxiter=args.generations)

    hist_path = os.path.join(args.out, "history.csv")
    start_gen = 0
    ckpts = sorted(f for f in os.listdir(args.out) if f.startswith("gen_"))
    if args.resume and ckpts:
        st = json.load(open(os.path.join(args.out, ckpts[-1])))
        saved_names = st.get("knob_names")
        if saved_names and saved_names != names:
            raise SystemExit(
                f"cannot resume {ckpts[-1]}: checkpoint has {len(saved_names)} knobs "
                f"but this run selected {len(names)}. Use a new --out directory or "
                "restore the original --knobs selection."
            )
        opt.load(st["optimizer"])
        start_gen = st["generation"] + 1
        print(f"resumed from {ckpts[-1]} at generation {start_gen}")
    else:
        with open(hist_path, "w", newline="") as f:
            csv.writer(f).writerow(
                ["generation", "best_fitness", "gen_best_fitness",
                 "mean_score_rate", "worst_score_rate", "mean_coins", "p10_coins",
                 "errors", "ms_step", "heldout_fitness", "heldout_sr", "seconds"])

    print(f"engine={args.engine}  knobs({dim})={names}")
    print(f"optimise league={opponents}  heldout={heldout or '-'}  "
          f"baseline_p10={args.baseline_p10:.0f}")

    t_start = time.time()
    for gen in range(start_gen, args.generations):
        t0 = time.time()
        eseed = (args.eval_seed + gen * 101) if args.rotate_seed else args.eval_seed
        genes = opt.ask()
        pop = [sv.from_unit(g, names, base) for g in genes]
        if args.screen_games > 0 and len(pop) > 1:
            screen_opponents = _lg.expand(args.screen_league)
            screened = evaluate_many(pop, screen_opponents, args.screen_games, eseed,
                                     args.workers, engine=args.engine,
                                     baseline_p10=args.baseline_p10)
            keep = max(1, min(len(pop), int(np.ceil(
                len(pop) * max(0.0, min(1.0, args.screen_top_fraction))))))
            promoted = sorted(range(len(pop)),
                              key=lambda i: screened[i]["fitness"], reverse=True)[:keep]
            full = evaluate_many([pop[i] for i in promoted], opponents, args.games,
                                 eseed, args.workers, engine=args.engine,
                                 baseline_p10=args.baseline_p10)
            reports = list(screened)
            for index, report in zip(promoted, full):
                reports[index] = report
            promoted_set = set(promoted)
            worst_full_loss = max(-report["fitness"] for report in full)
            screen_rank = {index: rank for rank, index in enumerate(
                sorted(range(len(pop)), key=lambda i: screened[i]["fitness"], reverse=True))}
            fs = [(-reports[i]["fitness"] if i in promoted_set else
                   worst_full_loss + 1.0 + screen_rank[i] / max(1, len(pop)))
                  for i in range(len(pop))]
        else:
            reports = evaluate_many(pop, opponents, args.games, eseed, args.workers,
                                    engine=args.engine, baseline_p10=args.baseline_p10)
            fs = [-r["fitness"] for r in reports]
        opt.tell(genes, fs)
        gi = int(np.argmin(fs))
        gen_best = reports[gi]

        ho_fit = ho_sr = float("nan")
        if heldout:
            ho = evaluate(pop[gi], heldout, max(4, args.games // 2),
                          eseed + 7777, args.workers, engine=args.engine)
            ho_fit, ho_sr = ho["fitness"], ho["mean_score_rate"]
        dt = time.time() - t0

        with open(hist_path, "a", newline="") as f:
            csv.writer(f).writerow([
                gen, f"{-opt.best[1]:.5f}", f"{gen_best['fitness']:.5f}",
                f"{gen_best['mean_score_rate']:.4f}", f"{gen_best['worst_score_rate']:.4f}",
                f"{gen_best['mean_coins']:.0f}", f"{gen_best['p10_coins']:.0f}",
                gen_best["errors"], f"{gen_best['ms_step']:.2f}",
                f"{ho_fit:.5f}", f"{ho_sr:.4f}", f"{dt:.0f}"])

        best_params = sv.from_unit(opt.best[0], names, base)
        _atomic_json(os.path.join(args.out, f"gen_{gen:04d}.json"), {
            "generation": gen,
            "optimizer": opt.state(),
            "gen_best_params": pop[gi],
            "gen_best_report": gen_best,
            "best_params": best_params,
            "knob_names": names,
        })
        _atomic_json(os.path.join(args.out, "best.json"), best_params)

        ho_txt = f"  held_sr={ho_sr:.3f}" if heldout else ""
        print(f"gen {gen:3d}/{args.generations}  best_fit={-opt.best[1]:+.4f}  "
              f"gen_best={gen_best['fitness']:+.4f}  "
              f"mean_sr={gen_best['mean_score_rate']:.3f} worst_sr={gen_best['worst_score_rate']:.3f}  "
              f"coins={gen_best['mean_coins']:.0f}  err={gen_best['errors']}  "
              f"ms={gen_best['ms_step']:.2f}{ho_txt}  ({dt:.0f}s)")
        if opt.stop():
            break

    best_params = sv.from_unit(opt.best[0], names, base)
    print("final re-evaluation of best config on a fresh seed block ...")
    final = evaluate(best_params, opponents, max(args.games, 16),
                     args.eval_seed + 5000, args.workers,
                     engine=args.engine, baseline_p10=args.baseline_p10)
    _atomic_json(os.path.join(args.out, "best.json"), best_params)
    _snapshot(args.out, best_params, sv)
    _write_report(args.out, names, best_params, final, args, time.time() - t_start, sv)
    print(f"\nwrote {args.out}/best.json  snapshot_agent.py  report.md  history.csv")
    print(f"final: fitness={final['fitness']:+.4f} mean_sr={final['mean_score_rate']:.3f} "
          f"coins={final['mean_coins']:.0f} err={final['errors']} ms={final['ms_step']:.2f}")


if __name__ == "__main__":
    main()
