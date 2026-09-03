# Kaggle Discussion Intelligence

Captured **2 September 2026** from the Kaggriculture discussion forum. This is a
paraphrased, source-linked research record rather than a copy of forum posts.
Discussion claims are leads until reproduced locally against the installed engine.

## Highest-value findings

### Town demand determines value more than the base-price table

The shared town continually removes products from market inventory, creating a
scarcity “hole.” Products with broad shop demand can therefore sell far above base,
while products without shop demand have little protection from a glut.

Reported expected full-season town consumption:

| Product | Expected units removed |
|---|---:|
| WHEAT | 525 |
| STRAWBERRY | 426 |
| CARROT | 327 |
| MILK | 327 |
| TOMATO | 228 |
| EGG | 228 |
| WOOL | 228 |
| MELON | 30 |
| FERTILIZER | 0 |

Consequences:

- Strawberry, milk, and wool can be worth much more than their base prices imply.
- Melon appears in no shop menu. Only the town center removes it, so producing it at
  scale can quickly push its price toward the floor.
- Fertilizer has stable production value but no town-created scarcity; every sale
  moves it farther down its glut curve.
- Shop draws are with replacement. Demand should be recalculated from the actual
  unlocked-shop multiset, not only from expected demand.
- Reported distribution warning: wool has no specialist buyer in roughly 34% of
  seasons; carrot demand is also highly variable.

Source: [The price table ranks the crops backwards](https://www.kaggle.com/competitions/kaggriculture/discussion/734412)

### Animals are fertilizer assets as well as product assets

Every surviving animal refreshes one available fertilizer per day, whether it was fed
or not. Fertilizer does not accumulate: failing to collect today's unit loses that
day's opportunity. The discussion estimates the fertilizer stream alone at roughly
$2,900 over a full season before price impact, often exceeding the named product's
ordinary contribution.

Strategic implications:

- Evaluate cows, sheep, and geese using product revenue **plus fertilizer revenue**.
- `COLLECT_FERTILIZER` should remain a high-priority same-tile action.
- Feed is still necessary for animal survival; “fertilizer without feeding” is not a
  sustainable long-term plan because an animal escapes after two missed refreshes.
- Milk and wool are high-variance because their town holes depend on shop draws and
  both players' selling. Fertilizer is lower-variance income.

Source: [Market and livestock analysis thread](https://www.kaggle.com/competitions/kaggriculture/discussion/734412)

### Walking, rather than hiring cost, is the main labor constraint

One published analysis reported that global target reassignment caused approximately
83% of unit turns to be spent moving. Making workers finish useful same-tile action
chains and retain sticky assignments reduced movement to about 55% and roughly tripled
the final bank. Hiring many hands is inexpensive because the Fibonacci counter resets
daily; the benefit is lost if workers thrash between distant targets.

This supports compact zones, sticky targets, same-tile action chaining, and measuring
movement share as a primary executor metric.

Source: [Market and executor analysis thread](https://www.kaggle.com/competitions/kaggriculture/discussion/734412)

### The fourth quadrant is a strategic choice, not a technical requirement

Participants observed that many strong agents do not buy the $4,000 fourth quadrant.
A high-ranked participant confirmed this is strategic. The discussion gives no proof
that three quadrants is universally optimal, so this should be treated as an A/B test,
not a rule.

Required experiment: compare `quadrant_target=3` versus `4` using paired seeds, both
seats, and the full opponent league. Measure win rate first, then movement share,
terminal bank, idle actions, and unused/weed tiles.

Source: [Why aren't top solutions using 4th quadrant?](https://www.kaggle.com/competitions/kaggriculture/discussion/734308)

### Engine 1.32.7 changed scarcity behavior

Version 1.32.7 changed the scarcity branches for carrot, tomato, and egg to a hinge
function. Carrot's `below_target` also reportedly changed from `0.20` to `1.00`, which
is more consequential under ordinary demand than the hinge itself. Reported parameters:

| Product | Scarcity function | Knee `T` | `below_target` |
|---|---|---:|---:|
| CARROT | hinge | 450 | 1.00 |
| TOMATO | hinge | 200 | 0.40 |
| EGG | hinge | 332 | 0.40 |

The current `main.py` market table already contains these values. Keep local testing
and replay analysis pinned to the same environment version used by Kaggle.

Sources: [1.32.7 analysis](https://www.kaggle.com/competitions/kaggriculture/discussion/735311),
[market thread](https://www.kaggle.com/competitions/kaggriculture/discussion/734412)

### Optimize wins, not maximum coins

The leaderboard rewards match outcomes. A strategy with a higher mean bank can still
have a worse win probability if its matchup variance is poorly placed. Discussion
analysis frames win probability in terms of the distribution of coin difference:
when safely ahead, stable revenue is valuable; when projected behind, a higher-variance
scarcity bet can improve the chance of overtaking the opponent.

The local optimizer already emphasizes mean and worst-opponent score rate, with coins
only as a small tie-break. Future work should add matchup-conditioned risk rather than
reverting to a raw-coin objective.

Source: [Market thread, comments on wins versus money](https://www.kaggle.com/competitions/kaggriculture/discussion/734412)

### Rules plus a learned decision layer is the practical ML direction

Public reports generally describe pure PPO as much weaker than deterministic scripts
on this 720-turn, sparse-reward problem. Reported successful directions use a hybrid:
a deterministic executor for movement and legal action sequences, with learning for
uncertain decisions such as opponent capacity, future selling, deviations from a plan,
or market policy.

This supports the repository's current `ml/engine.py`, opponent predictor, and hybrid
policy direction. Do not replace the executor with end-to-end RL without substantially
more rollout throughput and a strong reproducible benchmark.

Source: [Is Pure Self-Play PPO viable?](https://www.kaggle.com/competitions/kaggriculture/discussion/734952)

### Reproducible local measurement beats submission guessing

Participants recommend inspecting the actual environment implementation and running
many paired local games. Documentation and engine behavior have disagreed in places.
For noisy comparisons, force or stratify both shop and weed evolution; they use coupled
randomness in the official environment, so policy changes that alter empty tiles can
also alter later shop draws.

Sources: [Farming strategies](https://www.kaggle.com/competitions/kaggriculture/discussion/735366),
[weed/shop randomness](https://www.kaggle.com/competitions/kaggriculture/discussion/737663)

## Mapping to the current repository

Already implemented:

- 1.32.7 hinge price parameters in `main.py` and `ml/engine.py`.
- Dynamic marginal-price sell sizing.
- Town-shop demand counting.
- Cow-heavy livestock strategy and high-priority fertilizer collection.
- Fixed contiguous worker zones instead of global nearest-task reassignment.
- Opponent-conditional reduction of contested milk/wool production.
- Win-rate-first optimizer fitness in `ml/evaluate.py`.
- Deterministic executor plus learned predictor/hybrid-policy scaffolding.

Open opportunities, in recommended order:

1. A/B test three versus four quadrants.
2. Make sheep allocation zero when the observed shop draw gives wool no buyer.
3. Increase crop-allocation response to duplicate shops and zero-demand outcomes.
4. Estimate opponent market supply and compare the self-cost versus opponent-cost of
   aggressive selling into a shared market.
5. Add lead/deficit-aware risk selection: stable fertilizer/staples when ahead;
   conditional scarcity bets when behind.
6. Add fixed shop/weed trajectories to the evaluation harness for lower-noise ablations,
   while retaining official-randomness validation before promotion.

## Competition-process notes

- Kaggle staff stated that freely and publicly available work is fair use; privately
  shared code outside a team is prohibited. Original implementation and attribution
  remain the safest practice.
- The final Bradley–Terry fit reportedly uses episodes between submissions that are
  still active at final-tournament time; both agents from an episode must remain active
  for that episode to count.
- Public replay agents can be useful benchmark opponents, but optimizing only against
  copied trajectories risks overfitting the present public meta.

Sources: [Public-agent rules clarification](https://www.kaggle.com/competitions/kaggriculture/discussion/737788),
[final Bradley–Terry episode clarification](https://www.kaggle.com/competitions/kaggriculture/discussion/732931)

## Evidence policy for future use

- Treat installed engine code and controlled replay reproduction as authoritative.
- Treat numerical forum claims as hypotheses until locally reproduced.
- Record environment version, seeds, seats, opponents, and shop sequences for every
  experiment derived from these notes.
- Optimize paired win rate; use terminal coins, movement share, and action utilization
  to explain results rather than to replace the competition objective.
