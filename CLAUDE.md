# CLAUDE.md

Guidance for Claude Code in this repo. Kept deliberately short — it loads on
every session. Detail lives in `knowledge-base/` (read on demand).

## What this is

Single-agent entry for the **Kaggriculture** Kaggle Simulations competition: a
2-player, 720-turn (30 days × 24 turns) farming/economy game on
`kaggle-environments`. The whole submission is `main.py`, exposing
`agent(obs) -> {"farmer": [...], "hands": [[...], ...], "market": [[...], ...]}`.
Reward is `farm["money"]`; rating is Bradley-Terry over win/loss/tie only —
margin is discarded. Deadline **2026-09-30**.

## Start here every session

1. `TASKS.md` — live submission-slot state, ranked queue, shared work board.
   Claim a row (with the files you'll own) before editing code; update it in the
   same sitting as any action it lists. Re-read it + `experiments/LEDGER.md`
   right before writing either.
2. `knowledge-base/INDEX.md` — one-screen cheat sheet, then the matched file.
   `knowledge-base/04-engine-internals.md` is authoritative for any ambiguous
   mechanic. `07-codebase-and-workflow.md` = file map + pipeline walkthrough.
3. `docs/LADDER_RUNBOOK.md` — the execution loop (teardown → one flagged change
   → local-gate → queue → judge), run via `/ladder`. Its State table is the
   live slot status.

Codex may share this working tree — follow the handoff protocol in
`docs/PLAN_TO_3000.md`; don't touch another active row's owned files.

## Workflow rules — do not deviate

Repeated lessons from the ladder record; they override the "try lots of things"
instinct.

- **One atomic, `ENABLE_*`-flagged change per submission. Never bundle.**
  Bundled subs can't be attributed.
- **Judge only after ≥20 ladder episodes; never revert before ≥15.**
  Sub-episode reads have burned us.
- **Gate metric = win-rate (score-rate) vs `animal_factory`.** Not mean, not
  margin. It's ~56% of ladder games and the worst matchup, so
  `bots/bot_animalfactory_v2.py` carries extra weight in the local pool.
- **Prefer mechanical / efficiency / bug fixes over economy or crop tuning.**
  The only changes that ever moved the ladder were mechanical (feed-floor bug
  fix →574.6; routing + MAXHANDS-12 →605.1). Every economy/crop tweak failed to
  gate or was reverted.
- **Rule out an `agent()` exception first** on any flat/losing episode — a
  silent raise looks identical to a bad strategy.
- **No new local tooling, no new bots, no new `PLAN_*.md` files.** `ml/` is
  frozen until after 2026-09-30. Local eval only catches large regressions vs
  trivial bots — that's its ceiling (confirmed v6/v8/v8b/PLAN_300K).
- **~6-8 clean `main`-slot reads remain.** Spend them on ranked high-EV changes
  only.

## Submission caps & auto-submit (2026-09-09)

- **≤5 submissions per calendar day** across all slugs/models combined;
  **≤4 of those experiment agents**, released as 2 batches of 2 ~12h apart
  (Kaggle tracks only the latest 2 subs).
- Only the promoted `main.py` goes to the real `kaggriculture` slug — never
  `agents/main_v*.py`, `main_auto.py`, or ML probes.
- **Auto-submit is GRANTED** for locally-gated candidates (no per-sub
  approval). Preconditions: local gate clean (never-raise + **0 `agent()`
  errors** + no regression vs `animal_factory` win-rate), caps respected, and
  the **rating-floor guard** — don't submit if it leaves both tracked slots
  below the all-time peak (605.1 / `56044961`) with no candidate proven better
  at ≥20 eps. Post the sub id after submitting.

## Constraints the agent must respect

- **~1s wall-clock per `agent()` call.** `main.py` runs ~4ms/step; keep it there.
- **Never raise.** Top-level try/except falls back to all `PASS`; a silent
  exception is indistinguishable from a bad strategy in the replay.
- **≤10 market orders/turn** (`maxMarketOrdersPerTurn`); extras dropped
  silently — assemble orders priority-sorted.
- Observation has `day`/`hour`, **not** `step`. Shop names in
  `town.unlocked_shops` are `UPPER_SNAKE` (`PIZZA_SHOP`).

## Commands

Setup (pygame won't build on 3.14):
`pip install --no-deps kaggle-environments jsonschema kaggle`. Env math is
authoritative at `kaggle_environments/envs/kaggriculture/kaggriculture.py` in
the installed package.

```bash
python compete.py --games 120                 # ladder-like gate; archives to compete_runs/<stamp>/
python tools/analyze_runs.py --last 2 --json summary.json --csv games.csv   # per-archetype W/T/L, always via --json/--csv
python test.py --games 40 --candidate main.py --incumbent agents/main_v10.py # tight A/B on one hypothesis
kaggle competitions submit kaggriculture -f main.py -m "msg"
```

Full command reference: `AGENTS.md`. Real-ladder replay analysis:
`tools/ladder_analyze.py <sub>` after `download_episodes.py` (run with 3.13).

## Token economy — work cheaply in this repo

Running out of plan tokens is mostly structural here. Follow these:

- **Never `Read` raw episode data.** `replays/`, `logs/`, `episodes/`,
  `compete_runs/**/*.replay.json.gz`, `*.logs.json` — one file can be
  50–200k tokens. Always run `analyze_runs.py --json summary.json --csv
  games.csv` / `ladder_analyze.py <sub>` and read the compact output. To
  inspect one game use `probe_game.py` or grep a field — never the gz.
- **Grep/Glob before Read.** Then `Read` with `offset`/`limit`, not whole
  files. Don't re-read a file you just edited.
- **`/clear` between unrelated tasks.** A long debug session then a submission
  = you pay the debug tokens on every later call.
- **Cap the `/loop` & `/ladder-auto` rolling summary at ~15 lines** (sub id +
  ep count, last judged read, ≤3-item queue, what's benched) — not a
  narrative. Run 1–3 iterations, then `/clear`. Between a submit and its
  20-ep readback there is nothing to do — end the session.
- **Use `/model haiku`** for readbacks, submissions, `LEDGER`/`TASKS` edits,
  running the gate. Reserve Sonnet for strategy design / debugging.
- **Offload broad searches to a subagent** (Explore / general-purpose) — it
  burns its own context and returns only the conclusion.
- **No MCP servers are needed here** — keep them disabled in
  `.claude/settings.json`.
- **Log spend** to `experiments/TOKENS.md` (`tools/token_report.py`) each
  session so the expensive activity is visible.

## File map (essentials)

- `main.py` — the promoted submission. Forks at repo root: `main_herdbatch.py`,
  `main_ml.py`, `main_ai.py`.
- `agents/main_v*.py`, `agents/main_p*.py` — version lineage; `compete.py` pool
  opponents + `test.py` incumbents. Every agent change goes into a **new**
  versioned file — never overwrite a snapshot.
- `bots/` — opponent archetypes on `bots/_kagri_botlib.py`. `contenders/` — a
  second set on `contenders/_engine.py`.
- `compete.py` → `compete_runs/<stamp>/`; `tools/analyze_runs.py` reduces it.
  `tools/ladder_analyze.py` / `classify_ladder.py` / `probe_game.py` /
  `early_probe.py` — real-ladder replay analysis. `test.py` — paired A/B.
  `local.py` — one-off game. `download_episodes.py` — bulk replay pull (3.13).
- `experiments/LEDGER.md` — one row per version (change → local → ladder →
  status). `experiments/TOKENS.md` — per-session token spend.
- `knowledge-base/` — consolidated game/strategy/workflow reference (start at
  `INDEX.md`). `AGENTS.md` — Kaggle CLI workflow. `README.md` / `README_2.md` /
  `how to play.md` — full rules.
- `docs/` — strategy plans. Authoritative: `IMPACT_RANKED_LEADERBOARD_PLAN.md`,
  `PLAN_TO_3000.md`, `PLAN_LADDER_ECON.md`. Older plans kept as rollback
  history.
- `ml/` — frozen until after 2026-09-30.
- `PUBLIC_AGENT_STRATEGY_CATALOG.md` — competitor mechanisms, **ideas-only**:
  never copy/clone/adapt competitor source; re-derive from engine rules and
  gate like any candidate.

## Agent architecture & economics

Not repeated here — the prose drifted out of sync. Read:
`knowledge-base/07-codebase-and-workflow.md` (the `agent()` pipeline:
`make_zones` → animal crew → `build_tasks`/`add_plant_tasks` → `assign` →
`market_orders`), `knowledge-base/03-market-and-economy.md` and
`06-strategy-playbook.md` (market barely moves; lean into TOMATO/STRAWBERRY;
hard-cap MELON/CARROT; spread MILK/WOOL/FERTILIZER sales; end-of-day
auto-drops to shed). Lineage / ladder history: `experiments/LEDGER.md`.
