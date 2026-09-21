#!/usr/bin/env python3
"""Download representative replays for the Kaggriculture leaderboard leaders.

Examples:
    python download_top_replays.py
    python download_top_replays.py --top 20 --episodes-per-team 3
    python download_top_replays.py --skip-logs
    python download_top_replays.py --output ladder_replays --refresh

The script uses the authenticated official Kaggle CLI. Competitor logs are
normally private (HTTP 403); those failures are recorded without aborting.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


COMPETITION = "kaggriculture"
PYTHON_CANDIDATES = [
    os.environ.get("KAGGLE_PY"),
    sys.executable,
    r"C:\Users\LENOVO\AppData\Local\Programs\Python\Python313\python.exe",
    "python3",
    "python",
]


def resolve_kaggle() -> list[str]:
    executable = shutil.which("kaggle")
    candidates = [[executable]] if executable else []
    candidates += [[p, "-m", "kaggle"] for p in PYTHON_CANDIDATES if p]
    for command in candidates:
        try:
            result = subprocess.run(
                command + ["--version"], capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=20,
            )
            if result.returncode == 0:
                return command
        except (OSError, subprocess.TimeoutExpired):
            pass
    raise SystemExit(
        "A working Kaggle CLI was not found. Run `pip install -U kaggle`, "
        "or set KAGGLE_PY to a Python executable containing the kaggle package."
    )


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(
        KAGGLE + command, capture_output=True, text=True, encoding="utf-8",
        errors="replace", env=env,
    )
    if check and result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"Kaggle command failed ({result.returncode}): {detail}")
    return result


def json_output(command: list[str]) -> list[dict]:
    result = run(command + ["--format", "json"])
    # Notices such as a next-page token can appear around the JSON. Decode from
    # the first array opener instead of assuming stdout contains JSON alone.
    start = result.stdout.find("[")
    if start < 0:
        raise RuntimeError(f"No JSON returned by: {' '.join(command)}")
    value, _ = json.JSONDecoder().raw_decode(result.stdout[start:])
    return value


def same_score(left: object, right: object) -> bool:
    try:
        return abs(float(left) - float(right)) < 0.05
    except (TypeError, ValueError):
        return False


def active_submission(team_id: int, leaderboard_score: object) -> dict:
    submissions = json_output([
        "competitions", "team-submissions", str(team_id),
    ])
    if not submissions:
        raise RuntimeError(f"Team {team_id} has no visible submissions")
    # The leaderboard displays a team's best active bot, which is not always
    # its newest submission. Match its score first and use recency as fallback.
    matches = [s for s in submissions
               if same_score(s.get("publicScore"), leaderboard_score)]
    return (matches or submissions)[0]


def public_episodes(submission_id: int) -> list[dict]:
    episodes = json_output([
        "competitions", "episodes", str(submission_id),
    ])
    return [
        episode for episode in episodes
        if "COMPLETED" in str(episode.get("state", ""))
        and "PUBLIC" in str(episode.get("type", ""))
    ]


def _valid_json(path: Path) -> bool:
    """True iff `path` is a non-empty, parseable JSON file. A truncated pull
    (network cut, CLI error leaving bytes on disk) is deleted so the next run
    re-fetches it instead of treating the stub as a real replay (P0.7 fix)."""
    try:
        if path.stat().st_size < 2:
            raise ValueError("empty file")
        json.loads(path.read_text(encoding="utf-8"))
        return True
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        return False


# regression guard (P0.7): _valid_json must never raise, even on a missing path
assert _valid_json(Path("__nonexistent_probe__.json")) is False


def download(kind: str, episode_id: int, output: Path,
             agent: int | None = None) -> tuple[bool, str]:
    command = ["competitions", kind, str(episode_id)]
    if agent is not None:
        command.append(str(agent))
    command += ["-p", str(output), "-q"]
    result = run(command, check=False)
    message = (result.stderr or result.stdout).strip()
    if result.returncode != 0:
        return False, message
    suffix = f"-agent-{agent}-logs" if agent is not None else "-replay"
    landed = output / f"episode-{episode_id}{suffix}.json"
    if not _valid_json(landed):
        return False, "partial/corrupt download (deleted)"
    return True, message


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", type=int, default=3,
                        help="number of leaderboard teams (default: 10)")
    parser.add_argument("--episodes-per-team", type=int, default=1,
                        help="newest public episodes per team (default: 1)")
    parser.add_argument("--output", type=Path, default=Path("top10_ladder"),
                        help="output directory (default: top10_ladder)")
    parser.add_argument("--skip-logs", action="store_true",
                        help="do not request either agent's logs")
    parser.add_argument("--refresh", action="store_true",
                        help="download files even when already present")
    args = parser.parse_args()
    if args.top < 1 or args.episodes_per_team < 1:
        parser.error("--top and --episodes-per-team must be positive")

    replay_dir = args.output / "replays"
    log_dir = args.output / "logs"
    replay_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    print(f"Reading the top {args.top} leaderboard teams...")
    leaders = json_output([
        "competitions", "leaderboard", COMPETITION, "--show",
        "--page-size", str(args.top),
    ])[:args.top]

    rows: list[dict] = []
    selected: dict[int, list[str]] = {}
    for rank, leader in enumerate(leaders, 1):
        team = leader.get("teamName", f"team-{leader['teamId']}")
        print(f"[{rank}/{len(leaders)}] {team}: resolving submission...")
        submission = active_submission(leader["teamId"], leader.get("score"))
        episodes = public_episodes(submission["id"])
        if not episodes:
            print("  no completed public episodes")
            continue
        for episode in episodes[:args.episodes_per_team]:
            episode_id = int(episode["id"])
            selected.setdefault(episode_id, []).append(team)
            rows.append({
                "rank": rank,
                "team": team,
                "score": leader.get("score", ""),
                "team_id": leader["teamId"],
                "submission_id": submission["id"],
                "episode_id": episode_id,
                "create_time": episode.get("createTime", ""),
            })

    log_status: dict[tuple[int, int], str] = {}
    for number, (episode_id, teams) in enumerate(selected.items(), 1):
        print(f"[{number}/{len(selected)}] episode {episode_id}: {', '.join(teams)}")
        replay_file = replay_dir / f"episode-{episode_id}-replay.json"
        if args.refresh or not replay_file.exists():
            ok, message = download("replay", episode_id, replay_dir)
            if not ok:
                print(f"  replay failed: {message}")
            else:
                print("  replay downloaded")
        else:
            print("  replay already present")

        if args.skip_logs:
            continue
        for agent in (0, 1):
            log_file = log_dir / f"episode-{episode_id}-agent-{agent}-logs.json"
            if not args.refresh and log_file.exists():
                log_status[episode_id, agent] = "downloaded"
                continue
            ok, message = download("logs", episode_id, log_dir, agent)
            if ok:
                log_status[episode_id, agent] = "downloaded"
            elif "403" in message or "Forbidden" in message:
                log_status[episode_id, agent] = "forbidden"
            else:
                log_status[episode_id, agent] = f"failed: {message}"
            print(f"  agent {agent} log: {log_status[episode_id, agent]}")

    manifest = args.output / "manifest.csv"
    fields = ["rank", "team", "score", "team_id", "submission_id",
              "episode_id", "create_time", "agent_0_log", "agent_1_log"]
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            episode_id = row["episode_id"]
            row["agent_0_log"] = log_status.get((episode_id, 0), "skipped")
            row["agent_1_log"] = log_status.get((episode_id, 1), "skipped")
            writer.writerow(row)

    metadata = {
        "competition": COMPETITION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "top": args.top,
        "episodes_per_team": args.episodes_per_team,
        "unique_episodes": len(selected),
        "rows": rows,
    }
    (args.output / "manifest.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    print(f"Done: {len(selected)} unique replay(s). Manifest: {manifest}")


KAGGLE = resolve_kaggle()


if __name__ == "__main__":
    main()
