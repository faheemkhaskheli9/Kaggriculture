#!/usr/bin/env python3
"""
Download all Kaggle submissions, their episode replays, and agent logs for the
`kaggriculture` competition so they can be mined offline to improve gameplay.

What it does
------------
1. `kaggle competitions submissions kaggriculture`  -> list of my submissions
2. `kaggle competitions episodes <SUBMISSION_ID>`   -> episodes played by each
3. `kaggle competitions replay <EPISODE_ID>`        -> replay JSON  -> ./replays
4. `kaggle competitions logs <EPISODE_ID> <agent>`  -> agent logs   -> ./logs

Incremental: a manifest (episodes/manifest.json) plus on-disk file checks mean
only NEW episodes are fetched. Re-run any time after new games are played.

Outputs
-------
  replays/episode-<ID>-replay.json           raw replay (env.toJSON dump)
  logs/episode-<ID>-agent-<N>-logs.json      per-agent stderr/stdout logs
  episodes/episode-<ID>.json                 metadata (submission ref, score, times)
  episodes/manifest.json                     download bookkeeping
  episodes/index.csv                         flat table of every known episode

Usage
-----
  python download_episodes.py                     # download everything new
  python download_episodes.py --agents 0          # only my-agent logs (index 0)
  python download_episodes.py --skip-validation   # ignore VALIDATION episodes
  python download_episodes.py --submissions 55952549 55945642
  python download_episodes.py --refresh           # re-scan even known episodes
  python download_episodes.py --dry-run

The kaggle CLI + auth token must already be set up (kaggle 2.2.4 here lives in
the Python 3.13 install; this script auto-detects a working interpreter).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

COMPETITION = "kaggriculture"
ROOT = Path(__file__).resolve().parent
REPLAY_DIR = ROOT / "replays"
LOG_DIR = ROOT / "logs"
EP_DIR = ROOT / "episodes"
MANIFEST_PATH = EP_DIR / "manifest.json"
INDEX_PATH = EP_DIR / "index.csv"

# Candidate interpreters that might have the `kaggle` module installed.
_PY_CANDIDATES = [
    os.environ.get("KAGGLE_PY"),
    r"C:\Users\LENOVO\AppData\Local\Programs\Python\Python313\python.exe",
    sys.executable,
    "python3",
    "python",
]


# --------------------------------------------------------------------------- #
# kaggle CLI plumbing
# --------------------------------------------------------------------------- #
def _resolve_kaggle_cmd() -> list[str]:
    """Return an argv prefix that runs the kaggle CLI, or exit with a hint."""
    # 1) a real `kaggle` executable on PATH
    exe = shutil.which("kaggle")
    if exe:
        try:
            subprocess.run([exe, "--version"], capture_output=True, check=True)
            return [exe]
        except Exception:
            pass
    # 2) `<python> -m kaggle` for each candidate interpreter
    seen: set[str] = set()
    for py in _PY_CANDIDATES:
        if not py:
            continue
        resolved = shutil.which(py) or py
        if resolved in seen or not (resolved == py or Path(resolved).exists() or shutil.which(py)):
            continue
        seen.add(resolved)
        try:
            r = subprocess.run([resolved, "-m", "kaggle", "--version"],
                               capture_output=True, check=True, text=True)
            if "Kaggle CLI" in (r.stdout + r.stderr):
                return [resolved, "-m", "kaggle"]
        except Exception:
            continue
    sys.exit(
        "ERROR: could not find a working `kaggle` CLI.\n"
        "  pip install kaggle   (into the interpreter you want to use)\n"
        "  or set KAGGLE_PY=<path to python.exe that has kaggle installed>"
    )


KAGGLE = _resolve_kaggle_cmd()


def _run(args: list[str], *, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(KAGGLE + args, capture_output=capture, text=True)


def _parse_csv_block(text: str, key_col: str) -> list[dict]:
    """Pull the CSV block out of kaggle CLI output (it appends chatter lines)."""
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines)
                  if ln.strip().startswith(key_col + ",")), None)
    if start is None:
        return []
    # The kaggle CLI pads its CSV with blank lines between rows and appends a
    # "Use ..." hint line; keep data rows, drop the blanks and the chatter.
    block: list[str] = [lines[start]]
    for ln in lines[start + 1:]:
        s = ln.strip()
        if not s:
            continue
        if s.startswith('Use "') or s.startswith("Use '"):
            break
        block.append(ln)
    reader = csv.DictReader(io.StringIO("\n".join(block)))
    return [row for row in reader if row.get(key_col)]


def list_submissions() -> list[dict]:
    r = _run(["competitions", "submissions", COMPETITION, "--csv"])
    if r.returncode != 0:
        sys.exit(f"ERROR listing submissions:\n{r.stdout}\n{r.stderr}")
    return _parse_csv_block(r.stdout, "ref")


def list_episodes(submission_id: str) -> list[dict]:
    r = _run(["competitions", "episodes", str(submission_id), "--csv"])
    if r.returncode != 0:
        print(f"  ! could not list episodes for {submission_id}: "
              f"{r.stderr.strip() or r.stdout.strip()}")
        return []
    return _parse_csv_block(r.stdout, "id")


def download_replay(episode_id: str, quiet: bool) -> bool:
    args = ["competitions", "replay", str(episode_id), "-p", str(REPLAY_DIR)]
    if quiet:
        args.append("-q")
    r = _run(args, capture=quiet)
    if r.returncode != 0:
        msg = (r.stderr or r.stdout or "").strip() if quiet else "see output above"
        print(f"  ! replay {episode_id} failed: {msg}")
        return False
    return (REPLAY_DIR / f"episode-{episode_id}-replay.json").exists()


def download_logs(episode_id: str, agent_index: int, quiet: bool) -> tuple[bool, bool]:
    """Return (ok, forbidden). `forbidden` = this agent slot is the opponent's."""
    args = ["competitions", "logs", str(episode_id), str(agent_index),
            "-p", str(LOG_DIR)]
    if quiet:
        args.append("-q")
    r = _run(args, capture=quiet)
    out = (r.stderr or r.stdout or "")
    if r.returncode != 0:
        forbidden = "403" in out or "Forbidden" in out
        note = "opponent slot (403)" if forbidden else (out.strip() or "unavailable")
        print(f"  · logs {episode_id} agent {agent_index}: {note}")
        return False, forbidden
    ok = (LOG_DIR / f"episode-{episode_id}-agent-{agent_index}-logs.json").exists()
    return ok, False


# --------------------------------------------------------------------------- #
# manifest / index
# --------------------------------------------------------------------------- #
def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("  ! manifest.json unreadable - starting fresh")
    return {}


def save_manifest(manifest: dict) -> None:
    EP_DIR.mkdir(exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def replay_present(episode_id: str) -> bool:
    return (REPLAY_DIR / f"episode-{episode_id}-replay.json").exists()


def logs_present(episode_id: str, agent_index: int) -> bool:
    return (LOG_DIR / f"episode-{episode_id}-agent-{agent_index}-logs.json").exists()


def write_index(manifest: dict) -> None:
    rows = sorted(manifest.values(),
                  key=lambda e: e.get("endTime") or e.get("createTime") or "")
    cols = ["episode_id", "submission_ref", "submission_score", "type", "state",
            "createTime", "endTime", "replay", "logs", "downloaded_at"]
    with INDEX_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for e in rows:
            w.writerow({
                "episode_id": e.get("episode_id", ""),
                "submission_ref": e.get("submission_ref", ""),
                "submission_score": e.get("submission_score", ""),
                "type": (e.get("type", "") or "").replace("EpisodeType.EPISODE_TYPE_", ""),
                "state": (e.get("state", "") or "").replace("EpisodeState.", ""),
                "createTime": e.get("createTime", ""),
                "endTime": e.get("endTime", ""),
                "replay": "yes" if e.get("replay") else "no",
                "logs": ",".join(str(i) for i in e.get("logs", [])),
                "downloaded_at": e.get("downloaded_at", ""),
            })


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agents", type=int, nargs="+", default=[0, 1],
                    help="agent indices to fetch logs for (default: 0 1; "
                         "opponent logs may be inaccessible - that's fine)")
    ap.add_argument("--submissions", nargs="+", metavar="ID",
                    help="only these submission IDs (default: all of mine)")
    ap.add_argument("--skip-validation", action="store_true",
                    help="skip EPISODE_TYPE_VALIDATION episodes")
    ap.add_argument("--refresh", action="store_true",
                    help="re-download replay/logs even if already on disk")
    ap.add_argument("--sleep", type=float, default=1.0,
                    help="seconds to pause between downloads (default: 1.0)")
    ap.add_argument("--verbose", action="store_true",
                    help="show kaggle CLI progress output")
    ap.add_argument("--dry-run", action="store_true",
                    help="list what would be downloaded, fetch nothing")
    args = ap.parse_args()
    quiet = not args.verbose

    for d in (REPLAY_DIR, LOG_DIR, EP_DIR):
        d.mkdir(exist_ok=True)

    print(f"kaggle CLI: {' '.join(KAGGLE)}")
    manifest = load_manifest()

    subs = list_submissions()
    if args.submissions:
        wanted = {str(s) for s in args.submissions}
        subs = [s for s in subs if s["ref"] in wanted]
    if not subs:
        sys.exit("No matching submissions found.")

    print(f"\n{len(subs)} submission(s):")
    for s in subs:
        print(f"  {s['ref']}  score={s.get('publicScore') or '-':>7}  "
              f"{s.get('date', '')}  {s.get('description') or ''}".rstrip())

    # collect episodes across submissions (an episode can appear under one sub)
    episodes: dict[str, dict] = {}
    for s in subs:
        eps = list_episodes(s["ref"])
        print(f"\nsubmission {s['ref']}: {len(eps)} episode(s) reported")
        for ep in eps:
            eid = ep["id"]
            if args.skip_validation and "VALIDATION" in ep.get("type", ""):
                continue
            episodes.setdefault(eid, {
                "episode_id": eid,
                "submission_ref": s["ref"],
                "submission_score": s.get("publicScore", ""),
                "createTime": ep.get("createTime", ""),
                "endTime": ep.get("endTime", ""),
                "state": ep.get("state", ""),
                "type": ep.get("type", ""),
            })

    print(f"\n{len(episodes)} unique episode(s) to consider "
          f"({len(manifest)} already in manifest)\n")

    new_replays = new_logs = skipped = 0

    for eid, meta in sorted(episodes.items()):
        entry = manifest.get(eid, {})
        entry.update({k: meta[k] for k in meta})  # keep metadata fresh
        entry.setdefault("logs", [])
        forbidden = set(entry.get("logs_forbidden", []))

        # On-disk files are the source of truth for "already downloaded".
        # Agent slots already known to be the opponent's (403) aren't retried.
        need_replay = args.refresh or not replay_present(eid)
        need_agents = [a for a in args.agents
                       if args.refresh
                       or (not logs_present(eid, a) and a not in forbidden)]

        if not need_replay and not need_agents:
            skipped += 1
            entry["replay"] = replay_present(eid)
            entry["logs"] = sorted(set(entry.get("logs", [])) |
                                   {a for a in args.agents if logs_present(eid, a)})
            manifest[eid] = entry
            continue

        label = meta["type"].replace("EpisodeType.EPISODE_TYPE_", "")
        print(f"episode {eid}  [{label}]  sub={meta['submission_ref']} "
              f"score={meta['submission_score'] or '-'}")

        if args.dry_run:
            if need_replay:
                print("  would download replay")
            for a in need_agents:
                print(f"  would download logs agent {a}")
            manifest[eid] = entry
            continue

        if need_replay:
            if download_replay(eid, quiet):
                entry["replay"] = True
                new_replays += 1
                print("  replay ok")
            time.sleep(args.sleep)
        else:
            entry["replay"] = True

        for a in need_agents:
            ok, is_forbidden = download_logs(eid, a, quiet)
            if ok:
                new_logs += 1
                print(f"  logs agent {a} ok")
            elif is_forbidden:
                forbidden.add(a)
            time.sleep(args.sleep)
        # record every agent whose log file is on disk, not just this run's
        entry["logs"] = sorted({a for a in args.agents if logs_present(eid, a)}
                               | set(entry.get("logs", [])))
        if forbidden:
            entry["logs_forbidden"] = sorted(forbidden)

        entry["downloaded_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        manifest[eid] = entry

        # per-episode metadata sidecar
        (EP_DIR / f"episode-{eid}.json").write_text(
            json.dumps(entry, indent=2, sort_keys=True), encoding="utf-8")

    save_manifest(manifest)
    write_index(manifest)

    print(f"\ndone. {new_replays} new replay(s), {new_logs} new log file(s), "
          f"{skipped} episode(s) already up to date.")
    print(f"manifest : {MANIFEST_PATH}")
    print(f"index    : {INDEX_PATH}")


if __name__ == "__main__":
    main()
