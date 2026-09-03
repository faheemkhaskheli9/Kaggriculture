# 07 — Codebase & workflow

## File map

| Path | What |
|---|---|
| `main.py` | **The submission.** Current agent, "v5" (v3 zoned core + v4 animal module + throughput bundle + sharp endgame). |
| `main_v1.py` | Gen A snapshot (ladder 332.9): 6 hands, carrot-heavy, 1 land buy, no animals. Has the shop-name lookup bug. Kept as a regression opponent. |
| `main_600.py` | The "v2" baseline the improvement plans dissect; scored 600 seed on the ladder (unearned). Shop-name bug. *(May not be present in every checkout.)* |
| `main_v2.py`…`main_v5.py` | Promoted-snapshot lineage, kept as regression opponents. `main_v5.py` = the pre-throughput-bundle snapshot; it is `test.py`'s default `--incumbent`. |
| `main_p2.py` | Strict fork of an earlier `main.py` with only the endgame change; its endgame is now folded into `main.py` v5. |
| `main_p3.py` | Later experimental fork. |
| `bots/` | Local opponent archetypes — `bot_wheatflood.py`, `bot_animalfarm.py`, `bot_melonmono.py`, `bot_premium.py`, built on `bots/_kagri_botlib.py` (`make_agent(config)` — a shared zoned multi-unit engine parameterised by quadrant target, hire schedule, crop mix, animal mix, sell caps). Run via `test.py --suite`. |
| `local.py` | One-off single local game (edit the file to change opponents/config). |
| `test.py` | **The regression gate.** Paired benchmark, alternating seats. See below. |
| `download_episodes.py` | Bulk/incremental pull of every submission's ladder replays + logs → `replays/`, `logs/`, `episodes/`. |
| `AGENTS.md` | Getting-started + full Kaggle CLI workflow. |
| `README_2.md` / `how to play.md` / `readme.md` | Official game rules / narrative / competition blurb. |
| `PLAN_3000.md`, `PLAN_3000_v4.md`, `PLAN_300K.md`, `SCORE_IMPROVEMENT_PLAN.md`, `STRATEGY.md`, `WINNING_PLAN.md` | Strategy analysis / roadmaps. `PLAN_300K.md` is the current thinking; `PLAN_3000_v4.md` has the 30-replay archetype analysis. |
| `replays/`, `logs/`, `episodes/`, `benchmark_replays/` | Downloaded / generated episode data. |
| `commands.txt` | Recent ad-hoc CLI invocations. |
| `knowledge-base/` | This directory. |

## `main.py` (v5) pipeline — inside `agent(obs)`

Stateless turn-by-turn recompute, structured so labour isn't wasted on movement.

1. **`unlocked_cells(me)` + `make_zones(cells, n_units)`** — sweep owned tiles in
   a boustrophedon order, cut into contiguous near-equal **persistent per-unit
   zones**. A unit only leaves its zone for a survival deadline (priority ≥ 9000).
2. **`animal_targets` / `animal_tiles` / `animal_crew_actions`** — a dedicated
   crew (last 1–4 hands, sized to the herd, always leaving ≥ 6 units on crops)
   does what a generic task can't: `FEED` (wheat from the acting unit's own
   inventory), `CARE`, `PLACE`, `BUILD_*`, hauling wheat from the shed.
   `animal_targets` is opponent-conditional (opp ≥ 4 animals by day 7 → COW 3 /
   GOOSE 3 / SHEEP 0, cap 6); freezes new animals after day 17. Gated by
   `USE_ANIMALS = True`. Disbanded on day 29.
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

## `test.py` — the regression gate

```bash
python test.py --games 20                                   # vs starter, random, main_v5.py
python test.py --games 40 --candidate main.py --incumbent main_v5.py
python test.py --games 30 --suite                           # vs bots/ archetypes + starter
python test.py --games 20 --opponents starter bots/bot_wheatflood.py main_v1.py --save-worst 5
```

- Alternates seats (`--games` must be ≥ 2). Built-in opponents by name: `pass`,
  `random`, `starter`. Others are `.py` paths.
- Per-opponent + OVERALL summary: W/T/L, score-rate, coins mean/median/p10/min,
  mean difference, error count, **move%**, **sell/day**, **empty market-slot
  turns**, **terminal unsold**, coins at d10/d20/d29.
- `--save-worst N` dumps the N worst-difference replays to `benchmark_replays/`.

**Promotion gate:** higher paired own-coins mean **and** non-worse p10 **and**
0 non-DONE statuses **and** 0 terminal unsold **and** ≤ 4 ms/step, in **both
seats**. Keep every promoted `main` as a regression opponent. The `bots/` set is
a *floor* (v5 beats them 40-0-0); the discriminating local tests are self-play
and vs `main_p2`/`main_v5` — and even those don't predict the ladder. Read
ladder replays before large strategy changes.

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

## Replay-analysis method (for the next review)

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
