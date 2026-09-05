"""Autonomous improve-then-compete loop for the Kaggriculture agent.

One iteration:

  1. EVALUATE  `main_auto.py` with `compete.py --games N` (fixed paired seed) and,
     on iteration 0, the committed `main.py` baseline on the same matchups.
  2. DECIDE    stop if the candidate hit the score target AND matches/beats the
     baseline and survives a fresh-seed verification run; otherwise a fix is due.
  3. DIAGNOSE  run `tools/analyze_runs.py` on the run archive and pull the worst
     losing games' replay + log paths.
  4. FIX       hand the diagnosis, the losing-game pointers, and a digest of the
     prior iterations to an LLM driver (`claude` headless by default, OpenAI as
     a fallback when Claude hits a usage limit). The driver researches, writes a
     one-paragraph plan into the run LEDGER, and makes ONE change to
     `main_auto.py`. Every iteration is a fresh chat -- continuity is the LEDGER
     digest, not a growing conversation.
  5. GUARD     revert any stray edit outside `main_auto.py`; parse/import-check
     the file; run a 1-game debug canary. On failure, roll `main_auto.py` back to
     the best-known snapshot.
  6. repeat.

`main.py` is never modified. Nothing is submitted to Kaggle. Accepted snapshots
land in `tools/auto_improve_runs/<stamp>/`.

Usage
-----
    python tools/auto_improve.py --games 200 --workers 6 --target 0.58 --max-iters 15 --max-hours 12
    python tools/auto_improve.py --resume tools/auto_improve_runs/<stamp>
    python tools/auto_improve.py --driver openai --openai-model gpt-4o ...

Stop conditions (whichever first): score target met + baseline-matched + verified,
iteration cap, wall-clock cap, patience (no new best for K iters), or a STOP file
in the run directory.

v2 (see tools/PLAN_AUTO_IMPROVE_V2.md for the diagnosis this responds to):
  - the per-iteration candidate eval rotates its seed (`--pick-seed` itself is
    reserved, fixed, for the baseline + fresh-seed verification) so the search
    isn't graded on the same 120 frozen matchups every round,
  - `--workers` shards `compete.py` games across processes so a firmer
    `--games` count is affordable,
  - best-tracking ranks candidates by (worst single-opponent score-rate,
    overall score-rate, margin) instead of overall score-rate alone, so a
    change that lifts the one shut-out matchup wins even when overall is flat,
  - the fixer may make a justified 2-4 change "combo" edit when the diagnosis
    shows a coordinated multi-system deficit, not just one attributable change,
  - `--focus-pool` + `--curriculum-at` sharpen the diagnosis on just the
    losing cluster once the candidate clears a score threshold on the full
    pool (scoring/best-tracking always stays on the full pool),
  - `--reseed-pool` auto-reseeds `main_auto.py` from an alternate lineage file
    when patience is about to run out, instead of just stopping,
  - a usage-limit failure retries the same driver with backoff before falling
    back / stopping, and the fallback is disabled up front (not discovered
    mid-run) when its credentials are missing.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS_ROOT = ROOT / "tools" / "auto_improve_runs"


def resolve_claude_bin() -> str:
    """Best-effort locate the claude headless binary."""
    env = os.environ.get("CLAUDE_CODE_EXECPATH")
    if env and Path(env).exists():
        return env
    which = shutil.which("claude") or shutil.which("claude.exe")
    if which:
        return which
    for pat in (Path.home() / ".vscode" / "extensions",
                Path(os.environ.get("USERPROFILE", "")) / ".vscode" / "extensions"):
        if pat.exists():
            hits = sorted(pat.glob("anthropic.claude-code-*/resources/native-binary/claude*"))
            if hits:
                return str(hits[-1])
    for cand in (Path.home() / ".local" / "bin" / "claude",
                 Path.home() / ".claude" / "local" / "claude"):
        if cand.exists():
            return str(cand)
    return "claude"


DEFAULT_CLAUDE_BIN = resolve_claude_bin()

ALLOW_PREFIXES = ("tools/auto_improve_runs/",)
ALLOW_EXACT = {"main_auto.py"}


# --------------------------------------------------------------------------- #
# shell helpers
# --------------------------------------------------------------------------- #
def sh(argv, timeout=None, stdin_path=None, check=False):
    """Run argv in ROOT, capture combined output, never raise on non-zero."""
    kw = dict(cwd=str(ROOT), text=True, capture_output=True, timeout=timeout)
    if stdin_path is not None:
        with open(stdin_path, "r", encoding="utf-8") as fh:
            kw["stdin"] = fh
            proc = subprocess.run(list(argv), **kw)
    else:
        proc = subprocess.run(list(argv), **kw)
    if check and proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(map(str, argv))}\n"
                           f"{proc.stdout}\n{proc.stderr}")
    return proc


def git_status_paths():
    """Set of repo-relative POSIX paths git currently reports as changed/untracked.

    `git status --porcelain -z` records a rename/copy as TWO NUL-separated
    chunks: `"XY old_path"` followed by a bare `"new_path"` with no status
    prefix. Treating every chunk uniformly (the old code's `chunk[3:]` on
    each) strips 3 real characters off the new path and can let a renamed
    stray file slip past `is_allowed()` undetected."""
    parts = sh(["git", "status", "--porcelain", "-z"]).stdout.split("\0")
    paths = set()
    i = 0
    while i < len(parts):
        chunk = parts[i]
        i += 1
        if len(chunk) <= 3:
            continue
        status, path = chunk[:2], chunk[3:].strip()
        paths.add(path.replace("\\", "/"))
        if status[0] in "RC" and i < len(parts) and parts[i]:
            paths.add(parts[i].strip().replace("\\", "/"))
            i += 1
    return paths


def is_allowed(rel_posix):
    return rel_posix in ALLOW_EXACT or rel_posix.startswith(ALLOW_PREFIXES)


# --------------------------------------------------------------------------- #
# compete.py evaluation + parsing
# --------------------------------------------------------------------------- #
SUMMARY_RE = re.compile(
    r"W/T/L\s*=\s*(\d+)/(\d+)/(\d+)\s+score=([\d.]+)%\s+(?:crashes=(\d+)\s+)?errors=(\d+)")
COINS_RE = re.compile(r"our coins\s+mean/median/min\s*=\s*(-?\d+)\s*/\s*(-?\d+)\s*/\s*(-?\d+)")
MARGIN_RE = re.compile(r"margin\s+mean/median/min\s*=\s*([+-]?\d+)\s*/\s*([+-]?\d+)\s*/\s*([+-]?\d+)")
PEROPP_RE = re.compile(r"^\s*vs\s+(\S+)\s+(\d+)/(\d+)/(\d+)\s+margin mean=([+-]?\d+)", re.M)


def parse_compete(stdout: str) -> dict:
    m = SUMMARY_RE.search(stdout)
    if not m:
        if "interrupted after" in stdout:
            hint = ("compete.py was interrupted (Ctrl-C) before finishing -- it now "
                     "exits non-zero (130) when that happens, so this parse failure "
                     "shouldn't recur; if it does, an evaluate() caller is swallowing "
                     "that exit code.")
        elif not stdout.strip():
            hint = ("compete.py produced no stdout at all -- check stderr / that the "
                     "python interpreter and compete.py path are correct.")
        else:
            hint = "compete.py ran but printed no 'W/T/L=' summary line (need --games > 1)."
        raise RuntimeError(f"could not parse compete.py summary\n{hint}\n" + stdout[-2000:])
    w, t, l, score, crashes, errs = m.groups()
    res = {
        "wins": int(w), "ties": int(t), "losses": int(l),
        "score": float(score) / 100.0, "errors": int(errs),
        "crashes": int(crashes) if crashes is not None else 0,
        "per_opp": {},
    }
    c = COINS_RE.search(stdout)
    if c:
        res["coins_mean"], res["coins_median"], res["coins_min"] = map(int, c.groups())
    mg = MARGIN_RE.search(stdout)
    if mg:
        res["margin_mean"], res["margin_median"], res["margin_min"] = map(int, mg.groups())
    for opp, ow, ot, ol, omm in PEROPP_RE.findall(stdout):
        res["per_opp"][opp] = {"w": int(ow), "t": int(ot), "l": int(ol), "margin_mean": int(omm)}
    return res


def newest_compete_run(after_ts: float) -> Path | None:
    cand = [p for p in (ROOT / "compete_runs").glob("*") if p.is_dir() and p.stat().st_mtime >= after_ts - 2]
    return max(cand, key=lambda p: p.stat().st_mtime) if cand else None


def evaluate(agent_rel: str, games: int, pick_seed: int, python: str,
             pool_args: list[str], label: str, workers: int = 1) -> tuple[dict, Path | None]:
    t0 = time.time()
    argv = [python, "compete.py", "--agent", agent_rel, "--games", str(games),
            "--pick-seed", str(pick_seed)] + pool_args
    if workers and workers > 1:
        argv += ["--workers", str(workers)]
    proc = sh(argv, timeout=max(1200, games * 30))
    if proc.returncode != 0:
        raise RuntimeError(f"[{label}] compete.py exit {proc.returncode}\n{proc.stdout[-3000:]}\n{proc.stderr[-2000:]}")
    metrics = parse_compete(proc.stdout)
    metrics["label"] = label
    metrics["raw_tail"] = proc.stdout[-4000:]
    return metrics, newest_compete_run(t0)


# --------------------------------------------------------------------------- #
# diagnosis
# --------------------------------------------------------------------------- #
def analysis_report(run_dir: Path, python: str) -> str:
    if run_dir is None:
        return "(no run archive found)"
    proc = sh([python, "tools/analyze_runs.py", str(run_dir), "--worst", "10"], timeout=600)
    return proc.stdout or proc.stderr


def losing_games(run_dir: Path, top: int = 3) -> list[dict]:
    if run_dir is None:
        return []
    mani = run_dir / "manifest.json"
    if not mani.exists():
        return []
    games = json.loads(mani.read_text(encoding="utf-8")).get("games", [])
    losses = [g for g in games if g.get("result") == "LOSS"]
    losses.sort(key=lambda g: g.get("margin", 0))
    return losses[:top]


# --------------------------------------------------------------------------- #
# prompt
# --------------------------------------------------------------------------- #
PROMPT = """\
You are improving a Kaggle Simulations competition agent for the game "Kaggriculture".
This is one iteration of an autonomous loop. Work fast and make exactly ONE
attributable change.

## Hard rules
- Edit ONLY `main_auto.py`. Do NOT touch `main.py`, `agents/`, `bots/`, or any
  other file. The single exception: you may append a short lesson to
  `{lessons_path}`.
- The agent must NEVER raise at runtime (top-level try/except falls back to
  all-PASS -- a silent exception looks identical to a bad strategy).
- <= 10 market orders per turn; observation has `day`/`hour`, not `step`; shop
  names are UPPER_SNAKE.
- Keep `agent()` fast (~4ms/step target, ~1s hard wall per call).
- Prefer ONE attributable change with a clear hypothesis; do not rewrite the
  file. EXCEPTION: if the diagnosis shows a coordinated deficit across >= 2
  systems moving together in lockstep (e.g. herd size AND land count AND
  premium production all lagging together -- a single lever won't move a
  multi-lever gap; check the ledger digest below for levers already declared
  "exhausted" alone), you may make up to 3 coordinated changes in this ONE
  iteration. Justify each one separately in the PLAN and give each its own
  CHANGE line. Do not use this to bundle unrelated opportunistic tweaks.

## Research first (read, do not skip)
- `knowledge-base/INDEX.md` then the file matching this problem; `04-engine-internals.md`
  is authoritative for mechanics.
- `CLAUDE.md` (env economics, benchmarking notes), `experiments/LEDGER.md`
  (what was already tried and reverted -- do NOT repeat a reverted change).
- The env source: `kaggle_environments/envs/kaggriculture/kaggriculture.py`
  in the installed package.
- The current `main_auto.py` and its diff vs `main.py`:
```
{auto_diff}
```

## This iteration's problem
Candidate `main_auto.py` scored **{cand_score:.1%}** ({cand_w}/{cand_t}/{cand_l},
mean margin {cand_margin}) over {games} paired games. Baseline `main.py` scored
**{base_score:.1%}**. Target is **{target:.1%}**.

Worst matchups (per-opponent W/T/L, mean margin):
{per_opp_block}

Dominant losing archetype this round: **{dominant}**
{worst_line}

### Diagnosis (tools/analyze_runs.py)
```
{analysis}
```

### Worst losing games (open these replay + log files with Read/Bash)
{loss_files}

### Digest of prior iterations (LEDGER)
{ledger_digest}

## Your output
1. Append to the run LEDGER at `{ledger_path}` a section:
   `## iter {iter_n} -- <driver>` with: one-paragraph PLAN (hypothesis + the
   exact change), then after editing, a CHANGE line naming the function(s) and
   constants touched.
2. If you learned something reusable (a dead end, an env fact), append one line
   to `{lessons_path}`.
3. Apply the change to `main_auto.py`.
4. End your reply with a single line of JSON:
   `{{"changed": "main_auto.py", "summary": "<= 20 words", "hypothesis": "...", "combo": false}}`
   (set `"combo": true` only if you used the multi-change exception above.)
"""


def worst_opp_entry(cand: dict, min_n: int = 2) -> tuple[str | None, float]:
    """Lowest per-opponent score-rate among opponents with >= min_n games this
    eval (avoids single-game noise); (None, 1.0) if nothing qualifies."""
    best = (None, 1.0)
    for name, v in cand.get("per_opp", {}).items():
        n = v["w"] + v["t"] + v["l"]
        if n >= min_n:
            rate = (v["w"] + 0.5 * v["t"]) / n
            if rate < best[1]:
                best = (name, rate)
    return best


def worst_opp_rate(cand: dict, min_n: int = 2) -> float:
    return worst_opp_entry(cand, min_n)[1]


def build_prompt(iter_n, cand, base, games, target, analysis, losses,
                 ledger_digest, ledger_path, lessons_path, auto_diff) -> str:
    per_opp = sorted(cand.get("per_opp", {}).items(), key=lambda kv: kv[1]["margin_mean"])
    per_opp_block = "\n".join(
        f"  {o:<20} {v['w']}/{v['t']}/{v['l']}  margin {v['margin_mean']:+d}"
        for o, v in per_opp[:8]) or "  (none parsed)"
    dominant = per_opp[0][0] if per_opp else "unknown"
    wname, wrate = worst_opp_entry(cand)
    worst_line = (
        f"Worst single matchup this round: **{wname}** at {wrate:.1%} (n>=2 games) -- "
        f"best-tracking now ranks candidates by this figure first, then overall score, "
        f"so lifting THIS matchup beats a same-or-better overall score with this figure "
        f"unchanged." if wname else
        "Worst single matchup: n/a (no opponent had >=2 games this round)."
    )
    loss_files = "\n".join(
        f"  - {g['opponent']} seed {g['seed']} seat {g['our_seat']} margin {g['margin']:+.0f}\n"
        f"      replay: {g.get('replay','?')}\n      logs:   {g.get('logs','?')}"
        for g in losses) or "  (no losing games archived)"
    return PROMPT.format(
        iter_n=iter_n, games=games, target=target,
        cand_score=cand["score"], cand_w=cand["wins"], cand_t=cand["ties"],
        cand_l=cand["losses"], cand_margin=cand.get("margin_mean", 0),
        base_score=base["score"], per_opp_block=per_opp_block, dominant=dominant,
        worst_line=worst_line,
        analysis=analysis[:16000], loss_files=loss_files,
        ledger_digest=ledger_digest[:10000], ledger_path=ledger_path,
        lessons_path=lessons_path, auto_diff=auto_diff[:10000],
    )


# --------------------------------------------------------------------------- #
# LLM drivers
# --------------------------------------------------------------------------- #
class DriverResult:
    def __init__(self, ok, summary="", raw="", usage_limited=False, error="",
                 cost_usd=None, duration_ms=None, tokens=None):
        self.ok = ok
        self.summary = summary
        self.raw = raw
        self.usage_limited = usage_limited
        self.error = error
        self.cost_usd = cost_usd      # claude headless: from its own JSON, real $
        self.duration_ms = duration_ms
        self.tokens = tokens          # openai fallback: no hardcoded pricing, so
                                       # token count is reported instead of $


USAGE_LIMIT_RE = re.compile(
    r"usage limit|rate limit|rate_limit|quota|overloaded|insufficient_quota|"
    r"429|resource_exhausted|credit balance|too many requests", re.I)


class ClaudeDriver:
    name = "claude"

    def __init__(self, binary, model=None, max_turns=None, timeout=2400):
        self.binary = binary
        self.model = model
        self.max_turns = max_turns
        self.timeout = timeout

    def run_fix(self, prompt: str, iter_dir: Path) -> DriverResult:
        pf = iter_dir / "prompt.txt"
        pf.write_text(prompt, encoding="utf-8")
        argv = [self.binary, "-p", "--output-format", "json",
                "--dangerously-skip-permissions"]
        if self.model:
            argv += ["--model", self.model]
        if self.max_turns:
            argv += ["--max-turns", str(self.max_turns)]
        try:
            proc = sh(argv, timeout=self.timeout, stdin_path=pf)
        except subprocess.TimeoutExpired:
            return DriverResult(False, error="claude headless timed out")
        (iter_dir / "driver_stdout.json").write_text(proc.stdout or "", encoding="utf-8")
        (iter_dir / "driver_stderr.txt").write_text(proc.stderr or "", encoding="utf-8")
        blob = (proc.stdout or "") + "\n" + (proc.stderr or "")
        if proc.returncode != 0:
            return DriverResult(False, raw=blob[-4000:],
                                usage_limited=bool(USAGE_LIMIT_RE.search(blob)),
                                error=f"claude exit {proc.returncode}")
        try:
            data = json.loads(proc.stdout)
            text = data.get("result", "") if isinstance(data, dict) else str(data)
            is_err = isinstance(data, dict) and data.get("is_error")
            subtype = isinstance(data, dict) and data.get("subtype", "")
            cost_usd = data.get("total_cost_usd") if isinstance(data, dict) else None
            duration_ms = data.get("duration_ms") if isinstance(data, dict) else None
        except json.JSONDecodeError:
            text, is_err, subtype, cost_usd, duration_ms = proc.stdout, False, "", None, None
        if is_err or subtype in ("error_max_turns", "error_during_execution"):
            return DriverResult(False, raw=text[-4000:],
                                usage_limited=bool(USAGE_LIMIT_RE.search(blob)),
                                error=f"claude result error: {subtype}",
                                cost_usd=cost_usd, duration_ms=duration_ms)
        return DriverResult(True, summary=_last_json_line(text) or text[-400:], raw=text,
                            cost_usd=cost_usd, duration_ms=duration_ms)


class OpenAIDriver:
    """Minimal agentic tool loop over the OpenAI chat completions API. Beta:
    less battle-tested than the Claude driver; used mainly as a fallback."""
    name = "openai"

    def __init__(self, model=None, timeout=2400, max_steps=40):
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o")
        self.timeout = timeout
        self.max_steps = max_steps
        self.key = os.environ.get("OPENAI_API_KEY")

    def _call(self, messages, tools):
        import urllib.request
        body = json.dumps({"model": self.model, "messages": messages,
                           "tools": tools, "temperature": 0.2}).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions", data=body,
            headers={"Authorization": f"Bearer {self.key}",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read())

    def run_fix(self, prompt: str, iter_dir: Path) -> DriverResult:
        if not self.key:
            return DriverResult(False, error="OPENAI_API_KEY not set", usage_limited=False)
        import urllib.error
        tools = [
            {"type": "function", "function": {"name": "read_file", "description":
             "Read a repo file (relative path).", "parameters": {"type": "object",
             "properties": {"path": {"type": "string"},
                            "start": {"type": "integer"}, "end": {"type": "integer"}},
             "required": ["path"]}}},
            {"type": "function", "function": {"name": "run_bash", "description":
             "Run a read-only shell command in the repo root (git diff, grep, ls, python -c ...).",
             "parameters": {"type": "object", "properties": {"cmd": {"type": "string"}},
                            "required": ["cmd"]}}},
            {"type": "function", "function": {"name": "write_file", "description":
             "Overwrite a file with full new contents. Only main_auto.py and the "
             "LEDGER/LESSONS files are permitted.", "parameters": {"type": "object",
             "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
             "required": ["path", "content"]}}},
            {"type": "function", "function": {"name": "finish", "description":
             "Call when the change is applied.", "parameters": {"type": "object",
             "properties": {"summary": {"type": "string"}}, "required": ["summary"]}}},
        ]
        messages = [
            {"role": "system", "content": "You are an autonomous coding agent editing a "
             "single Python file in a git repo. Obey the hard rules in the user message. "
             "Research with read_file/run_bash, then write_file, then finish."},
            {"role": "user", "content": prompt},
        ]
        transcript = []
        total_tokens = 0
        try:
            for _ in range(self.max_steps):
                data = self._call(messages, tools)
                total_tokens += (data.get("usage") or {}).get("total_tokens", 0)
                msg = data["choices"][0]["message"]
                messages.append(msg)
                transcript.append(msg)
                calls = msg.get("tool_calls") or []
                if not calls:
                    break
                for call in calls:
                    fn = call["function"]["name"]
                    args = json.loads(call["function"].get("arguments") or "{}")
                    out = self._dispatch(fn, args)
                    messages.append({"role": "tool", "tool_call_id": call["id"],
                                     "content": out[:8000]})
                    if fn == "finish":
                        (iter_dir / "driver_openai.json").write_text(
                            json.dumps(transcript, indent=2)[:200000], encoding="utf-8")
                        return DriverResult(True, summary=args.get("summary", ""),
                                            raw=json.dumps(transcript)[:8000],
                                            tokens=total_tokens)
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            return DriverResult(False, error=f"openai HTTP {e.code}: {detail[:500]}",
                                usage_limited=e.code == 429 or bool(USAGE_LIMIT_RE.search(detail)),
                                tokens=total_tokens)
        except Exception as e:  # noqa: BLE001
            return DriverResult(False, error=f"openai driver: {e!r}", tokens=total_tokens)
        (iter_dir / "driver_openai.json").write_text(
            json.dumps(transcript, indent=2)[:200000], encoding="utf-8")
        return DriverResult(True, summary="(no finish call)", raw=json.dumps(transcript)[:8000],
                            tokens=total_tokens)

    def _dispatch(self, fn, args):
        try:
            if fn == "read_file":
                p = (ROOT / args["path"])
                if not p.exists():
                    return f"not found: {args['path']}"
                lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
                s = max(0, args.get("start", 1) - 1)
                e = args.get("end", min(len(lines), s + 400))
                return "\n".join(lines[s:e])[:12000]
            if fn == "run_bash":
                cmd = args["cmd"]
                if not re.match(r"^\s*(git diff|git log|grep|rg|ls|cat|head|tail|sed -n|"
                                r"python -c|python tools/analyze_runs\.py|find )", cmd):
                    return "command not allowed (read-only subset only)"
                pr = subprocess.run(cmd, cwd=str(ROOT), shell=True, text=True,
                                    capture_output=True, timeout=300)
                return (pr.stdout + pr.stderr)[:12000]
            if fn == "write_file":
                rel = args["path"].replace("\\", "/")
                if not is_allowed(rel):
                    return f"refused: {rel} is not editable (only main_auto.py + run files)"
                dest = ROOT / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(args["content"], encoding="utf-8")
                return f"wrote {rel} ({len(args['content'])} bytes)"
            if fn == "finish":
                return "ok"
        except Exception as e:  # noqa: BLE001
            return f"error: {e!r}"
        return f"unknown tool {fn}"


def _last_json_line(text: str) -> str:
    for line in reversed((text or "").strip().splitlines()):
        line = line.strip().strip("`")
        if line.startswith("{") and line.endswith("}"):
            return line
    return ""


def make_driver(name, args):
    if name == "claude":
        return ClaudeDriver(args.claude_bin, args.claude_model, args.claude_max_turns)
    if name == "openai":
        return OpenAIDriver(args.openai_model)
    raise SystemExit(f"unknown driver {name}")


# --------------------------------------------------------------------------- #
# guardrails
# --------------------------------------------------------------------------- #
def backup_tree(pre_paths: set[str], iter_dir: Path):
    bdir = iter_dir / "backup"
    for rel in pre_paths | {"main.py", "main_auto.py"}:
        src = ROOT / rel
        if src.is_file():
            dst = bdir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    return bdir


def revert_stray(pre_paths: set[str], bdir: Path) -> list[str]:
    reverted = []
    touched = pre_paths | git_status_paths()
    for rel in sorted(touched):
        if is_allowed(rel):
            continue
        live = ROOT / rel
        backup = bdir / rel
        if backup.exists():
            if not live.exists() or live.read_bytes() != backup.read_bytes():
                live.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup, live)
                reverted.append(rel)
        else:
            # No pre-fix backup -- this file was clean (not in pre_paths) before
            # the driver ran, so backup_tree() never copied it. If git tracks it
            # (it existed clean at HEAD), a straight unlink() would PERMANENTLY
            # DELETE a real repo file instead of reverting it -- restore from
            # HEAD instead. Only delete when it's genuinely new/untracked.
            tracked = sh(["git", "ls-files", "--error-unmatch", "--", rel]).returncode == 0
            if tracked:
                sh(["git", "checkout", "--", rel])
                reverted.append(f"{rel} (restored from HEAD)")
            elif live.exists():
                live.unlink()
                reverted.append(f"{rel} (deleted new)")
    return reverted


def candidate_sane(python: str) -> tuple[bool, str]:
    check = ("import importlib.util,sys; "
             "s=importlib.util.spec_from_file_location('m','main_auto.py'); "
             "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
             "assert hasattr(m,'agent'),'no agent()'; print('import-ok')")
    pr = sh([python, "-c", check], timeout=120)
    if pr.returncode != 0 or "import-ok" not in pr.stdout:
        return False, f"import/parse check failed:\n{pr.stdout}\n{pr.stderr}"
    pr = sh([python, "compete.py", "--agent", "main_auto.py", "--games", "1",
             "--no-store", "--debug"], timeout=300)
    if pr.returncode != 0:
        return False, f"1-game canary exit {pr.returncode}:\n{pr.stdout[-2000:]}"
    if re.search(r"Traceback \(most recent call last\)|!ERR", pr.stdout + pr.stderr):
        return False, f"1-game canary surfaced an error:\n{(pr.stdout + pr.stderr)[-2000:]}"
    return True, "ok"


# --------------------------------------------------------------------------- #
# ledger
# --------------------------------------------------------------------------- #
def ledger_digest(ledger: Path, lessons: Path, keep_iters: int = 8) -> str:
    parts = []
    if lessons.exists():
        parts.append("LESSONS:\n" + lessons.read_text(encoding="utf-8").strip())
    if ledger.exists():
        blocks = re.split(r"(?=^## iter )", ledger.read_text(encoding="utf-8"), flags=re.M)
        tail = [b.strip() for b in blocks if b.strip().startswith("## iter")][-keep_iters:]
        parts.append("\n\n".join(tail))
    return "\n\n".join(parts) or "(first iteration -- no history)"


def append_ledger(ledger: Path, text: str):
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write(text.rstrip() + "\n\n")


# --------------------------------------------------------------------------- #
# state
# --------------------------------------------------------------------------- #
def load_state(run_dir: Path) -> dict:
    p = run_dir / "state.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_state(run_dir: Path, state: dict):
    tmp = run_dir / "state.json.tmp"
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(run_dir / "state.json")


def score_key(m: dict) -> tuple:
    """Lexicographic: (worst single-opponent score-rate, overall score-rate,
    margin). A shut-out matchup (see PLAN_AUTO_IMPROVE_V2.md s1.1/P2-#9) can
    sit under a flat-looking overall score-rate forever with the old
    (score, margin) key; ranking the worst matchup first forces the search to
    address it before it can "win" on overall score alone."""
    return (round(worst_opp_rate(m), 4), round(m["score"], 4), m.get("margin_mean", 0))


# --------------------------------------------------------------------------- #
# main loop
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--games", type=int, default=200,
                    help="games per search-phase evaluation (raise this with --workers "
                         "for a firmer accept/reject signal near a plateau)")
    ap.add_argument("--workers", type=int, default=1,
                    help="parallel compete.py worker processes (passed through)")
    ap.add_argument("--search-seed-stride", type=int, default=9973,
                    help="candidate search eval uses pick-seed + stride*(iter+1) each "
                         "iteration so the loop isn't graded on the same frozen matchups "
                         "every round; --pick-seed itself stays fixed for the baseline "
                         "and fresh-seed verification")
    ap.add_argument("--verify-games", type=int, default=80,
                    help="fresh-seed confirmation games before declaring success")
    ap.add_argument("--target", type=float, default=0.58, help="score-rate target (0..1)")
    ap.add_argument("--baseline-edge", type=float, default=0.0,
                    help="candidate must beat main.py score by at least this")
    ap.add_argument("--max-iters", type=int, default=15)
    ap.add_argument("--max-hours", type=float, default=12.0)
    ap.add_argument("--max-cost-usd", type=float, default=None,
                    help="stop once the claude driver's accumulated total_cost_usd "
                         "(from its own JSON output) reaches this; unset = no cap. "
                         "The openai fallback has no hardcoded pricing table so its "
                         "spend is tracked in tokens only and does not count here.")
    ap.add_argument("--patience", type=int, default=5,
                    help="stop after this many iters with no new best")
    ap.add_argument("--regress-tol", type=float, default=0.02,
                    help="restore best snapshot if candidate score drops this far below best")
    ap.add_argument("--pick-seed", type=int, default=20260904,
                    help="fixed RNG seed for opponent/seat/episode selection (paired eval)")
    ap.add_argument("--pool", nargs="+", default=None,
                    help="override compete.py opponent pool (default: full pool); "
                         "scoring/best-tracking always uses this pool, never --focus-pool")
    ap.add_argument("--focus-pool", nargs="+", default=None,
                    help="opponent subset for an EXTRA diagnosis-only eval once the "
                         "candidate clears --curriculum-at on the full pool -- sharpens "
                         "the prompt's read on a losing cluster without changing what "
                         "scoring/best-tracking optimizes")
    ap.add_argument("--curriculum-at", type=float, default=None,
                    help="full-pool score-rate (0..1) that activates --focus-pool")
    ap.add_argument("--focus-games", type=int, default=None,
                    help="games for the focus-pool diagnosis eval (default: --games // 2)")
    ap.add_argument("--reseed-pool", nargs="+", default=None,
                    help="alternate seed-from files (e.g. agents/main_v11.py "
                         "main_herdbatch.py); when patience is one iteration from "
                         "running out, main_auto.py is auto-reseeded from the next "
                         "untried one instead of stopping, to search a different basin")
    ap.add_argument("--usage-limit-retries", type=int, default=3,
                    help="same-driver retries with backoff before falling back / stopping "
                         "on a usage-limit error")
    ap.add_argument("--usage-limit-backoff", type=float, default=300.0,
                    help="base backoff seconds before a usage-limit retry (doubles each "
                         "retry, capped at 3600s)")
    ap.add_argument("--seed-from", default="main.py",
                    help="file to initialise main_auto.py from when absent")
    ap.add_argument("--python", default=sys.executable or "python")
    ap.add_argument("--driver", choices=["claude", "openai"], default="claude")
    ap.add_argument("--fallback-driver", choices=["claude", "openai", "none"], default="openai",
                    help="switch to this when the primary hits a usage limit")
    ap.add_argument("--claude-bin", default=DEFAULT_CLAUDE_BIN)
    ap.add_argument("--claude-model", default=None)
    ap.add_argument("--claude-max-turns", type=int, default=60)
    ap.add_argument("--openai-model", default=None)
    ap.add_argument("--resume", metavar="RUN_DIR", default=None)
    ap.add_argument("--dry-run", action="store_true",
                    help="run one evaluation + diagnosis, build the prompt, skip the fix")
    args = ap.parse_args()

    pool_args = (["--pool", *args.pool] if args.pool else [])

    # ---- preflight ----------------------------------------------------------- #
    # A missing fallback credential used to be discovered mid-run: iterations
    # burned themselves out failing "OPENAI_API_KEY not set" (usage_limited is
    # False for that error, so the old code just kept incrementing `it`).
    # Disable the fallback up front instead so a claude usage-limit goes
    # straight to backoff-retry (--usage-limit-retries) and a clean stop.
    effective_fallback = args.fallback_driver
    if args.fallback_driver == "openai" and args.driver != "openai" \
            and not os.environ.get("OPENAI_API_KEY"):
        print("preflight: --fallback-driver openai requested but OPENAI_API_KEY is not "
              "set -- disabling the fallback for this run. A usage-limit will retry the "
              f"primary driver with backoff ({args.usage_limit_retries}x) and then stop "
              "cleanly instead of burning iterations on a broken fallback.")
        effective_fallback = "none"

    # ---- run dir ----------------------------------------------------------- #
    if args.resume:
        run_dir = Path(args.resume).resolve()
        if not run_dir.exists():
            raise SystemExit(f"resume dir not found: {run_dir}")
    else:
        run_dir = RUNS_ROOT / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir.mkdir(parents=True, exist_ok=False)
    lock = run_dir / "loop.lock"
    if lock.exists():
        raise SystemExit(f"another loop owns {lock} (delete it if stale)")
    lock.write_text(f"pid={os.getpid()} {dt.datetime.now().isoformat()}\n", encoding="utf-8")

    ledger = run_dir / "LEDGER.md"
    lessons = run_dir / "LESSONS.md"
    best_py = run_dir / "best.py"
    auto = ROOT / "main_auto.py"
    state = load_state(run_dir)
    started = state.get("started_at") or dt.datetime.now().isoformat()
    t_start = time.time() - state.get("elapsed_s", 0.0)

    try:
        # ---- seed main_auto.py ------------------------------------------- #
        if not auto.exists():
            src = ROOT / args.seed_from
            if not src.exists():
                raise SystemExit(f"--seed-from not found: {src}")
            shutil.copy2(src, auto)
            print(f"seeded main_auto.py from {args.seed_from}")
        if not ledger.exists():
            ledger.write_text(f"# auto_improve ledger\nstarted {started}\n"
                              f"seed-from {args.seed_from}  pick-seed {args.pick_seed}\n\n",
                              encoding="utf-8")
        if not lessons.exists():
            lessons.write_text("# lessons (reverted dead-ends, env facts)\n\n", encoding="utf-8")

        # ---- baseline (once) ------------------------------------------------ #
        if "baseline" not in state:
            print("== evaluating main.py baseline ==")
            base, _ = evaluate("main.py", args.games, args.pick_seed, args.python,
                               pool_args, "baseline", workers=args.workers)
            state["baseline"] = base
            save_state(run_dir, state)
        base = state["baseline"]
        print(f"baseline main.py: score={base['score']:.1%} "
              f"W/T/L={base['wins']}/{base['ties']}/{base['losses']}")

        driver_name = state.get("driver", args.driver)
        it = state.get("iter", 0)
        raw_best_key = state.get("best_key")
        if raw_best_key and len(raw_best_key) == 3:
            best_score = tuple(raw_best_key)
        else:
            if raw_best_key:
                print(f"note: run dir has a pre-v2 best_key {raw_best_key} (2-tuple) -- "
                      "resetting best-tracking to the new (worst_opp, score, margin) "
                      "schema. best.py is untouched and will be re-adopted as best on "
                      "the next iteration if it still scores well.")
            best_score = (0.0, 0.0, -10**9)
        best_metrics = state.get("best_metrics")
        last_best_iter = state.get("last_best_iter", 0)
        reseed_tried = state.get("reseed_tried", [])
        cost_usd_total = state.get("cost_usd_total", 0.0)
        tokens_total = state.get("tokens_total", 0)

        while True:
            # ---- stop checks ---------------------------------------------- #
            if (run_dir / "STOP").exists():
                print("STOP file present -- exiting"); break
            elapsed_h = (time.time() - t_start) / 3600.0
            if elapsed_h >= args.max_hours:
                print(f"wall-clock cap {args.max_hours}h reached"); break
            if it >= args.max_iters:
                print(f"iteration cap {args.max_iters} reached"); break
            if args.max_cost_usd is not None and cost_usd_total >= args.max_cost_usd:
                print(f"cost cap ${args.max_cost_usd:.2f} reached (spent ${cost_usd_total:.2f})"); break

            # one iteration before patience would exhaust, try an auto-reseed from
            # the next untried --reseed-pool file instead of just stopping -- a
            # different starting basin, same iteration budget (PLAN_AUTO_IMPROVE_V2 P1-#8)
            if (args.reseed_pool and it > 0
                    and it - last_best_iter == max(1, args.patience - 1)
                    and len(reseed_tried) < len(args.reseed_pool)):
                reseed_file = args.reseed_pool[len(reseed_tried)]
                reseed_src = ROOT / reseed_file
                reseed_tried = reseed_tried + [reseed_file]
                if reseed_src.exists():
                    shutil.copy2(reseed_src, auto)
                    last_best_iter = it  # fresh patience budget for the new basin
                    append_ledger(ledger, f"## iter {it} -- AUTO-RESEED\n"
                                  f"No new best for {args.patience - 1} iters (best worst_opp="
                                  f"{best_score[0]:.1%} score={best_score[1]:.1%}); patience "
                                  f"nearly exhausted. Reseeded main_auto.py from `{reseed_file}` "
                                  f"to search a different basin instead of stopping.")
                    print(f"  auto-reseed: patience near exhaustion -> reseeded main_auto.py "
                          f"from {reseed_file}")
                else:
                    print(f"  auto-reseed candidate not found, skipping: {reseed_file}")
                state.update(reseed_tried=reseed_tried)
                save_state(run_dir, state)

            if it - last_best_iter >= args.patience and it > 0:
                print(f"patience {args.patience} exhausted (no new best)"); break

            iter_dir = run_dir / f"iter_{it:02d}"
            iter_dir.mkdir(exist_ok=True)
            print(f"\n===== iter {it}  (driver={driver_name}, elapsed {elapsed_h:.1f}h) =====")

            # ---- evaluate candidate ------------------------------------- #
            # Rotating seed: --pick-seed itself is reserved for the baseline and
            # fresh-seed verification (a held-out check), so the search-phase
            # eval isn't graded on the same frozen 200 matchups every iteration
            # (PLAN_AUTO_IMPROVE_V2 P0-#1).
            search_seed = args.pick_seed + args.search_seed_stride * (it + 1)
            cand, crun = evaluate("main_auto.py", args.games, search_seed,
                                  args.python, pool_args, f"iter{it}", workers=args.workers)
            (iter_dir / "candidate_metrics.json").write_text(json.dumps(cand, indent=2), encoding="utf-8")
            print(f"candidate: score={cand['score']:.1%} "
                  f"W/T/L={cand['wins']}/{cand['ties']}/{cand['losses']} "
                  f"margin_mean={cand.get('margin_mean', 0)} errors={cand['errors']} "
                  f"worst_opp={worst_opp_rate(cand):.1%} (seed={search_seed})")

            # ---- best-so-far bookkeeping -------------------------------- #
            k = score_key(cand)
            if k > best_score:
                best_score = k
                best_metrics = cand
                last_best_iter = it
                shutil.copy2(auto, best_py)
                shutil.copy2(auto, iter_dir / "main_auto.kept.py")
                print(f"  new best: score={cand['score']:.1%} worst_opp={k[0]:.1%}")

            # ---- success? ---------------------------------------------- #
            hit_target = (cand["score"] >= args.target
                          and cand["score"] >= base["score"] + args.baseline_edge
                          and cand["errors"] == 0)
            if hit_target:
                print("target met on paired seed -- running fresh-seed verification")
                vcand, _ = evaluate("main_auto.py", args.verify_games, args.pick_seed + 1,
                                    args.python, pool_args, f"verify{it}", workers=args.workers)
                (iter_dir / "verify_metrics.json").write_text(json.dumps(vcand, indent=2), encoding="utf-8")
                print(f"  verify: score={vcand['score']:.1%} errors={vcand['errors']}")
                if vcand["score"] >= args.target - args.regress_tol and vcand["errors"] == 0:
                    append_ledger(ledger, f"## iter {it} -- SUCCESS\n"
                                  f"paired {cand['score']:.1%} / verify {vcand['score']:.1%} "
                                  f"(target {args.target:.1%}, baseline {base['score']:.1%}). "
                                  f"Run cost so far: ${cost_usd_total:.2f}. "
                                  f"Reminder (CLAUDE.md Benchmarking notes): local compete.py "
                                  f"score is a candidate signal, NOT a promote decision -- A/B "
                                  f"vs main.py yourself and submit manually. Stopping.")
                    state.update(iter=it, driver=driver_name, best_key=list(best_score),
                                 best_metrics=best_metrics, last_best_iter=last_best_iter,
                                 reseed_tried=reseed_tried, elapsed_s=time.time() - t_start,
                                 cost_usd_total=cost_usd_total, tokens_total=tokens_total,
                                 outcome="success", final=cand, verify=vcand)
                    save_state(run_dir, state)
                    print("\n*** SUCCESS -- candidate at", f"{cand['score']:.1%}",
                          "-- snapshot:", best_py)
                    print("*** local score cannot gate a main.py economy change -- "
                          "A/B this snapshot yourself before submitting.")
                    break
                print("  verification failed -- treating as a normal iteration")

            # ---- diagnosis ------------------------------------------------ #
            report = analysis_report(crun, args.python)
            if args.focus_pool and args.curriculum_at is not None \
                    and cand["score"] >= args.curriculum_at:
                fgames = args.focus_games or max(20, args.games // 2)
                print(f"  curriculum: score {cand['score']:.1%} >= "
                      f"{args.curriculum_at:.1%} -- sharpening diagnosis on focus pool "
                      f"({', '.join(args.focus_pool)})")
                try:
                    fcand, frun = evaluate("main_auto.py", fgames, search_seed + 1, args.python,
                                           ["--pool", *args.focus_pool], f"iter{it}-focus",
                                           workers=args.workers)
                    (iter_dir / "focus_metrics.json").write_text(
                        json.dumps(fcand, indent=2), encoding="utf-8")
                    freport = analysis_report(frun, args.python)
                    (iter_dir / "focus_analysis.txt").write_text(freport, encoding="utf-8")
                    report += (
                        f"\n\n### CURRICULUM -- focus-pool diagnosis "
                        f"({', '.join(args.focus_pool)}, {fgames} games, score="
                        f"{fcand['score']:.1%})\nFull pool cleared --curriculum-at "
                        f"{args.curriculum_at:.1%}; here is a sharper read on just the "
                        f"losing cluster (scoring/best-tracking above is still the full "
                        f"pool -- do not optimize only for this):\n```\n{freport}\n```\n"
                    )
                except Exception as e:  # noqa: BLE001
                    print(f"  curriculum focus-pool eval failed, skipping: {e!r}")
            (iter_dir / "analysis.txt").write_text(report, encoding="utf-8")
            losses = losing_games(crun, 3)
            auto_diff = sh(["git", "diff", "--no-index", "--", str(ROOT / args.seed_from),
                            str(auto)]).stdout or "(no diff vs seed)"
            prompt = build_prompt(it, cand, base, args.games, args.target, report, losses,
                                  ledger_digest(ledger, lessons), str(ledger), str(lessons),
                                  auto_diff)
            (iter_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

            if args.dry_run:
                print("dry-run: prompt written, stopping before the fix.")
                break

            # ---- fix ---------------------------------------------------- #
            pre_paths = git_status_paths()
            bdir = backup_tree(pre_paths, iter_dir)
            last_good = iter_dir / "main_auto.pre.py"
            shutil.copy2(auto, last_good)

            def call_driver(d):
                nonlocal cost_usd_total, tokens_total
                r = d.run_fix(prompt, iter_dir)
                if r.cost_usd:
                    cost_usd_total += r.cost_usd
                if r.tokens:
                    tokens_total += r.tokens
                return r

            driver = make_driver(driver_name, args)
            print(f"  invoking {driver.name} ...")
            res = call_driver(driver)

            # Usage limits often reset within minutes-to-an-hour -- retry the
            # SAME driver with backoff before giving up on it (PLAN_AUTO_IMPROVE_V2
            # P4-#17); only switch driver / stop once retries are exhausted.
            retry_i = 0
            while (not res.ok and res.usage_limited
                   and retry_i < args.usage_limit_retries):
                delay = min(3600.0, args.usage_limit_backoff * (2 ** retry_i))
                retry_i += 1
                print(f"  {driver.name} usage-limited -- retry {retry_i}/"
                      f"{args.usage_limit_retries} in {delay:.0f}s ...")
                time.sleep(delay)
                res = call_driver(driver)

            if not res.ok and res.usage_limited and effective_fallback != "none" \
                    and effective_fallback != driver_name:
                print(f"  {driver.name} still usage-limited after {retry_i} retries -> "
                      f"switching to {effective_fallback}")
                with lessons.open("a", encoding="utf-8") as fh:
                    fh.write(f"- iter {it}: {driver.name} usage-limited after {retry_i} "
                             f"retries, switched to {effective_fallback}\n")
                driver_name = effective_fallback
                driver = make_driver(driver_name, args)
                res = call_driver(driver)

            if res.cost_usd:
                print(f"  driver cost this call: ${res.cost_usd:.4f}")
            elif res.tokens:
                print(f"  driver tokens this call: {res.tokens}")
            print(f"  run total so far: ${cost_usd_total:.2f}" +
                  (f" + {tokens_total} openai tokens" if tokens_total else ""))

            # ---- guardrails ------------------------------------------- #
            reverted = revert_stray(pre_paths, bdir)
            if reverted:
                print(f"  reverted stray edits: {reverted}")
            (iter_dir / "driver_result.json").write_text(json.dumps(
                {"ok": res.ok, "usage_limited": res.usage_limited, "error": res.error,
                 "summary": res.summary, "reverted": reverted}, indent=2), encoding="utf-8")

            if not res.ok:
                append_ledger(ledger, f"## iter {it} -- {driver_name} FAILED\n{res.error}\n"
                              f"(no change applied)")
                if not res.usage_limited:
                    it += 1
                    state.update(iter=it, driver=driver_name, best_key=list(best_score),
                                 best_metrics=best_metrics, last_best_iter=last_best_iter,
                                 reseed_tried=reseed_tried, elapsed_s=time.time() - t_start)
                    save_state(run_dir, state)
                    continue
                print(f"  {driver.name} still usage-limited after {retry_i} retries and no "
                      "usable fallback -- stopping")
                break

            sane, why = candidate_sane(args.python)
            if not sane:
                print(f"  candidate rejected: {why.splitlines()[0]}")
                shutil.copy2(best_py if best_py.exists() else last_good, auto)
                append_ledger(ledger, f"## iter {it} -- {driver_name} change REJECTED\n"
                              f"{why[:1500]}\nrolled back to best snapshot.")
            else:
                append_ledger(ledger, f"## iter {it} -- {driver_name} applied\n"
                              f"driver summary: {res.summary[:600]}")
                shutil.copy2(auto, iter_dir / "main_auto.post.py")

            it += 1
            state.update(iter=it, driver=driver_name, best_key=list(best_score),
                         best_metrics=best_metrics, last_best_iter=last_best_iter,
                         reseed_tried=reseed_tried, elapsed_s=time.time() - t_start,
                         baseline=base)
            save_state(run_dir, state)

            # NOTE: a "hill-climb reset" used to live here -- if this iteration's
            # PRE-FIX `cand` scored more than --regress-tol below best_metrics, it
            # copied best.py back over main_auto.py, discarding whatever the driver
            # had just applied a few lines above. Removed: `cand` and `best_metrics`
            # are scores from DIFFERENT search-phase seeds (the seed rotates every
            # iteration on purpose, see --search-seed-stride), so the comparison was
            # noise, not regression -- confirmed from tools/auto_improve_runs/
            # 20260905-081459/LEDGER.md, where the same Q4 land-gate fix was
            # diagnosed and reapplied 4 times (iters 3/5/6/7) because this block
            # silently reverted it each round, freezing last_best_iter at 3 through
            # iter 8. best.py is already insulated from a drifting main_auto.py by
            # the best-tracking + --patience stop condition above, so this block
            # added no safety it didn't already have.

        # ---- wrap up ---------------------------------------------------- #
        if best_py.exists():
            if best_metrics is not None:
                print(f"\nbest snapshot: {best_py}  (score {best_metrics['score']:.1%}, "
                      f"worst_opp {best_score[0]:.1%}, margin {best_score[2]:+d})")
            else:
                print(f"\nbest snapshot: {best_py}")
            print(f"to promote:    cp {best_py} main_auto.py   # then A/B vs main.py yourself")
        state.setdefault("outcome", "stopped")
        state["elapsed_s"] = time.time() - t_start
        save_state(run_dir, state)
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
