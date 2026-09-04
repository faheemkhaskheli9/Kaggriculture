"""Immutable champion/challenger registry for Kaggriculture submissions."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "ml" / "artifacts" / "champions"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True).stdout.strip()
    except Exception:
        return "unknown"


def archive(agent: Path, name: str, status: str, report: Path | None = None,
            submission_id: str = "", kaggle_score: str = "") -> Path:
    if status not in {"champion", "challenger", "rejected", "rolled_back"}:
        raise ValueError(f"invalid status: {status}")
    agent = agent.resolve()
    if not agent.is_file():
        raise FileNotFoundError(agent)
    digest = sha256(agent)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = REGISTRY / f"{stamp}_{name}_{digest[:10]}"
    dest.mkdir(parents=True, exist_ok=False)
    shutil.copy2(agent, dest / "main.py")
    if report and report.is_file():
        shutil.copy2(report, dest / "evaluation.json")
    manifest = {
        "name": name, "status": status, "created_at": datetime.now(timezone.utc).isoformat(),
        "agent_source": str(agent), "sha256": digest, "git_commit": git_commit(),
        "submission_id": submission_id, "kaggle_score": kaggle_score,
    }
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return dest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("agent")
    ap.add_argument("--name", required=True)
    ap.add_argument("--status", choices=["champion", "challenger", "rejected", "rolled_back"],
                    default="challenger")
    ap.add_argument("--report")
    ap.add_argument("--submission-id", default="")
    ap.add_argument("--kaggle-score", default="")
    args = ap.parse_args()
    out = archive(ROOT / args.agent, args.name, args.status,
                  ROOT / args.report if args.report else None,
                  args.submission_id, args.kaggle_score)
    print(out)


if __name__ == "__main__":
    main()
