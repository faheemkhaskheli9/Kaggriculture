"""Incremental SQLite index for local and Kaggle Kaggriculture replays."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "ml" / "artifacts" / "state" / "replays.sqlite3"


def _open_replay(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    return opener(path, "rt", encoding="utf-8")


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _metadata(path: Path) -> dict:
    with _open_replay(path) as fh:
        replay = json.load(fh)
    steps = replay.get("steps") or []
    agents = (replay.get("info") or {}).get("Agents") or []
    names = [str(a.get("Name", "")) if isinstance(a, dict) else str(a) for a in agents]
    final_money = []
    if steps:
        for seat, state in enumerate(steps[-1]):
            try:
                final_money.append(float(state["observation"]["farms"][seat]["money"]))
            except Exception:
                final_money.append(float(state.get("reward") or 0))
    return {
        "steps": len(steps),
        "agents": names,
        "final_money": final_money,
        "seed": (replay.get("info") or {}).get("seed"),
    }


def connect(db_path: Path = DEFAULT_DB) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(db_path)
    db.execute("""
        CREATE TABLE IF NOT EXISTS replays (
            sha256 TEXT PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            mtime_ns INTEGER NOT NULL,
            steps INTEGER NOT NULL,
            agents_json TEXT NOT NULL,
            final_money_json TEXT NOT NULL,
            seed TEXT,
            indexed_at TEXT NOT NULL
        )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS replay_source_idx ON replays(source)")
    return db


def discover(roots: list[Path]):
    seen = set()
    for root in roots:
        if not root.exists():
            continue
        patterns = ("*.replay.json.gz", "episode-*-replay.json")
        for pattern in patterns:
            for path in root.rglob(pattern):
                path = path.resolve()
                if path not in seen:
                    seen.add(path)
                    yield path


def source_for(path: Path) -> str:
    parts = {p.lower() for p in path.parts}
    if "replays" in parts:
        return "kaggle"
    if "compete_runs" in parts:
        return "local_compete"
    if "benchmark_replays" in parts:
        return "local_benchmark"
    if "tournament_replays" in parts:
        return "local_tournament"
    return "local"


def update_index(roots: list[Path], db_path: Path = DEFAULT_DB,
                 max_new: int = 0) -> dict:
    db = connect(db_path)
    added = unchanged = invalid = 0
    try:
        known = {row[0]: (row[1], row[2]) for row in db.execute(
            "SELECT path, size_bytes, mtime_ns FROM replays")}
        for path in sorted(discover(roots), key=lambda p: (p.stat().st_mtime_ns, str(p))):
            stat = path.stat()
            key = str(path)
            if known.get(key) == (stat.st_size, stat.st_mtime_ns):
                unchanged += 1
                continue
            try:
                meta = _metadata(path)
                digest = _digest(path)
            except (OSError, ValueError, json.JSONDecodeError, gzip.BadGzipFile) as exc:
                invalid += 1
                print(f"skip invalid replay {path}: {exc}")
                continue
            db.execute("DELETE FROM replays WHERE path = ? AND sha256 != ?", (key, digest))
            db.execute("""
                INSERT OR REPLACE INTO replays
                (sha256,path,source,size_bytes,mtime_ns,steps,agents_json,
                 final_money_json,seed,indexed_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                digest, key, source_for(path), stat.st_size, stat.st_mtime_ns,
                meta["steps"], json.dumps(meta["agents"]),
                json.dumps(meta["final_money"]), str(meta["seed"] or ""),
                datetime.now(timezone.utc).isoformat(),
            ))
            added += 1
            db.commit()
            if added % 25 == 0:
                print(f"indexed {added} new replays ...", flush=True)
            if max_new and added >= max_new:
                break
        db.commit()
        total = db.execute("SELECT COUNT(*) FROM replays").fetchone()[0]
    finally:
        db.close()
    return {"added": added, "unchanged": unchanged, "invalid": invalid,
            "total": total, "database": str(db_path)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("roots", nargs="*", default=[
        "replays", "compete_runs", "benchmark_replays", "tournament_replays"])
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--max-new", type=int, default=0,
                    help="index at most this many new/changed files (0 = unlimited)")
    args = ap.parse_args()
    roots = [(ROOT / p).resolve() if not Path(p).is_absolute() else Path(p) for p in args.roots]
    print(json.dumps(update_index(roots, Path(args.db), args.max_new), indent=2))


if __name__ == "__main__":
    main()
