# Kaggriculture Knowledge Base

Self-contained reference for the **Kaggriculture** Kaggle Simulations competition:
every rule, every number, the exact engine behaviour, and the distilled strategy
record. Built so a fresh Claude session can come up to speed without re-reading
the whole repo.

## How to use this

1. Skim this page for the cheat-sheet and pick the file(s) that match the task.
2. Read the **full** matched file — the tables and edge-cases matter.
3. `04-engine-internals.md` is authoritative when a mechanic is ambiguous; it is
   transcribed from `kaggle_environments/envs/kaggriculture/kaggriculture.py`.
   If that source and any prose here ever disagree, trust the source and fix the
   file.
4. Strategy is opinionated and evidence-tagged in `06-strategy-playbook.md` —
   treat it as "what we tried and measured", not gospel.

## Files

| File | Contents |
|---|---|
| [01-competition-and-submission.md](01-competition-and-submission.md) | What the contest is, how it's scored (Bradley-Terry, win/loss only), submission format & limits, the `agent(obs)` contract, hard runtime constraints. |
| [02-game-rules.md](02-game-rules.md) | Full rules: board/quadrants, farmer & hands, every farmer op, every market op, crops, animals, watering/feeding/decay/weeds, shed, town shops, turn-processing order. All the tables. |
| [03-market-and-economy.md](03-market-and-economy.md) | The price function (shapes, `T`, `target`), per-resource parameter table, town/shop consumption math, the derived-facts list (what the market actually does in a real game). |
| [04-engine-internals.md](04-engine-internals.md) | Line-level behaviour of the env: per-step sequence, exact yield formulas, `consecutive_unwatered`/`consecutive_unfed`, decay timing, **reward-lock timing (step 718)**, edge cases and gotchas. |
| [05-observation-action-api.md](05-observation-action-api.md) | Exact shape of `obs`, the action dict, every tile/plant/animal field, and the traps (shop-name casing, `step` vs `day`/`hour`, atomic PLANT, 10-order cap). |
| [06-strategy-playbook.md](06-strategy-playbook.md) | Opponent archetypes, phase plan, the ranked levers, the coin-ceiling analysis, and the full **tried-and-reverted** log so we don't re-run dead ends. |
| [07-codebase-and-workflow.md](07-codebase-and-workflow.md) | `main.py` (v10) architecture, the `agents/main_v*.py` lineage, `bots/` + `contenders/`, the `compete.py` ladder-like gate + `tools/analyze_runs.py` analysis pipeline, `test.py`, the standing iteration loop, Kaggle CLI + `download_episodes.py` + `tools/ladder_analyze.py`. |
| [08-kaggle-discussion-notes.md](08-kaggle-discussion-notes.md) | Source-linked community findings: town-demand economics, livestock/fertilizer value, walking efficiency, fourth-land ROI, engine 1.32.7 changes, hybrid ML, and prioritized experiments. |

---

## One-screen cheat sheet

**Goal:** more coins than the opponent at step 718. Rating moves on win/loss/tie
only — coin margin never matters. Reward = `farm["money"]`; unsold inventory = $0.

**Season:** 30 days × 24 turns = 720 steps. Start $3000. Board 10×10 = four 5×5
quadrants; only **NW** unlocked at start. `BUY_LAND` unlocks NE→SW→SE for
**$1000 / $2000 / $4000**.

**Per turn** you return `{"farmer": [...], "hands": [[...], ...], "market": [[...], ...]}`.
One op per unit. ≤ **10** market orders/turn (extras silently dropped). Budget
~1 s wall-clock; `main.py` runs ~4 ms/step. **Never raise** — top-level
try/except falls back to all-PASS and a silent exception looks like a bad
strategy.

**Crops** (seed / first-yield-day / max-yield-day / interval / max-yield / ongoing):

| Crop | seed | 1st yield | max yield day | interval | max held | ongoing |
|---|---|---|---|---|---|---|
| WHEAT | 10 | day 2 | day 4 | – | 6 (4 no-fert) | no |
| CARROT | 20 | day 2 | day 3 | – | 4 (3 no-fert) | no |
| TOMATO | 50 | day 8 | day 8 | 1 day | 4 ticks | **yes** |
| STRAWBERRY | 100 | day 10 | day 10 | 2 days | 4 ticks | **yes** |
| MELON | 80 | day 10 | day 12 | – | 6 | no |

Base sell prices: WHEAT 25, CARROT 35, TOMATO 60, STRAWBERRY 120, MELON 250,
EGG 50, MILK 160, WOOL 200, FERTILIZER 100.

**Animals** (cost / structure / 1st yield / interval / max held / product):
GOOSE 300 / COOP / day 4 / 1d / 4 / EGG · COW 400 / PASTURE / day 8 / 2d / 6 / MILK ·
SHEEP 500 / PASTURE / day 6 / 3d / 6 / WOOL.
Animals produce **without being fed**; feeding (1 wheat/day) only (a) prevents
escape — 2 missed days = gone forever — and (b) unlocks the `CARE` bonus. Every
surviving animal drops **1 free fertilizer/day**.

**Watering:** every plant, every day. Fresh plant starts `consecutive_unwatered=1`
so it **must be watered on its planting day** or it weeds that night. 2 consecutive
missed days → WEED. One-time crops: watering on ages `ceil(maxYieldDay/2) .. maxYieldDay`
adds +1 yield/day (+2 if fertilized), applied at WATER time.

**Market:** only WHEAT & FERTILIZER can be bought back (`BUY_PRODUCT`); everything
sells. Price = `base` at inventory `I0 = 10000`, rises as inventory falls, falls
as it rises, per-resource shape function each side. Floor $1. Selling walks the
price down **within a single order**. Town center eats 1 of every non-fertilizer
product/day; up to 8 shops unlock (end of days 2,5,…,23) and each eats its demand
list 6×/day. Town drains faster than one farm produces, so premium/ongoing prices
usually sit **well above base** all season.

**Key strategic facts** (see `06`): market barely moves for WHEAT (pure volume
lever); MILK/WOOL/FERTILIZER floor to single digits when both players sell them;
STRAWBERRY is the safe premium; MELON crashes on any glut; the game is decided
days 12–20 by compounding scale (land + animals + rotation); movement is the
scarce resource; `main.py` ladder progress is 333 → 477. Worst matchup =
`animal_factory` (~56% of ladder games): mid-game cash crater vs its
WHEAT-as-working-capital engine (`docs/PLAN_LADDER_ECON.md`).

**Workflow:** iterate one attributable change at a time. `python compete.py
--games 120` (ladder-like: random pool opp, random seat, stock config, silent
exception→all-PASS) archives to `compete_runs/<stamp>/`; `python
tools/analyze_runs.py --last N` reduces that to per-opponent / per-archetype
W/T/L + move%/plant/weed/sell diagnostics + a worst-games loss diagnosis. Local
**cannot gate a `main.py` economy change** (only catches trivial-bot
regressions + errors) — the real gate is a ladder submission read with
`tools/ladder_analyze.py`. Full detail in `07`.
