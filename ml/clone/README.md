# `ml/clone/` — vectorised engine clone (PLAN_ML_MODELS section 5)

**Why:** the real `kaggle_environments` interpreter is ~1–5 s per 720-step game.
CMA-ES at scale and any Phase-3 RL need 100–1000× that. Every formula, the
per-step order, and the seeded RNG are fully specified in
`knowledge-base/04-engine-internals.md`, so an exact NumPy/JAX reimplementation
that steps **K games in parallel** is a bounded task.

**Status:** scaffold. `engine_np.py` has the state layout, the step ordering, and
the fully-specified pure functions (`market_price`, `_shape`, town consumption,
decay). The unit-action application (`_apply_unit_action`) and the end-of-day
block are stubbed with `TODO(04-*)` markers pointing at the exact spec section.

## Build order

1. Fill `_apply_unit_action` (spec §"`_apply_unit_action`") — the big one.
   Vectorise per action-type: gather the units issuing that op, apply as a masked
   scatter. Movement / PASS / PLANT / WATER / HARVEST / FERTILIZE / DIG /
   PICKUP / PLACE / DROP / BUILD_* / FEED / COLLECT_FERTILIZER / CARE.
2. Fill `_process_market` (spec §"`_process_market`") — the slot-by-slot,
   per-unit lockstep with `_refresh_prices` after each slot.
3. Fill `_end_of_day` (spec §"`_end_of_day`") — plant refresh, animal refresh,
   `_spawn_weeds` (RNG: `env.info["seed"] * 1_000_003 ^ day`), inventory
   auto-drop, shop unlock (`sorted(SHOPS)`, uniform with replacement).
4. `validate_clone.py`: replay every episode in `replays/` through the clone,
   feeding the recorded actions, and assert farm state is **bit-identical** each
   step. Fix divergences until all 58 replays pass.
5. Only then wire it into `ml/evaluate.py` as an optional fast backend
   (`--backend clone`) and into `ml/rl/`.

## Non-goals

The clone does **not** need to match the env's Python object shapes, only the
*values* that matter for reward and for our observation features. Keep it in
plain int/float arrays; convert to the dict `obs` shape only at the boundary
where a Python agent (a league bot) needs to be queried.
