"""Restart-safe continuous learning supervisor.

The loop downloads/indexes data, resumes an optimizer, gates its best config,
and exports qualifying challengers. It never submits or overwrites main.py.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from ml.replay_index import DEFAULT_DB, update_index

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "ml" / "artifacts" / "runner"
DEFAULT_CONFIG = ROOT / "ml" / "loop_config.json"


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


class Lock:
    def __init__(self, path: Path):
        self.path = path
        self.fd = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise SystemExit(f"another learning loop owns {self.path}") from exc
        os.write(self.fd, f"pid={os.getpid()}\nstarted={datetime.now(timezone.utc).isoformat()}\n".encode())
        return self

    def __exit__(self, *_):
        if self.fd is not None:
            os.close(self.fd)
        self.path.unlink(missing_ok=True)


def load_config(path: Path) -> dict:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg.setdefault("download", {})
    cfg.setdefault("index", {})
    cfg.setdefault("preflight", {})
    cfg.setdefault("optimize", {})
    cfg.setdefault("gate", {})
    return cfg


def run_command(name: str, argv: list[str], log_dir: Path, dry_run: bool,
                timeout_seconds: float = 0) -> int:
    print(f"[{name}] {' '.join(argv)}")
    if dry_run:
        return 0
    log_dir.mkdir(parents=True, exist_ok=True)
    log = log_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{name}.log"
    env = os.environ.copy()
    native_threads = str(env.get("ML_NATIVE_THREADS", "1"))
    env["ML_NATIVE_THREADS"] = native_threads
    for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                     "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        env[variable] = native_threads
    try:
        with log.open("w", encoding="utf-8") as fh:
            result = subprocess.run(
                argv, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT,
                text=True, check=False, env=env,
                timeout=timeout_seconds if timeout_seconds > 0 else None)
        rc = result.returncode
    except subprocess.TimeoutExpired:
        rc = 124
        with log.open("a", encoding="utf-8") as fh:
            fh.write(f"\nTIMEOUT after {timeout_seconds:.0f} seconds\n")
    print(f"[{name}] exit={rc} log={log}")
    return rc


def qualifies(report: dict, cfg: dict) -> tuple[bool, list[str]]:
    failures = []
    if report.get("errors", 0):
        failures.append("agent errors")
    if report.get("p10_coins", 0) < cfg.get("min_p10_coins", 0):
        failures.append("p10 below floor")
    if report.get("terminal_unsold", 0) > cfg.get("max_terminal_unsold", 3):
        failures.append("terminal unsold above limit")
    if report.get("ms_step", 999) > cfg.get("max_ms_step", 4):
        failures.append("runtime above limit")
    if report.get("mean_score_rate", 0) < cfg.get("min_mean_score_rate", 0.5):
        failures.append("mean score rate below floor")
    paired = report.get("paired")
    if cfg.get("require_paired_improvement", False):
        if not paired:
            failures.append("paired incumbent comparison missing")
        elif paired.get("score_delta_lcb95", -1) <= cfg.get("min_score_delta_lcb95", 0):
            failures.append("paired score improvement is not statistically credible")
        if paired and paired.get("margin_delta", 0) < cfg.get("min_margin_delta", 0):
            failures.append("paired margin regressed")
    if report.get("plant_deaths", 0) > cfg.get("max_plant_deaths", 0):
        failures.append("avoidable plant deaths above limit")
    if report.get("animal_escapes", 0) > cfg.get("max_animal_escapes", 0):
        failures.append("animal escapes above limit")
    if report.get("market_order_overflow", 0):
        failures.append("market order overflow")
    animal_floor = cfg.get("min_animal_score_rate", 0.5)
    for opponent, metrics in report.get("per_opponent", {}).items():
        if "animal" in opponent and metrics.get("score_rate", 0) < animal_floor:
            failures.append(f"{opponent} score rate below floor")
    return not failures, failures


def cycle(cfg: dict, dry_run: bool = False) -> dict:
    started = datetime.now(timezone.utc)
    cycle_id = started.strftime("%Y%m%dT%H%M%SZ")
    state = {"cycle": cycle_id, "started_at": started.isoformat(),
             "dry_run": dry_run, "stages": {}}
    logs = RUNNER / "logs"
    stop = RUNNER / "STOP"
    if stop.exists():
        state["stopped"] = "STOP file present"
        return state

    pcfg = cfg["preflight"]
    if pcfg.get("enabled", True):
        argv = [sys.executable, "-m", "ml.evaluate", "--engine",
                pcfg.get("engine", "v7"), "--default", "--league",
                pcfg.get("league", "quick"), "--games",
                str(pcfg.get("games", 2)), "--workers", str(pcfg.get("workers", 2)),
                "--seed", str(pcfg.get("seed", 9_000_000))]
        rc = run_command("preflight", argv, logs, dry_run,
                         float(pcfg.get("timeout_seconds", 600)))
        state["stages"]["preflight"] = {"returncode": rc}
        if rc:
            raise RuntimeError(
                "evaluation preflight failed; optimizer was not started "
                f"(returncode={rc})")

    dcfg = cfg["download"]
    if dcfg.get("enabled", False):
        argv = [sys.executable, "download_episodes.py"] + list(dcfg.get("args", []))
        rc = run_command("download", argv, logs, dry_run)
        state["stages"]["download"] = {"returncode": rc}
        if rc and dcfg.get("required", False):
            raise RuntimeError("required replay download failed")

    icfg = cfg["index"]
    if icfg.get("enabled", True):
        roots = [ROOT / p for p in icfg.get("roots", [
            "replays", "compete_runs", "benchmark_replays", "tournament_replays"])]
        result = ({"dry_run": True} if dry_run else
                  update_index(roots, Path(icfg.get("db", DEFAULT_DB)),
                               int(icfg.get("max_new_per_cycle", 50))))
        print(f"[index] {result}")
        state["stages"]["index"] = result

    ocfg = cfg["optimize"]
    out = ROOT / ocfg.get("out", "ml/artifacts/continuous/current")
    if ocfg.get("enabled", False):
        argv = [sys.executable, "-m", "ml.optimize"] + list(ocfg.get("args", []))
        if "--out" not in argv:
            argv += ["--out", str(out)]
        if "--resume" not in argv:
            argv.append("--resume")
        rc = run_command("optimize", argv, logs, dry_run,
                         float(ocfg.get("timeout_seconds", 0)))
        state["stages"]["optimize"] = {"returncode": rc, "out": str(out)}
        if rc:
            raise RuntimeError("optimizer failed")

    best = out / "best.json"
    gcfg = cfg["gate"]
    if gcfg.get("enabled", False) and (best.exists() or dry_run):
        report = RUNNER / "reports" / f"{cycle_id}.json"
        argv = [sys.executable, "-m", "ml.evaluate", "--params", str(best),
                "--engine", gcfg.get("engine", "v7"), "--league", gcfg.get("league", "ladder_econ"),
                "--games", str(gcfg.get("games", 50)), "--workers", str(gcfg.get("workers", 1)),
                "--seed", str(gcfg.get("seed", 70000000)), "--json-out", str(report)]
        incumbent_params = gcfg.get("incumbent_params", "default")
        if incumbent_params:
            argv += ["--incumbent-params", str(incumbent_params),
                     "--bootstrap-samples", str(gcfg.get("bootstrap_samples", 10_000))]
        rc = run_command("gate", argv, logs, dry_run)
        state["stages"]["gate"] = {"returncode": rc, "report": str(report)}
        if rc:
            raise RuntimeError("promotion gate failed")
        if not dry_run:
            data = json.loads(report.read_text(encoding="utf-8"))
            ok, failures = qualifies(data, gcfg)
            state["stages"]["gate"].update({"qualified": ok, "failures": failures})
            if ok:
                challenger = RUNNER / "challengers" / f"main_{cycle_id}.py"
                rc = run_command("export", [sys.executable, "-m", "ml.export_main",
                                 "--engine", gcfg.get("engine", "v7"), str(best),
                                 "-o", str(challenger)], logs, False)
                state["stages"]["export"] = {"returncode": rc, "challenger": str(challenger)}
                if rc:
                    raise RuntimeError("challenger export failed")

    state["finished_at"] = datetime.now(timezone.utc).isoformat()
    return state


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--daemon", action="store_true", help="repeat cycles until STOP exists")
    ap.add_argument("--interval-minutes", type=float, default=60)
    args = ap.parse_args()
    cfg = load_config(Path(args.config))
    with Lock(RUNNER / "loop.lock"):
        while True:
            try:
                state = cycle(cfg, args.dry_run)
            except Exception as exc:
                state = {"failed_at": datetime.now(timezone.utc).isoformat(),
                         "error": f"{type(exc).__name__}: {exc}",
                         "traceback": traceback.format_exc()}
                print(state["error"])
            atomic_json(RUNNER / "last_cycle.json", state)
            history = RUNNER / "history.jsonl"
            history.parent.mkdir(parents=True, exist_ok=True)
            with history.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(state, separators=(",", ":")) + "\n")
            if not args.daemon or args.dry_run or (RUNNER / "STOP").exists():
                break
            time.sleep(max(60, args.interval_minutes * 60))


if __name__ == "__main__":
    main()
