# Public-agent strategy catalog (ideas only)

**Captured:** 2026-09-05  
**Purpose:** preserve publicly described Kaggriculture strategy mechanisms for
future independent experiments.

## Safety and evidence boundary

This is a paraphrased idea catalog, not a source-code archive. Never clone,
restore, embed, translate, or adapt another competitor's implementation,
compressed payloads, route tapes, constants, or action sequences. Public code
that was previously inspected has been deleted and must stay deleted.

Every idea below must be re-derived from the installed game engine, public game
rules, and our own replay data. It must be independently implemented behind a
toggle, tested as one attributable mechanism, and evaluated through the paired
gates in `docs/IMPACT_RANKED_LEADERBOARD_PLAN.md`. Results reported for another
agent are discovery context only and are never evidence for our candidate.

## Strategy families observed in public agents

### 1. Precomputed season-level route

- Plan most or all of the 719 actionable turns in advance.
- Coordinate land, crop layout, herd composition, workers, inventory, and
  market cadence as one long-horizon schedule.
- Use the schedule as a macro-policy while online code enforces legality and
  repairs deviations.
- Maintain multiple route families for different crop/herd allocations rather
  than expecting one tape to dominate every shop and opponent regime.

Independent experiment: generate routes from our engine model and optimizer;
compare movement, productive actions, deadline misses, and paired score-rate
against the current scheduler.

### 2. Closed-loop repair around a fixed plan

- Detect when stochastic state makes the scheduled action invalid or unsafe.
- Repair weeds before a scheduled build or plant.
- Repair missing seeds, animals, feed, inventory room, and worker alignment.
- Remember the displaced scheduled action and resume/re-align after repair.
- Protect survival deadlines even when the tape expected a different state.
- Reconcile planned versus actual inventory and cash before purchases.

Independent experiment: define explicit plan invariants and repair handlers;
measure recovery success without copying any public action sequence.

### 3. Multiple specialist routes

- Maintain specialists for alternative cow/sheep balances, shop regimes,
  aggressive openings, and premium-market situations.
- Let specialists share the same safety/execution interface.
- Prefer a small set of meaningfully different plans over many nearly identical
  constant variants.

Independent experiment: derive specialists from our replay clusters and engine
economics, then validate each against a held-out archetype.

### 4. Public-state opponent classification

- Classify behavior from visible facts rather than hidden identity: early cash,
  hires, land, crop counts, herd/species, structures, and selling pressure.
- Recognize extreme early spending or hiring as an opening-style signature.
- Re-evaluate at a few causal checkpoints rather than switching every turn.
- Use fail-closed defaults for unseen states.

Useful features to test: opponent herd/crop counts by day, rate of expansion,
visible production capacity, market inventory deltas, and town-shop multiset.

### 5. Sticky first-divergence route selection

- Advance candidate experts consistently until their actions meaningfully
  diverge.
- Select using only information available at that moment.
- Commit to the selected macro route to prevent oscillation.
- Permit later changes only through narrow, separately guarded overlays.

Independent experiment: compare sticky selection with per-turn switching on
route churn, invalid actions, and paired score-rate.

### 6. Causal/no-hindsight route selection

- A route may not diverge before the public signal used to select it becomes
  observable.
- When a late shop/opponent signal appears, choose a prefix-compatible route or
  transition plan rather than pretending it was known at turn zero.
- Validate every classifier against its information timestamp.

This is a mandatory correctness rule for all replay-derived strategies.

### 7. Component-level policy overlays

- Borrow only a proposed market delta, purchase decision, or other isolated
  component while retaining the incumbent field execution.
- Apply an overlay only when the proposal is compatible with the active
  physical plan; agreement on farmer/hand actions is one possible guard.
- Preserve a base-versus-overlay state so the delta is calculated explicitly.

Independent experiment: start with market-only overlays because they can be
ablated without replacing routing or maintenance.

### 8. Opponent-aware market timing

- Observe market inventory and visible opponent production/selling pressure.
- Time premium sales around town consumption and current scarcity.
- Size sales to avoid collapsing high-value products to their floor.
- Reduce or defer contested milk/wool/premium production when both farms are
  visibly flooding the same line.
- Consider defensive or denial selling only after measuring its cost to our own
  revenue.

Candidate parameters: demand weight, opponent-crowding penalty, sell floor,
maximum price impact, observation window, and intervention cooldown.

### 9. Premium preemption with repayment/reserve

- Front-run a predictable premium opportunity only with a defined capital or
  inventory reserve.
- Track what the intervention borrowed from the base plan.
- Repay/reconcile that deviation so later scheduled purchases and feed remain
  serviceable.

Independent experiment: transactional simulation must prove the overlay cannot
double-count same-turn sale proceeds or starve mandatory maintenance.

### 10. Shop-conditioned production

- Count duplicate shops independently.
- Prefer products with strong realized town demand, not merely high base price.
- Maintain special handling for repeated shop draws and zero-demand outcomes.
- Avoid large melon/fertilizer gluts because town demand provides little or no
  price recovery.

Candidate parameters: demand-per-shop weights, response delay, minimum remaining
production cycles, and maximum portfolio share.

### 11. Adaptive herd composition

- Score species using product price, remaining production ticks, purchase and
  feed cost, fertilizer value, realized town demand, and visible crowding.
- Use staged herd caps so opening land and labor can service every animal.
- Preserve existing animals; apply adaptation primarily to new purchases.
- Keep feed and escape prevention in the deterministic safety layer.

Our independent `ANTI_META` mode already implements part of this family. Its
next experiment is strict feed-first servicing, not another species-weight
tweak or a larger fixed crew.

### 12. Animal-as-fertilizer factory

- Value each surviving animal as both a product asset and a daily fertilizer
  source.
- Collect fertilizer before the daily opportunity disappears.
- Treat feed logistics and service capacity as constraints on herd ROI.
- Sell fertilizer progressively because it has no town-created scarcity.

This is an archetype to counter and a possible portfolio component, not a reason
to maximize herd size blindly.

### 13. Labor locality and action throughput

- Movement is the binding resource; cheap hiring does not help when workers
  repeatedly cross the farm.
- Use persistent zones, coherent local sweeps, same-tile action chaining, and
  global overrides only for survival deadlines.
- Evaluate productive actions and missed deadlines alongside movement share.

Our validated routing work is the independent implementation substrate for
this family.

### 14. Capacity-aware land expansion

- Three quadrants can outperform four when the last quadrant adds more travel
  and maintenance than profitable output.
- Buy land only when existing land is sufficiently utilized and remaining
  worker capacity can service the additional tiles.
- Use remaining-season marginal profit rather than a universal quadrant cap.

### 15. Lead/deficit-aware risk

- When projected safely ahead, favor stable staples and fertilizer cash flow.
- When projected behind, selectively increase variance through scarcity or
  less-contested premium lines.
- Optimize probability of winning rather than maximum average terminal coins.

Independent experiment: define a conservative public-state lead estimator and
test risk response separately from portfolio selection.

### 16. Endgame liquidation and plan shutdown

- Stop actions whose payoff occurs after the final scored step.
- Redirect labor to harvest, shed delivery, and selling.
- Liquidate all useful inventory even at the price floor when it otherwise has
  zero terminal value.
- Repair terminal market capacity and worker-position failures explicitly.

### 17. Hybrid deterministic + learned controller

- Keep movement, legal action sequences, maintenance, and inventory safety
  deterministic.
- Use learning only for uncertain strategic choices such as expansion timing,
  opponent capacity, route selection, selling, or deviation from plan.
- Prefer explicit value/timing rules for rare BUY_LAND and BUY_ANIMAL events
  when imitation data cannot learn them reliably.
- Avoid end-to-end sparse-reward RL until rollout throughput and held-out
  evaluation fidelity are strong enough.

### 18. Reproducible evaluation discipline

- Use identical opponents, seeds, and alternating seats for candidate/incumbent
  comparisons.
- Freeze train and validation manifests and hash generated artifacts.
- Preserve known wins and inspect results by opponent archetype.
- Promote on paired score-rate; use money and action metrics diagnostically.
- Confirm that selection signals use only public information available at the
  decision time.

## Public-agent concepts intentionally not preserved

The following implementation artifacts must not be saved:

- competitor source files or repositories;
- compressed/base-encoded source payloads;
- exact route tapes or turn-by-turn action sequences;
- competitor-specific constants copied from code;
- code translated, mechanically rewritten, or lightly refactored from a public
  submission.

If future research reveals a new mechanism, append a paraphrased entry here
with its causal hypothesis, observable inputs, safety constraints, independent
implementation path, and evaluation gate. Link external discussion sources in
`knowledge-base/08-kaggle-discussion-notes.md`; do not turn this catalog into a
copy of public posts.

## Mapping to the shared work board

| Catalog family | Current task |
|---|---|
| Adaptive herd + deterministic maintenance | `AM-FEED-1` |
| Unsaturated archetype evaluation | `EVAL-FACTORY-1` |
| Replay-derived herd timing | `R3-HERD-1` |
| Rare-event strategic controller | `POLICY-RARE-1` |
| Long-horizon route + repair | Future task after current routing promotion |
| Market-only overlay | Future E5 adaptive-portfolio ablation |

