# auto_improve.py — autonomous improve-then-compete loop

`tools/auto_improve.py` runs the agent through `compete.py`, and whenever it is
below target it hands the replay/log diagnosis to an LLM that researches, plans,
and makes one change to `main_auto.py` — then loops. Fully unattended.

**v2:** the first run (`tools/auto_improve_runs/20260904-052919`) plateaued at
79.2% after iteration 2 and never moved again — see
`tools/PLAN_AUTO_IMPROVE_V2.md` for the diagnosis (a frozen-seed accept/reject
signal inside its own noise band, a shut-out opponent cluster hidden by the
overall score-rate, and one bad run that burned 5 iterations on a fallback
driver with no API key). The flags and behavior below marked **(v2)**
implement that plan's "minimal first cut."

**Not the same thing as `ml/loop.py`.** That's a separate, independently-built
supervisor: it optimizes an engine-config/policy search over downloaded ladder
replays and never touches `main_auto.py`/`main.py`. This script instead drives
`compete.py` locally and hands an LLM the diagnosis to hand-edit
`main_auto.py`. Both are currently kept — see `ml/README.md`'s "Continuous
learning supervisor" section for the other one.

## What it does per iteration

1. **Evaluate** `main_auto.py` with `compete.py --games N`. **(v2)** The
   search-phase seed rotates every iteration (`--pick-seed +
   --search-seed-stride*(iter+1)`) so the loop isn't graded on the same frozen
   matchups round after round; `--pick-seed` itself is reserved, fixed, for
   the once-only `main.py` baseline and the fresh-seed success verification —
   a held-out check the search phase never sees.
2. **Decide** — success = candidate score ≥ `--target` **and** ≥ baseline +
   `--baseline-edge` **and** 0 errors **and** it survives a fresh-seed
   `--verify-games` run. Otherwise a fix is due. **(v2)** Best-tracking itself
   ranks candidates by `(worst single-opponent score-rate, overall score-rate,
   margin)`, not overall score-rate alone — a change that lifts a shut-out
   matchup (opponent score-rate ~0%, invisible in an overall-score average) now
   counts as a new best even when the headline score doesn't move.
3. **Diagnose** — `tools/analyze_runs.py` on the run archive + the 3 worst
   losing games' `*.replay.json.gz` / `*.logs.json` paths.
4. **Fix** — a fresh LLM chat gets the diagnosis, the losing-game pointers, the
   `main_auto.py`-vs-`main.py` diff, and a digest of prior iterations (the run
   `LEDGER.md` + `LESSONS.md`). It must research (`knowledge-base/`, env source,
   `experiments/LEDGER.md`), write a one-paragraph plan into the LEDGER, and make
   **one** change to `main_auto.py`. **(v2)** Exception: if the diagnosis shows a
   *coordinated* deficit across ≥2 systems moving together (the exact shape that
   made every single-lever fix in run 1 either no-op or regress), it may make up
   to 3 justified, individually-explained changes in one iteration and marks the
   iteration `"combo": true`. If `--focus-pool` + `--curriculum-at` are set and
   the candidate has cleared the threshold on the full pool, the prompt also
   carries an extra diagnosis run against just the focus pool (scoring/best-
   tracking never switches off the full pool — this only sharpens what the
   fixer sees).
5. **Guard** — any edit outside `main_auto.py` is reverted from a pre-fix
   backup; the file is import/parse-checked; a 1-game `--debug` canary runs. On
   any failure `main_auto.py` is rolled back to the best snapshot.
6. Repeat. **(v2)** One iteration before `--patience` would exhaust with no new
   best, and only if `--reseed-pool` was given, `main_auto.py` is auto-reseeded
   from the next untried file in that list (a different lineage agent) instead
   of just stopping — a different starting basin on the same iteration budget.

`main.py` is never touched. Nothing is submitted to Kaggle. The best snapshot is
`tools/auto_improve_runs/<stamp>/best.py`; promote it yourself after your own
A/B.

## LLM drivers

- `--driver claude` (default) — shells out to `claude` headless
  (`-p --output-format json --dangerously-skip-permissions`, prompt on stdin).
  Uses your Claude Code plan quota. The binary is auto-located
  (`CLAUDE_CODE_EXECPATH`, `PATH`, the VS Code extension); override with
  `--claude-bin`.
- `--driver openai` — a minimal agentic tool loop over the OpenAI chat API
  (`read_file` / `run_bash` (read-only) / `write_file` (allow-listed) / `finish`).
  Needs `OPENAI_API_KEY`; model via `--openai-model` or `$OPENAI_MODEL`. Beta —
  less battle-tested than the Claude driver.
- `--fallback-driver` (default `openai`) — when the primary reports a usage /
  rate / quota limit, the loop switches drivers **for the rest of the run** and
  retries the current iteration once. **(v2)** Before that: (a) a startup
  preflight disables the fallback up front (prints why) if it's `openai` and
  `OPENAI_API_KEY` isn't set — the exact failure mode that burned run 2's
  entire budget on 5 iterations of `FAILED: OPENAI_API_KEY not set`; (b) a
  usage-limit error retries the *same* driver with exponential backoff
  (`--usage-limit-retries`, `--usage-limit-backoff`) before switching driver or
  giving up, since usage limits often clear within the hour.

Each iteration is a brand-new chat — continuity is the LEDGER digest passed into
the prompt, never a growing conversation. `LESSONS.md` is the fixer's own
running list of dead ends / env facts and is fed back every iteration.

## Run it

```bash
# typical: 15 iterations or 12h, target 58% vs the full pool, sharded for a firmer signal
python tools/auto_improve.py --games 200 --workers 6 --target 0.58 --max-iters 15 --max-hours 12

# curriculum: sharpen the diagnosis on the losing cluster once score clears 72%,
# and hop to a different lineage file if patience nearly runs out
python tools/auto_improve.py --games 200 --workers 6 --target 0.6 --max-iters 20 --patience 8 \
    --focus-pool c_v5clone main_p3 main_v5 main_v6 main_v7 c_animalfactory \
    --curriculum-at 0.72 \
    --reseed-pool agents/main_v11.py main_herdbatch.py

# quick shakedown (few games, cheap)
python tools/auto_improve.py --games 20 --verify-games 12 --target 0.6 --max-iters 3

# see the prompt for iteration 0 and stop before any edit
python tools/auto_improve.py --games 40 --dry-run

# OpenAI as primary
OPENAI_API_KEY=sk-... python tools/auto_improve.py --driver openai --openai-model gpt-4o ...

# resume an interrupted run (re-uses baseline, iteration counter, best snapshot)
python tools/auto_improve.py --resume tools/auto_improve_runs/20260904-120000
```

Stop conditions (whichever first): target met + verified, `--max-iters`,
`--max-hours`, `--patience` iterations with no new best, or a `STOP` file dropped
in the run directory.

## Key flags

| flag | default | meaning |
|---|---|---|
| `--games` | 200 | games per search-phase evaluation (raise with `--workers`) |
| `--workers` | 1 | **(v2)** parallel `compete.py` worker processes (passed through) |
| `--search-seed-stride` | 9973 | **(v2)** search-eval seed = `pick-seed + stride*(iter+1)`; `--pick-seed` stays fixed for baseline/verify |
| `--verify-games` | 80 | fresh-seed games before declaring success |
| `--target` | 0.58 | score-rate target (0–1) |
| `--baseline-edge` | 0.0 | required score margin over `main.py` |
| `--max-iters` | 15 | iteration cap |
| `--max-hours` | 12 | wall-clock cap |
| `--patience` | 5 | stop after N iters with no new best (delayed one round if `--reseed-pool` fires first) |
| `--regress-tol` | 0.02 | restore `best.py` as the fix base when the candidate's overall score drifts this far below best's; also the verify slack |
| `--pick-seed` | 20260904 | fixed selection seed, now reserved for the baseline + fresh-seed verification (held-out; search no longer uses it directly) |
| `--pool …` | full pool | passed to `compete.py --pool` for **scoring** (lineage agents are still appended unless you also wire `--exclude-lineage` into `compete.py`) |
| `--focus-pool …` | none | **(v2)** opponent subset for an extra diagnosis-only eval once `--curriculum-at` is cleared on the full pool |
| `--curriculum-at` | none | **(v2)** full-pool score-rate (0–1) that activates `--focus-pool` |
| `--focus-games` | `games // 2` | **(v2)** games for the focus-pool diagnosis eval |
| `--reseed-pool …` | none | **(v2)** alternate seed-from files auto-tried, one per near-patience-exhaustion, instead of stopping |
| `--usage-limit-retries` | 3 | **(v2)** same-driver retries with backoff before falling back / stopping |
| `--usage-limit-backoff` | 300 | **(v2)** base backoff seconds (doubles each retry, capped at 3600s) |
| `--seed-from` | `main.py` | file `main_auto.py` is created from when absent |
| `--python` | this interpreter | Python used for `compete.py` / `analyze_runs.py` |

## Run directory

```
tools/auto_improve_runs/<stamp>/
  state.json            # resumable: baseline, iter, best_key (3-tuple, v2),
                         # best_metrics, driver, reseed_tried, elapsed
  LEDGER.md             # one section per iteration (plan + change + result),
                         # plus AUTO-RESEED sections when --reseed-pool fires
  LESSONS.md            # fixer-maintained dead-ends / env facts
  best.py               # best main_auto.py seen so far (ranked worst_opp, score, margin)
  iter_NN/
    prompt.txt          candidate_metrics.json  analysis.txt
    focus_metrics.json  focus_analysis.txt      # only when curriculum fired this iter
    verify_metrics.json                         # only on a target-met iteration
    main_auto.pre.py / .post.py / .kept.py
    driver_stdout.json  driver_result.json  backup/
```

`state.json`'s `best_key` is now a 3-tuple `[worst_opp_rate, score, margin]`
(v2); resuming a pre-v2 run dir prints a note and resets best-tracking rather
than misreading the old 2-tuple (`best.py` on disk is untouched either way).

## Guardrails / caveats

- **Don't edit the repo while a run is live** — the stray-edit guard restores any
  tracked file the fixer changed (including files you had uncommitted) from its
  pre-fix backup, and deletes new untracked files outside the run dir.
- The loop **seeds from the current working-tree `main.py`**. If that file is a
  broken WIP, the loop starts from broken. Check `git diff main.py` first, or
  point `--seed-from` at a known-good snapshot (`agents/main_v10.py`).
- `compete.py` cannot gate a `main.py` economy change (see `CLAUDE.md`
  "Benchmarking notes"). A local score win here is a *candidate signal*, not a
  promote decision — always A/B `best.py` yourself and submit manually. The
  SUCCESS ledger entry and stdout both now say this out loud.
- The Claude driver runs with `--dangerously-skip-permissions`; the revert guard
  is the safety net. Run it in this repo only.
- `--workers > 1` runs games in separate processes; the match sequence for a
  given `--pick-seed`/search seed is unchanged (opponent/seed/seat are drawn
  single-threaded first), only the wall-clock cost drops.
- A `--usage-limit-backoff`-driven sleep can hold the process for up to an hour
  per retry; that's intentional for an unattended run, but don't expect a quick
  `Ctrl-C` turnaround while it's waiting.
- Suggested `.gitignore` additions: `main_auto.py`, `tools/auto_improve_runs/`.
```
