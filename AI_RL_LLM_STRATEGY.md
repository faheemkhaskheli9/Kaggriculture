# AI strategy for Kaggriculture: supervised learning, RL, and LLMs

## Recommendation

Build a **hybrid hierarchical agent**, not an end-to-end LLM agent and not a
policy that directly chooses every primitive action.

The production agent should contain three layers:

1. **Deterministic safety layer** — validates actions, protects crops/animals,
   enforces budgets, expands intents into legal primitive actions, and falls back
   to the current scripted agent.
2. **Small neural policy** — chooses strategic intents for each unit and compact
   market/economy decisions.
3. **Offline training loop** — behavior cloning followed by league-based RL and
   repeated leaderboard validation.

Use an LLM as an offline research assistant for replay analysis and opponent-bot
generation. Do not call an LLM during a Kaggle match.

## Why this architecture

One turn may control a farmer, roughly 13 hands, and up to 10 market orders. A
flat primitive action space is combinatorial and most combinations are invalid.
The current scripted agent already knows legality, pathing, zones, survival
deadlines, inventory handling, and endgame liquidation. Learning should improve
the decisions that are uncertain rather than relearn the rules.

The useful learned choices are:

- how many workers to allocate to crops versus animals;
- whether to expand land, hire, or conserve cash;
- crop and animal investment targets;
- which task family each unit should prioritize;
- how aggressively to sell each product;
- how to adapt to the opponent's visible farm and predicted production.

## Model interface

### Observation encoder

Encode every observation into:

- A `10 x 10` board tensor with channels for ownership, locked/empty/weed,
  crop type, age, yield, watering state, plant survival risk, structure type,
  animal type, feeding/care state, fertilizer, and unit positions.
- A scalar vector containing day/hour, both players' money, hand counts, land,
  shed/seeds, market prices and inventories, town demand, crop/animal counts,
  recent money deltas, and opponent-production estimates.
- A per-unit feature vector containing position, inventory, assigned zone,
  distance to shed, current task, and nearby urgent work.

Normalize money, inventory, age, and price features. Represent day/hour with both
linear progress and cyclic sine/cosine features.

### Neural network

Use a compact network that can be exported for fast CPU inference:

- small CNN for the board;
- MLP for global scalars;
- shared MLP/attention block for units;
- per-unit intent head;
- global economy head;
- value head for training.

Keep the model below about 1-2 million parameters. Export weights to `.npz` or
plain arrays and run inference with NumPy if the Kaggle runtime supports it. If
NumPy availability is uncertain, generate a smaller pure-Python linear/MLP
policy or retain the scripted baseline.

### Hybrid action space

Do not predict raw movement commands. Predict one intent per unit:

- `SURVIVE_WATER`
- `YIELD_WATER`
- `HARVEST`
- `PLANT`
- `BUILD_PLACE`
- `FEED_CARE_COLLECT`
- `CLEAR_WEED`
- `DELIVER_LIQUIDATE`
- `IDLE_LOCAL_SWEEP`

The deterministic expander filters the current legal task list by intent, scores
tasks using deadline slack/value/distance, and emits movement or the required
tile action.

The economy head predicts bounded decisions:

- sell fraction for each product;
- crop allocation logits;
- animal allocation logits;
- desired crew size;
- desired unlocked quadrants;
- daily investment fraction and cash reserve;
- confidence to use the scripted decision instead.

Every output is clipped by hard legality, affordability, feed, service-capacity,
order-count, and endgame rules.

## Training stages

### Stage 0 — simulator and data validation

RL should not start on an incorrect simulator.

1. Finish the vectorized engine clone in `ml/clone/engine_np.py`.
2. Replay at least 20 real episodes through it.
3. Require exact action legality and less than 1% error in money/inventory/state
   trajectories at checkpoints.
4. Benchmark throughput. Target thousands of complete games per training hour;
   otherwise optimize or parallelize the environment before training PPO.

Exit condition: deterministic seeds reproduce the official environment closely
enough that a policy cannot exploit clone bugs.

### Stage 1 — behavior cloning

Create a strong, stable initialization from the best scripted agent.

1. Generate 5,000-20,000 games against the full local league with randomized
   seeds and both seats.
2. Record observations, scripted actions, inferred intents, economy targets,
   returns, and opponent archetype.
3. Oversample rare critical actions: survival watering, animal placement/feed,
   land purchase, endgame drops, and liquidation.
4. Train intent and economy heads with supervised losses.
5. Use action masks and class-balanced/focal loss so `MOVE`/`IDLE` does not
   dominate the labels.

Acceptance gate:

- at least 98% agreement on safety-critical intents;
- no illegal actions after expansion;
- at least 95% of the teacher's score-rate and p10 money;
- inference below the competition time budget.

Behavior cloning is a warm start, not the final objective: it cannot exceed the
teacher consistently without RL or search.

### Stage 2 — value model and offline ranking

Before online RL, train a value model to predict terminal coin difference and
win probability from partial states. Use it to:

- rank alternative market plans;
- choose among several legal task assignments;
- identify states where the policy disagrees with the teacher;
- prioritize difficult trajectories for further training.

Validate calibration separately by day and opponent archetype. A value model
that is accurate against passive bots but wrong against animal factories should
not control decisions.

### Stage 3 — RL self-play

Use PPO as the first RL algorithm because the action heads are discrete/bounded,
the value head is already present, and the hybrid layer keeps exploration legal.
An IMPALA-style learner is an option only if many simulator workers can run in
parallel.

Training league:

- current scripted `main.py`;
- all historical promoted versions;
- animal-factory, wheat-flood, premium, melon, and passive bots;
- frozen policy checkpoints;
- replay-derived opponent clones.

Sample opponents with prioritized fictitious self-play (PFSP): frequently train
against opponents where the policy has a 20-80% win rate, while retaining some
uniform sampling to prevent forgetting.

Reward:

- terminal reward: large `sign(my_coins - opponent_coins)` bonus;
- dense reward: clipped change in coin difference;
- small potential-based terms for realized inventory value and productive assets;
- penalties for plant death, animal escape, overflow, invalid/no-op market
  orders, and terminal unsold value;
- no reward for merely moving, owning plants, or holding inventory.

Anneal dense shaping downward so the final policy optimizes wins. Evaluate only
on full 720-turn games.

### Stage 4 — opponent-conditioned policy

Once the base policy is stable, add an opponent embedding based on visible state:

- crop/animal counts and growth rate;
- land and crew expansion timing;
- estimated product production over the next 1, 3, and 5 days;
- market inventory changes attributable to the opponent;
- likely archetype and uncertainty.

Condition crop mix, herd composition, sell timing, and land/crew investment on
this embedding. Keep survival scheduling opponent-independent.

### Stage 5 — distillation and export

The training model may use PyTorch, but the submitted model should be small and
robust.

1. Distill the best ensemble/checkpoint into the compact inference network.
2. Quantize weights if it does not reduce held-out score-rate.
3. Bundle weights and inference code with the deterministic expander.
4. Wrap inference in a top-level exception/time guard.
5. On low confidence, invalid output, missing dependency, or time pressure, use
   the scripted agent's decision.

## How to use an LLM

An LLM is valuable outside the live policy:

1. **Replay analyst:** summarize losses, identify the first divergence in money,
   herd, crop coverage, movement, or market decisions, and produce structured
   failure labels.
2. **Opponent generator:** turn replay patterns into deterministic local bots,
   then verify those bots against the source replay statistics.
3. **Experiment proposer:** suggest one-change hypotheses from aggregate metrics;
   every suggestion still goes through paired evaluation.
4. **Code reviewer:** check reward leakage, observation leakage, action masking,
   simulator mismatches, and train/evaluation contamination.
5. **Curriculum builder:** cluster replays and update opponent sampling weights.

Do not use LLM-generated actions as training truth unless they are executed and
scored in the simulator. Textual strategic plausibility is not evidence of game
strength.

## Evaluation and promotion

Use three disjoint evaluation levels:

1. **Training league:** used by PPO/PFSP.
2. **Held-out local league:** opponents and seed bank never used for updates.
3. **Leaderboard:** the only evidence that the policy generalizes to the real
   distribution.

For local promotion, require:

- 50+ paired seeds, alternating seats;
- score-rate above the incumbent overall;
- at least 45%, then 50%, against each animal-factory test bot;
- non-worse p10 coin difference;
- zero errors, deaths/escapes attributable to the policy, or terminal inventory
  failures;
- inference comfortably inside the runtime limit.

Submit intermediate checkpoints. Collect 20-50 public episodes, download them,
update the replay corpus and league, and resume from the last checkpoint that
improved both held-out and leaderboard performance.

## Implementation order in this repository

1. Improve/freeze `main.py` as the teacher and fallback.
2. Complete and validate `ml/clone/engine_np.py`.
3. Implement `ml/rl/encode.py` and tests.
4. Finish intent-aware expansion in `ml/rl/hybrid_action.py` using the strong
   `engine_v7`/current-agent task machinery, not the weaker legacy engine.
5. Implement `ml/rl/net.py` and `ml/rl/bc.py`.
6. Build the trace dataset and behavior-clone the teacher.
7. Implement `ml/rl/selfplay.py` with PPO, PFSP, checkpoint league, and held-out
   evaluation.
8. Implement `ml/rl/export.py`, fallback, and runtime benchmark.
9. Add the LLM-assisted replay-to-archetype report as an offline tool.
10. Ladder-test one checkpoint at a time and update the league after every read.

## Go/no-go gates

- **No clone fidelity:** do not train RL; continue CMA-ES on the parameterized
  scripted engine.
- **BC below 95% teacher strength:** fix labels, masks, encoder, or expander.
- **RL beats training but not held-out:** expand the league and reduce reward
  shaping; do not submit.
- **RL cannot beat CMA-ES/scripted after a fixed compute budget:** deploy the
  value model or opponent predictor as an advisory component and keep the
  deterministic policy.
- **Runtime/dependency risk:** distill further or ship a tuned config rather than
  a neural network.

## Practical path to 3000

The highest-probability sequence is:

1. Scripted correctness and CMA-ES create the strongest teacher.
2. Behavior cloning reproduces it with a learnable policy interface.
3. PPO improves only strategic intents and economy scalars through diverse
   league self-play.
4. The opponent-conditioned model targets the current animal-factory weakness.
5. Continuous leaderboard replay mining closes the local-to-ladder gap.

RL is the ceiling-raising component. The deterministic engine is the safety and
sample-efficiency component. The LLM accelerates research but stays outside the
submitted turn-by-turn controller.
