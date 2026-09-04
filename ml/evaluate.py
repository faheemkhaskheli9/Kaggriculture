"""Paired, seat-alternating evaluation of an engine config against a league.

Mirrors ``test.py``'s methodology (shared map seed per seat-swap pair, W/T/L,
p10 coins) but the candidate is an in-process ``build_agent`` callable, so we can
time it and run hundreds of configs without disk I/O, in parallel.

Two engines:
  * ``--engine v7``    -> ``ml/engine_v7.py`` (faithful ``main.py`` fork; use this)
  * ``--engine legacy`` -> ``ml/engine.py``  (``_kagri_botlib`` fork; smoke only)

``fitness`` (PLAN_ML_IMPROVE.md B2) is the **promote rule**, not a weighting:
a config that loses to an animal opponent, ends with unsold stock, is slow, or
crashes is disqualified outright. Only survivors are ranked.

CLI:
    python -m ml.evaluate --engine v7 --default --league gate --games 12 --workers 12
    python -m ml.evaluate --engine v7 --params ml/artifacts/phase1/best.json --league ladder_econ
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import random
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

# Keep native numerical libraries from multiplying the requested Python worker
# count into hundreds of threads.  This must run before kaggle_environments (and
# its NumPy/OpenSpiel dependency tree) is imported in spawned Windows workers.
_native_threads = os.environ.get("ML_NATIVE_THREADS", "1")
for _thread_var in (
        "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_thread_var] = _native_threads

from kaggle_environments import make

from ml import league as _lg

# --- engine registry --------------------------------------------------------
from ml.engine import build_agent as _build_legacy
from ml.engine_v7 import build_agent_v7 as _build_v7
from ml.spec import default_params as _default_legacy
from ml.spec import params_to_config as _cfg_legacy
from ml.spec_v7 import default_params_v7 as _default_v7
from ml.spec_v7 import params_to_config_v7 as _cfg_v7

_ENGINES = {
    "legacy": (_build_legacy, _cfg_legacy, _default_legacy),
    "v7": (_build_v7, _cfg_v7, _default_v7),
}


def _p10(xs):
    if not xs:
        return 0.0
    s = sorted(xs)
    i = max(0, min(len(s) - 1, int(0.10 * len(s) + 0.9999) - 1))
    return s[i]


def _timed(fn):
    stats = {"t": 0.0, "n": 0}

    def wrapped(obs):
        t0 = time.perf_counter()
        try:
            return fn(obs)
        finally:
            stats["t"] += time.perf_counter() - t0
            stats["n"] += 1
    return wrapped, stats


def _unsold_from_final(final, seat) -> int:
    try:
        priv = final[seat].observation["private"] or {}
    except Exception:
        return 0
    n = 0
    for v in (priv.get("shed") or {}).values():
        try:
            n += max(0, int(v))
        except (TypeError, ValueError):
            pass
    for iv in priv.get("inventories") or []:
        for v in (iv or {}).values():
            try:
                n += max(0, int(v))
            except (TypeError, ValueError):
                pass
    return n


def _diagnostics(steps, seat: int) -> dict:
    """Cheap action/lifecycle diagnostics without materializing env.toJSON()."""
    moves = nonpass = market_overflow = 0
    actions = Counter()
    plant_deaths = animal_escapes = 0
    final_weeds = 0
    for i, pair in enumerate(steps):
        if seat >= len(pair):
            continue
        action = pair[seat].action or {}
        unit_actions = [action.get("farmer")] + list(action.get("hands") or [])
        for act in unit_actions:
            if not act:
                continue
            op = str(act[0])
            actions[op] += 1
            if op != "PASS":
                nonpass += 1
                moves += op in {"NORTH", "SOUTH", "EAST", "WEST"}
        market_overflow += max(0, len(action.get("market") or []) - 10)
        if i + 1 >= len(steps) or (i + 1) % 24:
            continue
        try:
            before = pair[0].observation.farms[seat].tiles
            after = steps[i + 1][0].observation.farms[seat].tiles
            for y, row in enumerate(before):
                for x, tile in enumerate(row):
                    if not isinstance(tile, dict):
                        continue
                    nxt = after[y][x]
                    if (tile.get("kind") == "PLANT" and
                            int(tile.get("consecutive_unwatered", 0)) >= 1 and
                            not tile.get("watered_today") and
                            isinstance(nxt, dict) and nxt.get("kind") == "WEED"):
                        plant_deaths += 1
                    if (tile.get("animal") and int(tile.get("consecutive_unfed", 0)) >= 1 and
                            not tile.get("fed_today") and
                            not (isinstance(nxt, dict) and nxt.get("animal"))):
                        animal_escapes += 1
        except Exception:
            pass
    try:
        tiles = steps[-1][0].observation.farms[seat].tiles
        final_weeds = sum(isinstance(t, dict) and t.get("kind") == "WEED"
                          for row in tiles for t in row)
    except Exception:
        pass
    return {"move_share": moves / nonpass if nonpass else 0.0,
            "plant_deaths": plant_deaths, "animal_escapes": animal_escapes,
            "market_order_overflow": market_overflow, "final_weeds": final_weeds,
            "actions": dict(actions)}


def play_one(params: dict, opponent: str, seat: int, seed: int | None,
             engine: str = "v7") -> dict:
    """One game. ``seat`` is the candidate's seat (0/1). Returns a result row."""
    build, to_cfg, _ = _ENGINES[engine]
    cand_raw = build(to_cfg(params))
    cand, tstats = _timed(cand_raw)
    opp = _lg.resolve(opponent)
    agents = [cand, opp] if seat == 0 else [opp, cand]
    cfg = {"episodeSteps": 720}
    if seed is not None and seed >= 0:
        cfg["seed"] = seed
    unsold = 0
    diag = {}
    try:
        env = make("kaggriculture", configuration=cfg, debug=False)
        env.run(agents)
        final = env.steps[-1]
        statuses = [str(s.status) for s in final]
        money = []
        for i, s in enumerate(final):
            try:
                money.append(float(s.observation.farms[i].money))
            except Exception:
                money.append(float(s.reward or 0))
        cm, om = money[seat], money[1 - seat]
        err = any(st != "DONE" for st in statuses)
        unsold = _unsold_from_final(final, seat)
        diag = _diagnostics(env.steps, seat)
    except Exception as exc:  # env blew up -> treat as a loss + error
        cm, om, err = 0.0, 1.0, True
        statuses = [f"EXC:{type(exc).__name__}"]
    ms = 1000.0 * tstats["t"] / max(1, tstats["n"])
    return {
        "opponent": opponent, "seat": seat, "seed": seed,
        "cand_money": cm, "opp_money": om, "diff": cm - om,
        "result": 1 if cm > om else (-1 if cm < om else 0),
        "error": err, "statuses": statuses, "ms_step": ms,
        "terminal_unsold": unsold,
        **diag,
    }


def _job(a):
    return play_one(*a)


def _reduce(rows: list[dict], opponents: list[str], baseline_p10: float = 0.0) -> dict:
    per = {}
    for opp in opponents:
        r = [x for x in rows if x["opponent"] == opp]
        w = sum(x["result"] > 0 for x in r)
        t = sum(x["result"] == 0 for x in r)
        coins = [x["cand_money"] for x in r]
        per[opp] = {
            "games": len(r), "w": w, "t": t, "l": len(r) - w - t,
            "score_rate": (w + 0.5 * t) / len(r) if r else 0.0,
            "mean_coins": statistics.fmean(coins) if coins else 0.0,
            "p10_coins": _p10(coins),
            "mean_diff": statistics.fmean([x["diff"] for x in r]) if r else 0.0,
            "errors": sum(x["error"] for x in r),
            "move_share": statistics.fmean([x.get("move_share", 0) for x in r]) if r else 0.0,
            "plant_deaths": sum(x.get("plant_deaths", 0) for x in r),
            "animal_escapes": sum(x.get("animal_escapes", 0) for x in r),
            "final_weeds": statistics.fmean([x.get("final_weeds", 0) for x in r]) if r else 0.0,
        }
    srates = [per[o]["score_rate"] for o in opponents]
    rep = {
        "per_opponent": per,
        "mean_score_rate": statistics.fmean(srates) if srates else 0.0,
        "worst_score_rate": min(srates) if srates else 0.0,
        "mean_coins": statistics.fmean([x["cand_money"] for x in rows]) if rows else 0.0,
        "p10_coins": _p10([x["cand_money"] for x in rows]),
        "errors": sum(x["error"] for x in rows),
        "ms_step": statistics.fmean([x["ms_step"] for x in rows]) if rows else 0.0,
        "terminal_unsold": statistics.fmean([x["terminal_unsold"] for x in rows]) if rows else 0.0,
        "games": len(rows),
        "baseline_p10": baseline_p10,
        "move_share": statistics.fmean([x.get("move_share", 0) for x in rows]) if rows else 0.0,
        "plant_deaths": sum(x.get("plant_deaths", 0) for x in rows),
        "animal_escapes": sum(x.get("animal_escapes", 0) for x in rows),
        "market_order_overflow": sum(x.get("market_order_overflow", 0) for x in rows),
        "final_weeds": statistics.fmean([x.get("final_weeds", 0) for x in rows]) if rows else 0.0,
    }
    rep["fitness"] = fitness(rep)
    return rep


def evaluate_many(params_list: list[dict], opponents: list[str], games: int = 8,
                  seed_base: int = 10_000_000, workers: int = 1,
                  engine: str = "v7", baseline_p10: float = 0.0) -> list[dict]:
    """Evaluate a whole population in one flat process pool (best CPU use)."""
    jobs, owner = [], []
    for pi, params in enumerate(params_list):
        for oi, opp in enumerate(opponents):
            for g in range(games):
                seat = g % 2
                seed = -1 if seed_base < 0 else seed_base + g // 2
                jobs.append((params, opp, seat, seed, engine))
                owner.append(pi)
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            results = list(ex.map(_job, jobs, chunksize=1))
    else:
        results = [_job(a) for a in jobs]
    buckets = [[] for _ in params_list]
    for pi, row in zip(owner, results):
        buckets[pi].append(row)
    return [_reduce(rows, opponents, baseline_p10) for rows in buckets]


def evaluate(params: dict, opponents: list[str], games: int = 8,
             seed_base: int = 10_000_000, workers: int = 1,
             engine: str = "v7", baseline_p10: float = 0.0) -> dict:
    jobs = []
    for opp in opponents:
        for g in range(games):
            seat = g % 2
            seed = -1 if seed_base < 0 else seed_base + g // 2
            jobs.append((params, opp, seat, seed, engine))
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            rows = list(ex.map(_job, jobs))
    else:
        rows = [_job(a) for a in jobs]
    return _reduce(rows, opponents, baseline_p10)


def _score(row: dict) -> float:
    return 1.0 if row["result"] > 0 else (0.5 if row["result"] == 0 else 0.0)


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(q * (len(ordered) - 1))))
    return ordered[index]


def _paired_summary(challenger_rows: list[dict], incumbent_rows: list[dict],
                    bootstrap_samples: int = 10_000, bootstrap_seed: int = 0) -> dict:
    """Compare policies on identical opponent/seat/map-seed jobs.

    The percentile interval is over paired jobs, so map and seat variation is
    shared instead of being counted as independent noise.
    """
    key = lambda row: (row["opponent"], row["seat"], row["seed"])
    incumbent = {key(row): row for row in incumbent_rows}
    pairs = [(row, incumbent[key(row)]) for row in challenger_rows if key(row) in incumbent]
    score_deltas = [_score(c) - _score(i) for c, i in pairs]
    margin_deltas = [c["diff"] - i["diff"] for c, i in pairs]
    rng = random.Random(bootstrap_seed)
    boot = []
    if score_deltas:
        n = len(score_deltas)
        for _ in range(max(1, bootstrap_samples)):
            boot.append(statistics.fmean(score_deltas[rng.randrange(n)] for _ in range(n)))
    per_opponent = {}
    for opponent in sorted({c["opponent"] for c, _ in pairs}):
        selected = [(c, i) for c, i in pairs if c["opponent"] == opponent]
        deltas = [_score(c) - _score(i) for c, i in selected]
        per_opponent[opponent] = {
            "pairs": len(selected),
            "score_delta": statistics.fmean(deltas) if deltas else 0.0,
            "margin_delta": statistics.fmean(
                [c["diff"] - i["diff"] for c, i in selected]) if selected else 0.0,
        }
    return {
        "pairs": len(pairs),
        "score_delta": statistics.fmean(score_deltas) if score_deltas else 0.0,
        "score_delta_ci95": [_percentile(boot, 0.025), _percentile(boot, 0.975)],
        "score_delta_lcb95": _percentile(boot, 0.05),
        "margin_delta": statistics.fmean(margin_deltas) if margin_deltas else 0.0,
        "per_opponent": per_opponent,
    }


def evaluate_paired(challenger: dict, incumbent: dict, opponents: list[str],
                    games: int = 8, seed_base: int = 10_000_000,
                    workers: int = 1, engine: str = "v7",
                    bootstrap_samples: int = 10_000) -> dict:
    """Evaluate challenger and incumbent using common opponents, seats, and seeds."""
    jobs = []
    for params in (challenger, incumbent):
        for opponent in opponents:
            for game in range(games):
                jobs.append((params, opponent, game % 2,
                             -1 if seed_base < 0 else seed_base + game // 2, engine))
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            rows = list(ex.map(_job, jobs, chunksize=1))
    else:
        rows = [_job(job) for job in jobs]
    split = len(rows) // 2
    challenger_rows, incumbent_rows = rows[:split], rows[split:]
    report = _reduce(challenger_rows, opponents)
    report["incumbent"] = _reduce(incumbent_rows, opponents)
    report["paired"] = _paired_summary(
        challenger_rows, incumbent_rows, bootstrap_samples, seed_base)
    return report


# opponents a promotable config MUST hold >= 45% against (PLAN_LADDER_ECON s4)
def _hard_opponents(per_opponent: dict) -> list[str]:
    return [o for o in per_opponent if "animal" in o]


def fitness(report: dict) -> float:
    """Higher is better; optimisers minimise ``-fitness``.

    This is the promote rule (PLAN_ML_IMPROVE.md B2): any config that
      * crashes, or
      * scores < 0.45 vs any animal opponent, or
      * ends with mean terminal unsold > 3, or
      * runs slower than 4 ms/step, or
      * has p10 coins below the baseline (when one is supplied)
    is disqualified (fitness in [-2, -1)). Survivors are ranked by
    ``0.5*worst_sr + 0.3*mean_sr + 0.2*coin_bonus``.
    """
    per = report.get("per_opponent", {})
    hard = _hard_opponents(per)
    worst_hard = min((per[o]["score_rate"] for o in hard), default=1.0)
    base_p10 = report.get("baseline_p10", 0.0) or 0.0

    # ---- disqualifiers: return a *ranked* penalty so CMA-ES still has a gradient
    if report["errors"]:
        return -2.0 + 0.1 * report["mean_score_rate"]
    dq = 0.0
    # Keep optimiser selection aligned with the supervisor's safety gate. A
    # profitable policy that silently loses crops/animals or overflows market
    # orders is a diagnostic lead, not a promotable winner.
    if report.get("plant_deaths", 0):
        dq += 0.01 * min(25.0, float(report["plant_deaths"]))
    if report.get("animal_escapes", 0):
        dq += 0.005 * min(50.0, float(report["animal_escapes"]))
    if report.get("market_order_overflow", 0):
        dq += 0.05 * min(10.0, float(report["market_order_overflow"]))
    if worst_hard < 0.45:
        dq += (0.45 - worst_hard)
    if report["terminal_unsold"] > 3.0:
        dq += 0.02 * min(50.0, report["terminal_unsold"] - 3.0)
    if report["ms_step"] > 4.0:
        dq += 0.05 * min(20.0, report["ms_step"] - 4.0)
    if base_p10 and report["p10_coins"] < base_p10:
        dq += min(0.5, (base_p10 - report["p10_coins"]) / max(1.0, base_p10))
    if dq > 0.0:
        return -1.0 - dq

    # ---- survivors ----
    coin_bonus = max(0.0, min(1.0, report["mean_coins"] / 80_000.0))
    return (0.5 * report["worst_score_rate"]
            + 0.3 * report["mean_score_rate"]
            + 0.2 * coin_bonus)


def _fmt(report: dict) -> str:
    dq = "" if report["fitness"] >= -0.999 else "  [DISQUALIFIED]"
    lines = [
        f"fitness={report['fitness']:+.4f}{dq}  mean_sr={report['mean_score_rate']:.3f}"
        f"  worst_sr={report['worst_score_rate']:.3f}"
        f"  mean_coins={report['mean_coins']:.0f}  p10={report['p10_coins']:.0f}"
        f"  unsold={report['terminal_unsold']:.1f}"
        f"  move={report['move_share']:.0%} deaths={report['plant_deaths']}"
        f" escapes={report['animal_escapes']} weeds={report['final_weeds']:.1f}"
        f"  err={report['errors']}  ms/step={report['ms_step']:.2f}"
    ]
    for o, d in report["per_opponent"].items():
        tag = "  <hard" if "animal" in o else ""
        lines.append(
            f"  {o:16} W/T/L={d['w']}/{d['t']}/{d['l']}  sr={d['score_rate']:.2f}"
            f"  coins {d['mean_coins']:.0f}/p10 {d['p10_coins']:.0f}"
            f"  diff={d['mean_diff']:+.0f}  err={d['errors']}{tag}"
        )
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="v7", choices=list(_ENGINES))
    ap.add_argument("--params", help="JSON file of params (flat dict)")
    ap.add_argument("--default", action="store_true", help="use spec defaults")
    ap.add_argument("--league", default="gate")
    ap.add_argument("--games", type=int, default=12)
    ap.add_argument("--seed", type=int, default=10_000_000)
    ap.add_argument("--workers", type=int, default=1,
                    help="processes used for games; 2-4 is the safe starting range on Windows")
    ap.add_argument("--baseline-p10", type=float, default=0.0)
    ap.add_argument("--incumbent-params",
                    help="compare against this params JSON on identical jobs; 'default' uses spec defaults")
    ap.add_argument("--bootstrap-samples", type=int, default=10_000)
    ap.add_argument("--json-out", help="also write the complete report as JSON")
    args = ap.parse_args()

    _, _, dflt = _ENGINES[args.engine]
    if args.default or not args.params:
        params = dflt()
    else:
        params = {**dflt(), **json.load(open(args.params))}
    opponents = _lg.expand(args.league)
    print(f"engine={args.engine} league={opponents} games/opp={args.games} workers={args.workers}")
    if args.incumbent_params:
        incumbent = dflt()
        if args.incumbent_params != "default":
            with open(args.incumbent_params, encoding="utf-8") as fh:
                incumbent.update(json.load(fh))
        rep = evaluate_paired(params, incumbent, opponents, args.games, args.seed,
                              args.workers, args.engine, args.bootstrap_samples)
    else:
        rep = evaluate(params, opponents, args.games, args.seed, args.workers,
                       engine=args.engine, baseline_p10=args.baseline_p10)
    print(_fmt(rep))
    if "paired" in rep:
        paired = rep["paired"]
        print(f"paired score delta={paired['score_delta']:+.3f} "
              f"one-sided LCB95={paired['score_delta_lcb95']:+.3f} "
              f"margin delta={paired['margin_delta']:+.0f} pairs={paired['pairs']}")
    if args.json_out:
        from pathlib import Path
        target = Path(args.json_out)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(json.dumps(rep, indent=2), encoding="utf-8")
        temporary.replace(target)


if __name__ == "__main__":
    main()
