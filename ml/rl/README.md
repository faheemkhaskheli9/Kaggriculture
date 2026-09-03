# `ml/rl/` — learned policy (PLAN_ML_MODELS Phase 3)

**Only start this after Phases 1–2 plateau** and the `ml/clone/` engine passes
`validate_clone.py --replay` (RL needs the throughput).

## Design (hybrid action space)

The policy never emits raw primitives. It emits, per unit, one **intent** and a
handful of **market scalars**; the deterministic layer (`hybrid_action.expand`,
which reuses `ml/engine.py`'s zone split + greedy `assign`) turns that into a
legal `{"farmer", "hands", "market"}` dict. This keeps the effective action space
at ~`7^n_units` (or less with independent per-unit heads) and makes illegal /
raising outputs impossible — the scripted fallback is the same file.

```
INTENTS = [IDLE, WATER, HARVEST, PLANT, PLACE_BUILD, FEED_CARE, MOVE_REGION]
market head: per-product sell fraction bucket (0/¼/½/¾/1 of shed) ×9,
             + toggles {HIRE, BUY_LAND, buy COW/GOOSE/SHEEP, buy seed bias}
```

## Modules (to build)

| file | role |
|---|---|
| `encode.py` | `obs -> (board CxHxW float32, scalar vec)`. Board channels: tile-type one-hot, crop one-hot, age, yield, watered, animal one-hot, fed, mine/theirs. Scalars: day/hour cyc, money (both), market price+inv (9+9), shed (9), seeds (5), hands, quadrants, shop-demand (9), opp-board summary. |
| `hybrid_action.py` | `expand(intents, market_vec, obs) -> action dict`. **Interface stub is in place.** |
| `net.py` | torch: small CNN trunk + scalar MLP + per-unit intent head + market head + value head. Keep <2M params (CPU inference). |
| `bc.py` | behaviour-clone from `main.py` (+ ladder replays via `logs/`): run `main.py` on many seeds, record `(encode(obs), intent_label, market_label)` where labels are *inferred* from `main.py`'s chosen primitives, train supervised. This is the warm start — a random policy never coheres here. |
| `selfplay.py` | PPO/IMPALA on `ml/clone`, PFSP league = {policy snapshots, `bots/`, `agents/main_v*`, `starter`}. Reward: `Δ(my_money − opp_money)` per step + terminal `sign()`. Entropy bonus; hold out 1–2 archetypes for eval. |
| `export.py` | dump trunk+heads to `.npz`; `main.py` does numpy forward + `hybrid_action.expand`; scripted fallback on any exception. Gate with `test.py` + ladder. |

## Guardrails (from PLAN_ML_MODELS section 4 & 7)

- Eval on **worst-archetype score-rate and p10**, never mean coins alone.
- League diversity is the whole ballgame — mine new `bots/` from ladder replays
  before and during training.
- Submit intermediate checkpoints for real ladder reads; local self-play
  dominance has a history of coexisting with a 477 ladder score.

## Hybrid v1 commands

The behavior-cloning deployment path now consists of `encode.py`, `policy.py`,
`hybrid_action.py`, `bc.py`, and the repository-root `main_ai.py`. The current
`main.py` remains the v10 teacher and fallback.

```bash
python -m ml.rl.bc --replays replays --out intent_model.json --epochs 25
python test.py --games 20 --candidate main_ai.py --incumbent main.py
```

Without `intent_model.json`, or when model confidence is low, `main_ai.py`
returns the v10 action unchanged. PPO remains gated on completing and validating
the fast environment clone.
