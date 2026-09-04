"""Statistically safer autonomous improvement loop for Kaggriculture.

Unlike auto_improve.py, every edit is tested immediately against the current
champion on identical, opponent-balanced games.  Rejected edits are restored
before another proposal is requested.  A separate validation schedule is never
included in the LLM prompt and is used to guard accepted candidates.

The original tools/auto_improve.py is intentionally untouched.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import random
import shutil
import statistics
import sys
import time
from pathlib import Path

import auto_improve as legacy

ROOT = legacy.ROOT
RUNS_ROOT = ROOT / "tools" / "auto_improve_v2_runs"


class SeatRng:
    """The only random value play_match requests is our seat."""

    def __init__(self, seat: int):
        self.seat = seat

    def randint(self, _low: int, _high: int) -> int:
        return self.seat


def import_compete():
    sys.path.insert(0, str(ROOT))
    import compete  # noqa: PLC0415
    return compete


def unique_pool(pool: list[str] | None, exclude_lineage: bool) -> list[str]:
    compete = import_compete()
    raw = list(pool) if pool else list(compete.DEFAULT_POOL)
    if not exclude_lineage:
        raw += list(compete.LINEAGE)
    resolved = compete.resolve_pool(raw)
    out = []
    seen = set()
    for item in resolved:
        key = Path(item).resolve().as_posix() if item.endswith(".py") else item
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def select_hard(pool: list[str], requested: list[str] | None) -> list[str]:
    needles = requested or ["c_v5clone", "main_p3", "c_animalfactory",
                            "main_v5", "main_v6", "main_v7"]
    selected = [p for p in pool if Path(p).stem in needles or p in needles]
    missing = sorted(set(needles) - {Path(p).stem for p in selected} - set(selected))
    if missing:
        print("warning: hard opponents absent from pool:", ", ".join(missing))
    return selected or pool


def make_schedule(pool: list[str], games: int, seed: int) -> list[dict]:
    """Round-robin opponents with balanced seats and stable shuffled seeds."""
    if games < 1 or not pool:
        raise ValueError("games and opponent pool must be non-empty")
    rng = random.Random(seed)
    order = list(pool)
    rng.shuffle(order)
    schedule = []
    appearances = {opponent: 0 for opponent in pool}
    for i in range(games):
        cycle, slot = divmod(i, len(order))
        if slot == 0 and cycle:
            rng.shuffle(order)
        opponent = order[slot]
        schedule.append({
            "opponent": opponent,
            "seed": rng.randint(100_000_000, 999_999_999),
            "seat": appearances[opponent] % 2,
        })
        appearances[opponent] += 1
    return schedule


def schedule_digest(schedule: list[dict]) -> str:
    blob = json.dumps(schedule, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def summarize(rows: list[dict], label: str) -> dict:
    wins = sum(r["result"] == "WIN" for r in rows)
    ties = sum(r["result"] == "TIE" for r in rows)
    margins = [r["margin"] for r in rows]
    by_opp = {}
    for r in rows:
        by_opp.setdefault(r["opponent"], []).append(r)
    per_opp = {}
    for opp, rs in sorted(by_opp.items()):
        per_opp[opp] = {
            "n": len(rs),
            "score": sum(x["result"] == "WIN" for x in rs) / len(rs)
                     + 0.5 * sum(x["result"] == "TIE" for x in rs) / len(rs),
            "margin_mean": statistics.fmean(x["margin"] for x in rs),
        }
    return {
        "label": label, "games": len(rows), "wins": wins, "ties": ties,
        "losses": len(rows) - wins - ties,
        "score": (wins + 0.5 * ties) / len(rows),
        "margin_mean": statistics.fmean(margins),
        "margin_median": statistics.median(margins),
        "errors": sum(r["errored"] for r in rows), "per_opp": per_opp,
    }


def evaluate(agent: Path, schedule: list[dict], out_dir: Path,
             label: str, store: bool = True) -> tuple[dict, list[dict]]:
    compete = import_compete()
    game_dir = out_dir / label
    rows = []
    for i, match in enumerate(schedule, 1):
        row = compete.play_match(
            str(agent.resolve()), match["opponent"], match["seed"],
            SeatRng(match["seat"]), save_dir=game_dir if store else None,
            game_number=i, debug=False,
        )
        rows.append(row)
    metrics = summarize(rows, label)
    game_dir.mkdir(parents=True, exist_ok=True)
    (game_dir / "manifest.json").write_text(json.dumps({
        "agent": str(agent), "schedule_digest": schedule_digest(schedule),
        "games": rows,
    }, indent=2), encoding="utf-8")
    (out_dir / f"{label}_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics, rows


def paired_stats(candidate: list[dict], champion: list[dict]) -> dict:
    if len(candidate) != len(champion):
        raise ValueError("paired result lengths differ")
    deltas = [a["margin"] - b["margin"] for a, b in zip(candidate, champion)]
    flips_up = sum(a["result"] == "WIN" and b["result"] != "WIN"
                   for a, b in zip(candidate, champion))
    flips_down = sum(a["result"] != "WIN" and b["result"] == "WIN"
                     for a, b in zip(candidate, champion))
    return {
        "margin_delta_mean": statistics.fmean(deltas),
        "margin_delta_median": statistics.median(deltas),
        "positive": sum(x > 0 for x in deltas), "negative": sum(x < 0 for x in deltas),
        "win_flips_up": flips_up, "win_flips_down": flips_down,
    }


def worst_opp_regression(cand: dict, champ: dict) -> tuple[float, str]:
    values = []
    for opp, old in champ["per_opp"].items():
        if opp in cand["per_opp"]:
            values.append((cand["per_opp"][opp]["score"] - old["score"], opp))
    return min(values, default=(0.0, "none"))


def prompt_for(iteration: int, champion: dict, analysis: str, losses: list[dict],
               ledger: Path, lessons: Path, diff: str) -> str:
    weak = sorted(champion["per_opp"].items(), key=lambda x: (x[1]["score"], x[1]["margin_mean"]))
    weak_text = "\n".join(
        f"- {name}: n={v['n']} score={v['score']:.1%} margin={v['margin_mean']:+.0f}"
        for name, v in weak[:8])
    loss_text = "\n".join(
        f"- {g['opponent']} seed={g['seed']} seat={g['our_seat']} margin={g['margin']:+.0f} "
        f"replay={g.get('replay', '?')}" for g in losses) or "(none)"
    return f"""You are improving main_auto.py for Kaggriculture, iteration {iteration}.

Edit ONLY main_auto.py and make one coherent, falsifiable change. The current
file is the accepted champion. Your edit will immediately face a balanced hard
suite, an identical paired development suite, and a hidden validation suite.
Rejected edits are reverted before the next iteration.

Research knowledge-base/INDEX.md, knowledge-base/04-engine-internals.md,
CLAUDE.md, experiments/LEDGER.md, the current main_auto.py, and relevant replay
files. Do not repeat a rejected lesson. Keep agent() safe and fast; maximum ten
market orders; observation uses day/hour.

Champion: score={champion['score']:.1%}, margin={champion['margin_mean']:+.0f}
Weak matchups:
{weak_text}

Analysis:
```
{analysis[:12000]}
```
Worst losses:
{loss_text}

Recent experiment history:
{legacy.ledger_digest(ledger, lessons)[:6000]}

Diff from original seed:
```
{diff[:8000]}
```

Append a PLAN and CHANGE entry to {ledger}. If useful append one short lesson
to {lessons}. End with JSON describing the hypothesis and expected matchup.
"""


def accept_candidate(cand: dict, champ: dict, paired: dict, hard_paired: dict,
                     args) -> tuple[bool, str]:
    if cand["errors"]:
        return False, "runtime error"
    score_delta = cand["score"] - champ["score"]
    worst_delta, worst_name = worst_opp_regression(cand, champ)
    improves = (score_delta >= args.min_score_delta or
                (score_delta >= 0 and paired["margin_delta_mean"] >= args.min_margin_delta))
    if hard_paired["margin_delta_mean"] < args.min_hard_margin_delta:
        return False, f"hard-suite paired margin {hard_paired['margin_delta_mean']:+.0f} below gate"
    if worst_delta < -args.max_opponent_regress:
        return False, f"{worst_name} score regressed {worst_delta:.1%}"
    if not improves:
        return False, (f"insufficient dev gain: score {score_delta:+.1%}, "
                       f"paired margin {paired['margin_delta_mean']:+.0f}")
    return True, "development and hard-suite gates passed"


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dev-games", type=int, default=120)
    ap.add_argument("--hard-games", type=int, default=48)
    ap.add_argument("--validation-games", type=int, default=200)
    ap.add_argument("--target", type=float, default=0.82)
    ap.add_argument("--min-score-delta", type=float, default=0.01)
    ap.add_argument("--min-margin-delta", type=float, default=250.0)
    ap.add_argument("--min-hard-margin-delta", type=float, default=0.0)
    ap.add_argument("--max-opponent-regress", type=float, default=0.10)
    ap.add_argument("--validation-tolerance", type=float, default=0.02)
    ap.add_argument("--max-iters", type=int, default=15)
    ap.add_argument("--max-hours", type=float, default=12.0)
    ap.add_argument("--patience", type=int, default=6)
    ap.add_argument("--schedule-seed", type=int, default=20260904)
    ap.add_argument("--pool", nargs="+", default=None)
    ap.add_argument("--hard-opponents", nargs="+", default=None)
    ap.add_argument("--exclude-lineage", action="store_true")
    ap.add_argument("--seed-from", default="main.py")
    ap.add_argument("--driver", choices=["claude", "openai"], default="claude")
    ap.add_argument("--fallback-driver", choices=["claude", "openai", "none"], default="openai")
    ap.add_argument("--claude-bin", default=legacy.DEFAULT_CLAUDE_BIN)
    ap.add_argument("--claude-model", default=None)
    ap.add_argument("--claude-max-turns", type=int, default=60)
    ap.add_argument("--openai-model", default=None)
    ap.add_argument("--python", default=sys.executable or "python")
    ap.add_argument("--resume", default=None)
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()


def main():
    args = parse_args()
    run_dir = (Path(args.resume).resolve() if args.resume else
               RUNS_ROOT / dt.datetime.now().strftime("%Y%m%d-%H%M%S"))
    run_dir.mkdir(parents=True, exist_ok=True)
    lock = run_dir / "loop.lock"
    if lock.exists():
        raise SystemExit(f"active or stale lock: {lock}")
    lock.write_text(f"pid={legacy.os.getpid()}\n", encoding="utf-8")
    auto, champion = ROOT / "main_auto.py", run_dir / "champion.py"
    ledger, lessons, state_path = run_dir / "LEDGER.md", run_dir / "LESSONS.md", run_dir / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    started = time.time() - state.get("elapsed_s", 0)
    try:
        pool = unique_pool(args.pool, args.exclude_lineage)
        hard_pool = select_hard(pool, args.hard_opponents)
        dev = make_schedule(pool, args.dev_games, args.schedule_seed)
        hard = make_schedule(hard_pool, args.hard_games, args.schedule_seed + 10_000)
        validation = make_schedule(pool, args.validation_games, args.schedule_seed + 20_000)
        schedules = {"dev": dev, "hard": hard, "validation": validation}
        schedule_meta = {k: schedule_digest(v) for k, v in schedules.items()}
        if state.get("schedules") not in (None, schedule_meta):
            raise SystemExit("resume arguments changed the saved schedules")
        if not champion.exists():
            source = auto if auto.exists() else ROOT / args.seed_from
            shutil.copy2(source, champion)
        shutil.copy2(champion, auto)
        if not ledger.exists():
            ledger.write_text("# auto_improve_v2 ledger\n\n", encoding="utf-8")
        if not lessons.exists():
            lessons.write_text("# lessons\n\n", encoding="utf-8")

        bootstrap = run_dir / "bootstrap"
        bootstrap.mkdir(exist_ok=True)
        if "champion_dev" not in state:
            cm, cr = evaluate(champion, dev, bootstrap, "champion_dev")
            vm, _ = evaluate(champion, validation, bootstrap, "champion_validation", store=False)
            state.update(champion_dev=cm, champion_validation=vm, schedules=schedule_meta,
                         iteration=0, accepted=0, last_accept=0)
            state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

        iteration = state.get("iteration", 0)
        driver_name = state.get("driver", args.driver)
        while iteration < args.max_iters:
            if (time.time() - started) / 3600 >= args.max_hours or (run_dir / "STOP").exists():
                break
            if iteration - state.get("last_accept", 0) >= args.patience and iteration:
                print("patience exhausted")
                break
            idir = run_dir / f"iter_{iteration:02d}"
            idir.mkdir(exist_ok=True)
            shutil.copy2(champion, auto)
            champ_metrics, champ_rows = evaluate(champion, dev, idir, "champion_dev")
            report = legacy.analysis_report(idir / "champion_dev", args.python)
            losses = sorted((r for r in champ_rows if r["result"] == "LOSS"),
                            key=lambda r: r["margin"])[:5]
            diff = legacy.sh(["git", "diff", "--no-index", "--", str(ROOT / args.seed_from),
                              str(champion)]).stdout or "(no diff)"
            prompt = prompt_for(iteration, champ_metrics, report, losses, ledger, lessons, diff)
            (idir / "prompt.txt").write_text(prompt, encoding="utf-8")
            if args.dry_run:
                print(f"dry-run prompt: {idir / 'prompt.txt'}")
                break

            before_status = legacy.git_status_paths()
            result = legacy.make_driver(driver_name, args).run_fix(prompt, idir)
            if not result.ok and result.usage_limited and args.fallback_driver not in ("none", driver_name):
                driver_name = args.fallback_driver
                result = legacy.make_driver(driver_name, args).run_fix(prompt, idir)
            stray = sorted(p for p in legacy.git_status_paths() - before_status if not legacy.is_allowed(p))
            sane, why = legacy.candidate_sane(args.python) if result.ok and not stray else (False, "stray edits: " + ", ".join(stray))
            decision = {"accepted": False, "driver_ok": result.ok, "sane": sane,
                        "reason": result.error or why, "stray": stray}
            if sane:
                ch, chr_ = evaluate(champion, hard, idir, "champion_hard", store=False)
                ah, ahr = evaluate(auto, hard, idir, "candidate_hard")
                hp = paired_stats(ahr, chr_)
                candidate_metrics, candidate_rows = evaluate(auto, dev, idir, "candidate_dev")
                paired = paired_stats(candidate_rows, champ_rows)
                accepted, reason = accept_candidate(candidate_metrics, champ_metrics, paired, hp, args)
                decision.update(reason=reason, candidate=candidate_metrics, champion=champ_metrics,
                                paired=paired, hard_candidate=ah, hard_champion=ch, hard_paired=hp)
                if accepted:
                    cv, _ = evaluate(champion, validation, idir, "champion_validation", store=False)
                    av, _ = evaluate(auto, validation, idir, "candidate_validation", store=False)
                    if av["errors"] or av["score"] < cv["score"] - args.validation_tolerance:
                        decision["reason"] = (f"hidden validation regressed: {cv['score']:.1%} "
                                              f"to {av['score']:.1%}")
                    else:
                        shutil.copy2(auto, champion)
                        decision["accepted"] = True
                        decision["validation_champion"] = cv
                        decision["validation_candidate"] = av
                        state["accepted"] = state.get("accepted", 0) + 1
                        state["last_accept"] = iteration + 1
                        state["champion_dev"] = candidate_metrics
                        state["champion_validation"] = av
            if not decision["accepted"]:
                shutil.copy2(champion, auto)
            (idir / "decision.json").write_text(json.dumps(decision, indent=2), encoding="utf-8")
            legacy.append_ledger(ledger, f"## iter {iteration} -- "
                                 f"{'ACCEPTED' if decision['accepted'] else 'REJECTED'}\n"
                                 f"{decision['reason']}")
            iteration += 1
            state.update(iteration=iteration, driver=driver_name, elapsed_s=time.time() - started,
                         schedules=schedule_meta)
            state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
            print(f"iter {iteration - 1}: {'ACCEPT' if decision['accepted'] else 'REJECT'} - {decision['reason']}")
            if decision["accepted"] and state["champion_validation"]["score"] >= args.target:
                state["outcome"] = "target_met"
                state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
                break
        shutil.copy2(champion, auto)
        print(f"champion: {champion}")
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
