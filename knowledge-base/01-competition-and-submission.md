# 01 — Competition, scoring, and submission

## What it is

Kaggriculture is a **Kaggle Simulations** competition: a turn-based, two-player
farming/economy game run on `kaggle-environments`. You write one autonomous agent
that manages a farm and competes head-to-head against other players' agents on a
live ladder. The agent is the "main farmer" and can hire farm hands to scale.

The season is one fixed run: **30 days × 24 turns/day = 720 turns**. Each player
starts with **$3000** and an empty NW quadrant. The winner is whoever has the
most coins in the bank at the end.

## Scoring / ranking

- Each submission gets a **skill rating**. It plays episodes against
  rating-matched opponents. **Win → rating up, loss → rating down, tie → ratings
  converge.** The size of the change scales with the rating gap (beating a
  strong agent is worth more).
- **The coin margin does not affect rating at all — only win / loss / tie.**
  A 1-coin win and a 100k-coin win are identical to the ladder. Optimise for
  *robust win probability*, not for maximising coins (though in practice a
  higher-coin agent wins more often).
- Up to **5 submissions/day**. Only your **latest 2** are tracked / kept active
  and are what the final leaderboard uses. Every submitted bot keeps playing
  until the competition ends; newer bots play more frequently.
- On upload, a **Validation Episode** runs the agent against a copy of itself. If
  it errors, the submission is marked **Error** (download logs to debug);
  otherwise it joins matchmaking at a default seed rating.
- **Final evaluation:** submissions lock at the deadline, games run ~2 more weeks
  to shrink uncertainty, then a **Bradley-Terry tournament** over those episodes
  produces the final leaderboard.

> Note on "600": a brand-new submission shows a **seed rating of ~600 before it
> has earned any result**. Do not read an unplayed 600 as a score. Earned
> progress for this project so far is **333 → 477** (see `06`).

## The agent contract

`main.py` at the submission root must define:

```python
def agent(obs):
    ...
    return {"farmer": [op, *args],
            "hands":  [[op, *args], ...],   # one per hired hand, in hands order
            "market": [[op, *args], ...]}   # ordered, capped at 10
```

- `obs` is a dict (see `05-observation-action-api.md`).
- Return one op for the farmer, one per hand (`hands` list length should match
  `len(me["hands"])`; extra/missing are tolerated), and an ordered market list.
- Invalid / illegal ops are **silent no-ops** — they cost the turn but nothing
  else.

## Hard constraints the agent must respect

- **~1 s wall-clock per `agent()` call.** `main.py` targets ~4 ms/step. Blowing
  the budget risks a timeout loss.
- **Never raise.** `agent()` wraps everything in `try/except` and returns
  all-PASS on failure. A silent exception is indistinguishable from a terrible
  strategy in the replay — when a submitted episode looks flat or lost, **first
  rule out an exception** (check downloaded logs).
- **≤ 10 market orders per turn** (`maxMarketOrdersPerTurn`). Extras are dropped
  silently, so assemble the order list priority-first (hires and high-value
  sells before speculative buys).
- Observation exposes `day` / `hour`, and *usually* `step` (framework-supplied) —
  but treat `step` as possibly-absent and derive from `day*24 + hour` if needed.
- Shop names in `town.unlocked_shops` are `UPPER_SNAKE` (`PIZZA_SHOP`,
  `FARMERS_MARKET`). A title-case lookup silently returns zero demand — this bug
  zeroed every shop signal in `main_600.py` / `main_v1.py`.

## Submission mechanics

```bash
# single file
kaggle competitions submit kaggriculture -f main.py -m "message"

# multi-file: tar.gz with main.py at the ROOT
tar -czf submission.tar.gz main.py helper.py weights.pkl
kaggle competitions submit kaggriculture -f submission.tar.gz -m "message"
```

- Submission files land at `/kaggle_simulations/agent/` at run time — set imports
  accordingly.
- Limits: **≤ 100 MiB** submission, 8 GiB HDD, 6.5 GiB RAM, 1.6 vCPU.
- Install locally without deps (pygame won't build on Python 3.14):
  `pip install --no-deps kaggle-environments jsonschema kaggle`.

Full CLI workflow (episodes, replays, logs, leaderboard) is in
`07-codebase-and-workflow.md` and `AGENTS.md`.
