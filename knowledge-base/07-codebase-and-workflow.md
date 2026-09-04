# 07 — Codebase & workflow

## File map

| Path | What |
|---|---|
| `main.py` | **The submission** (promoted agent). Committed @ `45ce7bd` = **v10** (v7 zoned core + P1 day-scaled reserve + F1 herd-match + P2 fertilizer staple + P4 coverage cap). Working tree may carry a WIP `v11` bundle. |
| `main_herdbatch.py` / `main_ml.py` / `main_ai.py` | Candidate forks at repo root. `main_herdbatch.py` = committed v10 + a gated dawn herd-batch bootstrap. |
| `agents/main_v1.py … main_v11.py` | The full promoted/probe lineage. Ladder reads: v1 **332.9**, v2/`main_600` **477.1**. `agents/main_v10.py` = the committed-`main.py` snapshot; it is `test.py`'s default `--incumbent`. `agents/main_p2.py` / `main_p3.py` = endgame / experimental forks. Every file here is a `compete.py` pool opponent. (v1–v2 carry the old shop-name lookup bug.) |
| `bots/` | Hand-written opponent archetypes — `bot_animalfactory_v2` (the ladder-representative hard counter: WHEAT sold every turn as working capital → 18-head herd + free fertilizer), `bot_animalfarm`, `bot_wheatflood`, `bot_premium`, `bot_melonmono` — on `bots/_kagri_botlib.py` (`make_agent(config)`: shared zoned multi-unit engine parameterised by quadrant target, hire schedule, crop/animal mix, sell caps). |
| `contenders/` | A second archetype set (`c_animalfactory`, `c_premium`, `c_v5clone`, `c_wheatflood`) on `contenders/_engine.py`. In the `compete.py` default pool. |
| `compete.py` | **The ladder-like gate.** See below. Archives to `compete_runs/<stamp>/`. |
| `tools/analyze_runs.py` | **The results/replay/log analysis pipeline** over `compete_runs/`. See below. |
| `tools/ladder_analyze.py` | Per-submission **real-ladder** replay analysis (reads `episodes/index.csv` + `replays/`). `tools/classify_ladder.py`, `probe_game.py`, `early_probe.py` — narrower ladder probes. `tools/token_report.py` — session token accounting. |
| `test.py` | Older paired seat-alternating A/B (fixed opponent list, shared per-pair seeds). Tight single-hypothesis comparisons; **not** the ladder model. |
| `local.py` | One-off single local game (edit the file for opponents/config). |
| `download_episodes.py` | Bulk/incremental pull of every submission's ladder replays + logs → `replays/`, `logs/`, `episodes/`. `download_top_replays.py` — top-of-leaderboard replays. |
| `experiments/LEDGER.md` | One row per agent version: the single change, local numbers, ladder read, promoted/reverted/pending. `experiments/TOKENS.md` — per-session token spend. |
| `ml/` | Optuna → CMA-ES engine-config search + IL/self-play scaffolding. `ml/loop.py` is a supervisor that **never submits or overwrites `main.py`**; challengers export to `ml/artifacts/`. |
| `docs/` | Strategy plans. Current: `docs/PLAN_LADDER_V10.md` (ladder-gated fix sequence P0–P5), `docs/PLAN_LADDER_ECON.md` (75-replay archetype sweep — the mid-game cash-crater diagnosis), `docs/PLAN_3000.md` / `PLAN_300K.md` (coin-ceiling analysis), `docs/PLAN_V6.md` (wedge-zone root-cause). |
| `AGENTS.md` | Getting-started + full Kaggle CLI workflow. |
| `README_2.md` / `how to play.md` / `readme.md` | Official game rules / narrative / competition blurb. |
| `replays/`, `logs/`, `episodes/`, `compete_runs/`, `benchmark_replays/` | Downloaded / generated episode data. |
| `commands.txt` | Recent ad-hoc CLI invocations. |
| `knowledge-base/` | This directory. |

## `main.py` (v10) pipeline — inside `agent(obs)`

Stateless turn-by-turn recompute, structured so labour isn't wasted on movement.
The v3→v7 zoned core below is unchanged; v10 adds P1 (day-scaled working-capital
`reserve`), F1 (herd-**match** vs an animal opponent, not crouch), P2 (FERTILIZER
treated as a staple sell) and P4 (Q4 land gated on crew ≥ 12; total plants capped
at `crop_units·8`).

1. **`unlocked_cells(me)` + `make_zones(cells, n_units)`** — sweep owned tiles in
   a boustrophedon order, cut into contiguous near-equal **persistent per-unit
   zones**. A unit only leaves its zone for a survival deadline (priority ≥ 9000).
2. **`animal_targets` / `animal_tiles` / `animal_crew_actions`** — a dedicated
   crew (last 1–4 hands, sized to the herd, always leaving ≥ 6 units on crops)
   does what a generic task can't: `FEED` (wheat from the acting unit's own
   inventory), `CARE`, `PLACE`, `BUILD_*`, hauling wheat from the shed.
   `animal_targets` is opponent-conditional — **v10 F1**: vs an animal-heavy opp
   it now *matches* the herd (COW 5 / GOOSE 5 / SHEEP 1) to claim its own free
   fertilizer line (1/animal/day, EGG/FERTILIZER never crash under a dump)
   rather than crouching to cap 6. Freezes new animals after day 17. Gated by
   `USE_ANIMALS = True`. Disbanded on day 29. (`main_herdbatch.py` adds a dawn
   BATCH bootstrap so the matched herd is bought in days, not one-per-turn.)
3. **`build_tasks` + `add_plant_tasks`** — emit `(priority, (x,y), action)`
   tuples over the whole farm: watering (dying-plant 10000+ / yield-window 6200+
   / comfort 2600), harvest (3200–5200), `COLLECT_FERTILIZER` (2700, any unit),
   weeds (1500), fill-every-serviceable-tile planting (1800, throttled only if
   unwatered plants exceed `n_units·22`). `choose_crops` picks the mix (has an
   `early = day < 7` week-1 front-load branch — see `06 §3`).
4. **`assign`** — priority-sorted greedy assignment. Pass 0: critical work
   (priority ≥ 9000) → globally-nearest free unit. Then per-unit:
   `eff = pr + 2000·[on-tile] + 150·[in-zone] − 25·dist`, zone-restricted first,
   then a global pass. Endgame drop logic (day 29 h7 / day 28 h19). Idle units
   creep toward pending work.
5. **`market_orders`** — `price_at` reimplements the env price curve; each `SELL`
   is sized against it (grow while marginal unit ≥ 0.72×base staple / 0.80×base
   premium; contested MILK/WOOL/FERTILIZER capped 8/turn and skipped below
   0.5×base; full dump from day 28). 10 slots filled by priority: dawn `HIRE` →
   top-3 `SELL` → land / animal / feed `BUY_PRODUCT` → seeds → remaining sells
   (day ≥ 29: every slot is the terminal dump).

Constants at the top: `CROPS`, `ONE_TIME`, `BASE`, `MKT`, `SHOPS`, `SHED_TILES`,
`PREMIUM`, `USE_ANIMALS`, `ANIMALS` — all tuned to this env's economics
(see `03` before changing them).

## `compete.py` — the ladder-like gate

Models one real-ladder game as closely as `kaggle-environments` allows: opponent
drawn at random from a pool, random 9-digit seed, random seat, stock
competition config (`episodeSteps=720`, `startingMoney=3000`, `actTimeout=1`,
`runTimeout=1200`), `debug=False` so a raised exception is silently swallowed to
all-PASS exactly like Kaggle.

```bash
python compete.py --games 120                               # default pool, fresh opp+seed each
python compete.py --agent main_herdbatch.py --games 120 --pick-seed 4242
python compete.py --opponent bots/bot_animalfactory_v2.py --games 20
python compete.py --pool bots/bot_wheatflood.py starter --games 10 --no-store
python compete.py --exclude-lineage                         # archetypes only, no self-play
```

- Default pool = `bots/` (×5, `bot_animalfactory_v2` weighted for realism) +
  `contenders/` (×4) + every `agents/*.py` + `starter`. `--pool` overrides,
  `--exclude-lineage` drops the `agents/*.py` self-play mirrors.
- `--pick-seed N` makes the whole run (opponent/seat/episode-seed picks)
  reproducible — use the **same** `--pick-seed` across two `--agent` runs for a
  paired comparison.
- Every run (unless `--no-store`) writes `compete_runs/<stamp>/`:
  `manifest.json` + one `*.replay.json.gz` + one `*.logs.json` per game.
- Prints W/T/L + score-rate, coins mean/median/min, margin mean/median/min, and
  a per-opponent W/T/L + mean-margin table.

## `tools/analyze_runs.py` — results / replay / log pipeline

Reduces one or more `compete_runs/` archives to scalars (one replay opened,
reduced, freed at a time — low memory) and reports the same shape
`tools/ladder_analyze.py` gives for real episodes.

```bash
python tools/analyze_runs.py                                # newest run
python tools/analyze_runs.py 20260904-045703-510895        # a specific stamp
python tools/analyze_runs.py --last 3                       # merge the 3 newest runs
python tools/analyze_runs.py --last 2 --worst 20 --full     # every game, not just worst-N
python tools/analyze_runs.py --compare <stampA> <stampB>    # per-opponent W/T/L + margin diff
python tools/analyze_runs.py --last 2 --json s.json --csv g.csv
```

Report contents:
- **overall** — N, W/T/L, score-rate, coins mean/median/p10/min, margin
  mean/median/min, error count.
- **by opponent** (score-rate ascending) — W/T/L, mean margin, mean coins, move%.
- **by archetype** — same buckets as `ladder_analyze` (`animal_factory`,
  `wheat_flood`, `melon_mono`, `premium`, `passive`, `other`), plus the median
  **lead-flip day** (first day mark our coin lead is lost).
- **diagnostics** — mean move%, plants d10/20/29, weeds29, animals, quads29,
  hires, non-PASS actions.
- **errors** — any game with a non-DONE status, non-empty agent `stderr` (with
  the first snippet), or an unparseable replay.
- **worst-N games** — per-game money-by-day both seats, lead-flip day, plant
  trajectory, animals (ours vs opp), move%, our sells, opp sells, opp day-29 mix.

## `test.py` — tight single-hypothesis A/B

Paired seat-alternating benchmark against a **fixed** opponent list with shared
per-pair seeds. Use it to compare one change against one incumbent; it is *not*
the ladder model (see Benchmarking notes below).

```bash
python test.py --games 40 --candidate main.py --incumbent agents/main_v10.py
python test.py --games 30 --suite                           # vs bots/ archetypes + starter
```

## Why local can't gate a `main.py` economy change

Confirmed repeatedly (v6, v8, v8b, PLAN_300K s1–2): a change is neutral/positive
vs `starter` and every isolated probe yet net-negative vs the active bots, or
the reverse. `bots/` wins are a *floor* the promoted agent clears ~40-0-0. What
local **does** catch: a large regression vs a trivial bot (`starter`/`random`)
is a real bug, not noise (`docs/PLAN_LADDER_V10.md` §3). So: `compete.py` +
`analyze_runs.py` for a sanity read and a per-archetype hypothesis, then the
real gate is a ladder submission — one attributable change at a time, compared
with `ladder_analyze.py` after ~15–20 episodes.

## Kaggle CLI workflow

```bash
kaggle competitions submit kaggriculture -f main.py -m "message"
kaggle competitions submissions kaggriculture                 # note the SUBMISSION_ID
kaggle competitions episodes <SUBMISSION_ID> -v               # CSV
kaggle competitions replay <EPISODE_ID> -p ./replays
kaggle competitions logs <EPISODE_ID> <0|1> -p ./logs
kaggle competitions leaderboard kaggriculture -s
```

Multi-file: `tar -czf submission.tar.gz main.py helper.py …` (main.py at root),
then submit the tar.gz.

## Bulk replay download

`download_episodes.py` pulls every submission's episodes incrementally (on-disk
check + `episodes/manifest.json`): replays → `replays/`, agent logs → `logs/`,
metadata → `episodes/` (`manifest.json`, `index.csv`, per-episode JSON).

**Run it with Python 3.13, not 3.14** (kaggle CLI + auth token only exist there):
```
C:\Users\LENOVO\AppData\Local\Programs\Python\Python313\python.exe download_episodes.py
```
Flags: `--dry-run`, `--refresh` (force re-download), `--skip-validation`,
`--agents 0`. Each episode exposes logs for **only our** agent slot (the other
returns HTTP 403, recorded in `manifest.json > logs_forbidden`, never retried).
The `logs` column in `episodes/index.csv` = the agent index we played as that
game — use it to orient replay analysis.

## Standing iteration loop

1. Make **one** attributable change (its own file if `main.py` is contended;
   note it in `experiments/LEDGER.md`).
2. `python compete.py --agent <file> --games 120 --pick-seed <N>` and the same
   seed for the incumbent → `python tools/analyze_runs.py --compare <new> <inc>`.
   Reject only on a large trivial-bot regression or new errors; otherwise this
   is a sanity read + a per-archetype hypothesis, not a gate.
3. Submit to the ladder (`kaggle competitions submit …`).
4. After ~15–20 episodes: `download_episodes.py`, then
   `python tools/ladder_analyze.py <sub>` — compare the `vs animal_factory` row
   and the median lead-flip day against the previous submission.
5. Update `experiments/LEDGER.md` (promoted / reverted / pending + reason), the
   memory notes, and — when the env, the agent, or the strategy understanding
   moved — this knowledge base.

## Real-ladder replay-analysis method

1. `download_episodes.py` for the delta.
2. Bulk-parse `steps[i][seat]["observation"]["farms"][seat]` at ~7 fractions of
   the game, both seats: `money, #hands, #plants, #weeds, crop Counter,
   animal Counter, unlocked_quadrants`. Tag our seat via `"faheem"` in
   `info.Agents` or `submission_ref` in `episodes/index.csv`.
3. Tally per-seat over the game: `SELL` volume by product, `BUY_*` counts,
   action histogram (move/water/harvest/pass/feed/care/collect) from
   `steps[i][seat]["action"]`.
4. Money-by-day both seats + opponent `SELL` units/day → find the turn the lead
   changed and the days the winner accelerated.
5. Classify the opponent into an archetype (`06 §2`); if new, add a `bots/` file.
6. Compare our fingerprint across submissions to confirm which shipped change
   moved the score.

## Environment setup

```bash
pip install --no-deps kaggle-environments jsonschema kaggle
```
(`kaggle-environments` bundles `pygame`, which won't build on Python 3.14 — hence
`--no-deps`.) Env source of truth:
`kaggle_environments/envs/kaggriculture/kaggriculture.py` in the installed
package (transcribed in `04-engine-internals.md`).
