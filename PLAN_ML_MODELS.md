# PLAN_ML_MODELS — can a learned model beat the hand-tuned agent?

Survey + phased plan for applying RL / other ML to Kaggriculture. Read
`knowledge-base/06-strategy-playbook.md` and `04-engine-internals.md` first — this
doc assumes both.

Status: **proposal, nothing built.** Date 2026-09-02.

---

## TL;DR / recommendation

- End-to-end deep RL replacing `main.py` is **feasible but the wrong first move**:
  huge factored action space, sparse 720-step credit assignment, and — the same
  wall the scripted agent hit at 477 — a **train-league vs real-ladder gap** that
  RL tends to *overfit harder* than a hand-tuned policy. Weeks of work, high
  variance of outcome.
- The domain economics are already encoded in `main.py` / `bots/_kagri_botlib.py`.
  The high-value ML application is **optimizing the ~50–150 knobs of the existing
  parameterized engine with a black-box optimizer** (CMA-ES / PBT), plus two
  cheap supervised wins. This keeps every legality/no-raise guarantee, ships as a
  tiny config, and directly attacks the ranked levers (M1 land, M4 sell cadence,
  opponent-conditional mix).
- Recommended order: **Phase 1** (Optuna tune of current constants + opponent
  predictor) → **Phase 2** (CMA-ES/PBT over a widened engine config) → **Phase 3**
  (IL-warm-started self-play policy net) *only if 1–2 plateau*. Phase 4
  (engine-as-model planning at key decisions) is an independent add-on.

---

## 1. What the problem looks like to an ML method

| Aspect | Detail | Consequence for modelling |
|---|---|---|
| **Observation** | 10×10 board × ~8 tile types/fields, both farms public; my `private` (shed/seeds/per-unit inv); shared market inventory+prices (9 products); `town.unlocked_shops`; `day`/`hour`. | Encoder = small CNN over board channels + MLP over scalars. State is ~few-hundred floats. Trivial at inference. |
| **Info structure** | Opponent `private` hidden. Future shop unlocks are seeded RNG (seed unknown to agent). Market is shared/public. | **Imperfect information + stochastic** → rules out vanilla AlphaZero determinism; favours model-free RL or MuZero/ISMCTS. |
| **Action space** | Per turn: 1 farmer + ≤~13 hands, each op ∈ ~25–30 discrete (`N/S/E/W/PASS`, `PLANT×5`, `WATER/HARVEST/FERTILIZE/DIG`, `PICKUP/PLACE/DROP`, `BUILD_*`, `FEED/COLLECT_FERTILIZER/CARE`). Plus ≤10 ordered market orders, each parameterized by product + qty. | Joint ≈ 30¹⁴ · (market). **Flat action space is intractable.** Must factor: autoregressive per-unit head, OR per-unit independent heads, OR — best here — **learn per-unit *intent* + market scalars and let the existing deterministic `assign` / order-assembler expand to legal primitives.** |
| **Reward** | `farm["money"]` at step 718. Ladder rating = **win/loss/tie only** (Bradley-Terry). | Train on dense proxy `Δ(my_money − opp_money)` per step + terminal `sign()` bonus; **evaluate on win-rate**, p10 not just mean. |
| **Horizon** | 720 steps, tens of primitive actions/step. | Long credit assignment → need warm start + reward shaping + a fast simulator. |
| **Simulator** | Full env available locally; engine math **fully specified** in `04-engine-internals.md`; weed/shop RNG is seeded and reproducible. | Can build an exact **vectorized clone** for 100–1000× training throughput. Bounded task. |

---

## 2. Competition-rule compliance (hard gates for ANY ML agent)

All satisfiable, but design for them from day 1:

1. **Submission = `main.py` (+ optional tar.gz), ≤100 MiB, 6.5 GiB RAM, 1.6 vCPU,
   no GPU, ~1 s/call.** A small MLP/CNN is KBs–MBs and <1 ms on CPU. Fine.
2. **Do not assume `torch` exists in the sim runner.** Train in torch/JAX locally,
   **export weights to a `.npz` and run pure-NumPy inference** in `main.py`
   (`kaggle-environments` guarantees NumPy). Keeps the submission dependency-free
   and tiny. *(Spike: submit a probe `main.py` that logs `importlib` availability
   of `torch`/`scipy` and records it here.)*
3. **Never raise.** Wrap the whole learned forward pass in `try/except` →
   fall back to the current scripted `agent()`. Any illegal primitive the policy
   emits is already a silent no-op, but prefer the **hybrid design** (§4E) where
   the deterministic layer only ever produces legal actions.
4. **Self-play validation episode on upload** — the net must not error vs itself.
5. **Training is fully offline on our hardware; only frozen params ship.** Allowed.
6. **No runtime network calls.** N/A for a local policy.

Net: a learned agent ships as `main.py` (NumPy inference) + `policy.npz` in a
tar.gz, with the scripted agent as an in-file fallback.

---

## 3. Candidate model families — survey

| # | Family | Fit | Effort | Risk | Verdict |
|---|---|---|---|---|---|
| A | **Bayesian opt / Optuna over current `main.py` constants** (~20 numbers) | high | XS (1–2 d) | very low | **Do now.** Pure upside, no architecture. |
| B | **CMA-ES / PBT over a widened parameterized engine** (50–150 knobs) | high | M (1–2 wk) | low–med | **Primary bet.** Gradient-free, parallel, robust to noisy win/loss fitness, ships as a dict. |
| C | **Supervised opponent-production predictor** (public board → next-5-day output/product) | high | S (2–4 d) | low | **Do now.** Feeds sell/crop shading (playbook §7). |
| D | **Supervised value function / GBDT position eval** | med | S | low | Useful only as a component of D-planning or RL bootstrap. |
| E | **Model-free deep RL** (PPO/IMPALA), **factored/hybrid action space, IL warm-start, PFSP league** | med–high | L (3–6 wk) | med–high | The "real" learned agent. Only after A–C. Needs §5 vectorized sim. |
| F | **AlphaZero / MuZero + MCTS** | med (imperfect-info) | XL | high | Theoretically apt for 2-player, but MCTS over the factored action space needs progressive widening + heavy eng. **Park.** |
| G | **Engine-as-model planning, no training** (beam / flat-MCTS / rollout at key decisions using the real interpreter) | high (targeted) | S–M | low | **Add-on (Phase 4).** Great for land-buy timing, animal-freeze day, terminal liquidation ordering. |
| H | **Offline RL / Decision Transformer on ladder replays** | low | M | med | We only log **our** actions; opponent actions only partially inferable from board deltas; ~hundreds of games. Data-poor. **Skip.** |
| I | **Bandit / meta-controller for portfolio selection** (pick wheatflood/premium/animalfactory sub-agent from early-game opponent features) | med–high | S–M | low | Pairs with `PLAN_CONTENDERS`. Cheap online adaptation without a policy net. |

### Notes per family

**A / B — black-box optimization.** `bots/_kagri_botlib.make_agent(config)` already
turns a config dict into an agent; `test.py` already does paired, seat-alternating
evaluation. Widen the config to expose: crop-share *schedule* (piecewise over
day), land-buy day/fill/cash thresholds per quadrant, hire curve, animal mix +
**opponent-conditional deltas**, sell-sizing coefficients (the `0.72×/0.80×base`
knobs, contested-line caps), `assign` priority weights, endgame trigger hours.
Fitness = **win-rate across (seed × opponent-archetype)**, tie-broken by p10
coins; opponents = frozen league (§ E). CMA-ES for ~50–150 continuous params;
PBT if we also want online schedules. **Graceful failure:** worst case it confirms
the current config is near-optimal for the local league — still informative, days
not weeks lost.

**C — opponent predictor.** Label = a product-vector of the opponent's realized
output over the next 5 days, extracted from downloaded replays
(`download_episodes.py` corpus). Features = their board Counter (crops/animals by
age), their money slope, `day`, unlocked shops. Model = GBDT or tiny MLP. Wire the
prediction into `market_orders` (shade sells away from what they're about to
flood) and `choose_crops`. Directly implements playbook §7; low risk because it's
advisory, not control.

**E — model-free RL, the hybrid design.** Policy net emits, per unit, one of ~7
**intents** (`WATER-zone`, `HARVEST`, `PLANT<crop>`, `PLACE/BUILD`, `FEED/CARE`,
`MOVE-to-region`, `IDLE`) + market **scalars** (per-product sell fraction bucket,
`HIRE`/`BUY_LAND`/animal/seed toggles). The existing deterministic layer resolves
intent → concrete tile (reusing zones + greedy `assign`) and assembles the ≤10
market orders by priority. This shrinks the effective action space from 30¹⁴ to
~7¹⁴ (worst case; less with per-unit independent heads) and **keeps legality +
no-raise for free**. Train: behavior-clone from `main.py` + ladder replays →
PPO/IMPALA self-play with **PFSP** over {policy snapshots, `bots/`,
`main_v1..v5`, `starter`}; dense reward `Δ(money diff)` + terminal `sign()`.
Warm start is non-negotiable — a random policy never coheres in this action space.

**F — MuZero.** Would need: learned dynamics model (or the exact clone as the
model), MCTS with progressive widening over factored actions, and belief handling
for the hidden opponent `private`. Highest ceiling, lowest tractability. Revisit
only if E works and plateaus.

**G — planning with the real engine.** No training. At a few decision points per
game, roll the actual interpreter forward N turns under the scripted policy for
each candidate choice, pick the best. Cheap wins on exactly the decisions the
playbook flags as high-variance: buy Q4 now vs wait, freeze animals, day-28/29
liquidation order. Cost is CPU per lookahead — fits the 1 s budget if N and the
branching factor are small (or precompute the endgame plan once at ~day 27).

---

## 4. Why not "just do deep RL"

1. **Action space** — needs the hybrid factoring (§3E) to be tractable at all;
   that factoring re-uses the scripted machinery, so we're fine-tuning the
   scripted agent's *decisions*, not replacing its *structure*.
2. **Credit assignment** — 720 steps × tens of actions, terminal-ish reward.
   Solvable with shaping + GAE but adds tuning surface.
3. **Throughput** — PPO wants ≥10⁶–10⁷ games. The real Python env is ~1–5 s/game;
   we'd need the §5 vectorized clone (bounded but real work) or a big CPU farm.
4. **The 477 wall is a generalization wall, not a tactics wall.** `test.py` warns
   48–0–0 locally has coexisted with 477 on the ladder; `experiments/LEDGER.md` v6
   shows local-gated changes going net-negative on real opponents. RL optimizes
   *whatever league you give it* — with a weak/narrow league it will find brittle
   exploits and look great locally. Mitigation = a genuinely diverse PFSP league
   mined from ladder replays, and eval that weights p10 / worst-archetype.
5. **Opportunity cost** — Phases 1–2 are ~2–3 weeks total for a likely real gain;
   Phase 3 is 3–6 weeks for an uncertain one.

---

## 5. Vectorized engine clone (enabler for B at scale and E)

`04-engine-internals.md` specifies every formula, the per-step order, and the
seeded RNG. A NumPy/JAX reimplementation that steps **K games in parallel** is a
bounded task (~1 engine file). Payoff: 100–1000× training/eval throughput, exact
reproducibility, and the ability to run CMA-ES generations in minutes. Validate by
replaying downloaded episodes through the clone and asserting bit-identical farm
state each step. **Build this before Phase 2-at-scale or any of Phase 3.**

---

## 6. Phased plan

### Phase 0 — de-risk (2–3 days)
- Probe submission: log runtime availability of `torch`/`scipy`/`sklearn`; record here.
- Stand up the **eval harness = ladder proxy**: `test.py` extended to report
  win-rate + p10 per archetype over {`bots/*`, `main_v1..v5`, `starter`, self}.
- Mine 2–4 more opponent archetypes from `replays/` into `bots/` (playbook §2).
- Decide: is the real env fast enough for Phase 1–2, or build the §5 clone now?

### Phase 1 — cheap supervised / search wins (1 week)
- **Optuna** over `main.py`'s ~20 constants (crop-mix weights, sell coefficients,
  land gates, hire target), objective = harness win-rate. Promote via the normal
  `experiments/LEDGER.md` gate. Submit the winner for a real ladder read.
- **Opponent-production predictor** (§3C); wire advisory outputs into
  `market_orders` + `choose_crops`. Gate the same way.

### Phase 2 — evolved engine config (1–2 weeks)
- Widen `_kagri_botlib` config to 50–150 knobs; make `main.py` consume the same
  config so a winning config *is* the submission.
- **CMA-ES** (and/or PBT for schedules) vs the frozen league on the §5 clone.
  Fitness = win-rate across (seed × archetype), tie-break p10.
- Promote the best config; submit; pull ladder replays; re-mine the league.

### Phase 3 — learned policy net (3–6 weeks, only if 1–2 plateau)
- Build/confirm §5 clone.
- Encoder (board CNN + scalar MLP) + hybrid heads (§3E).
- Behavior-clone from `main.py` + ladder replays; measure BC agent on the harness.
- PPO/IMPALA self-play + PFSP league; dense reward + terminal `sign()`.
- Export to NumPy; `main.py` = NumPy inference + scripted fallback; submit.

### Phase 4 — engine-as-model planning (independent add-on, ~1 week)
- Short real-interpreter rollouts at: quadrant-4 buy timing, animal freeze day,
  day-27 precomputed terminal liquidation schedule. Scripted policy as rollout.

**Every promotion still goes through `experiments/LEDGER.md` + a real ladder
submission** — local wins do not count until a ladder read confirms them.

---

## 7. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Train-league ≠ real ladder (the 477 wall) | Diverse PFSP league mined from replays; eval on worst-archetype / p10; submit early and often for real reads. |
| RL finds brittle exploits | Hybrid action space (legal-by-construction); league diversity; entropy bonus; hold out archetypes for eval. |
| `torch` absent in sim runner | NumPy-only inference from `.npz`; Phase 0 probe confirms. |
| Policy raises / times out | `try/except` → scripted fallback; hybrid layer emits only legal primitives; profile <4 ms/step. |
| Throughput too low for RL | §5 vectorized clone (specs are complete) or defer Phase 3. |
| Weeks sunk for no ladder gain | Front-load Phases 1–2 (cheap, likely-positive); Phase 3 gated on their plateau. |
| Overfit to a fixed opponent predictor | Keep it advisory (shading), never hard control; retrain as league grows. |

---

## 8. Effort / expected-value summary

| Approach | Effort | P(ladder gain) | Ceiling if it works |
|---|---|---|---|
| A Optuna constants | XS | med–high | small–med |
| C Opponent predictor | S | med | small–med |
| B CMA-ES/PBT engine config | M | med–high | med |
| G Engine-as-model planning | S–M | med | small–med (endgame coin-flips) |
| I Portfolio meta-controller | S–M | med | med (matchup robustness) |
| E IL + self-play policy net | L | low–med | med–high |
| F MuZero | XL | low | high |

---

## 9. Knowledge-base note

`E:\Projects\LLM\knowledge-base\` has no pattern covering competitive game-playing
agents / self-play RL / black-box policy optimization. If Phase 2 or 3 is pursued,
propose a new pattern file (`_template.md`) capturing: hybrid (learned-intent +
scripted-expansion) action factoring, PFSP league design, and
"evaluate-on-worst-archetype" for sim-to-real-ladder transfer.
