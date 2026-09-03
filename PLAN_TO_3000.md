# Kaggriculture plan: current agent to 3000 leaderboard rating

## Objective and baseline

Target: reach a **3000 leaderboard rating** by improving match win probability.
The ladder is driven by wins and losses, so terminal coins are a diagnostic and
tie-breaker, not the optimization target.

Current evidence (3 September 2026):

- `main.py` is a v10 heuristic agent; the reported live rating is about 600.
- The newest replay-analyzable submission (`55973423`, rating 504.5) is 12-15.
- Its main weakness is concentrated: **1-12 versus animal factories**, versus
  **11-3 against other classified opponents**.
- Typical symptoms are only 4-6 animals, about 65 plants on day 20, 65% movement,
  and roughly 25 weeds on day 29.

Reaching 3000 is not guaranteed by any single change. Treat it as a sequence of
ladder-validated rating milestones: **800, 1200, 1800, 2400, 3000**.

## Success metrics

Primary metric:

- Paired score-rate (win + 0.5 tie), overall and by opponent archetype.

Promotion safety metrics:

- At least 45% score-rate against every modeled archetype; first target is 40%
  and then 50% against animal factories.
- No runtime errors or invalid-output episodes.
- No animal escapes and no additional plant deaths.
- Terminal unsold value near zero.
- p10 terminal money does not regress from the incumbent.
- Average movement below 55% after the scheduler phase.

Operational metrics to add to every replay:

- Money, herd by species, live/serviceable plants, empty tiles and weeds at days
  5, 10, 15, 20, 25, and 29.
- Accepted/failed market orders, queued-sale proceeds, shed occupancy/overflow,
  feed reserve, plant deaths, animal escapes, task completions, WATER count,
  movement count, and terminal unsold inventory value.

## Phase 0: establish a trustworthy experiment loop (1 day)

1. Snapshot the exact current `main.py` as the incumbent and record its
   submission ID, rating, commit, and replay count.
2. Fix the tournament replay-memory failure so long gates complete. Store compact
   diagnostics by default and make full replay storage optional.
3. Build a ladder-proxy league containing:
   - the strongest reconstructed animal-factory agents;
   - wheat flood, premium/strawberry, melon, passive, and starter agents;
   - all promoted historical agents and current self-play.
4. Use paired seeds and alternating seats. Screen on 20 paired seeds; use 50+
   paired seeds for promotion.
5. Keep a machine-readable experiment ledger: hypothesis, one code diff, seeds,
   opponent results, p10 money, movement, failures, ladder submission, and verdict.

Exit gate: repeat runs give stable conclusions, complete without memory errors,
and expose per-archetype results.

## Phase 1: recover maintenance capacity (highest-priority change)

The current task builder emits comfort WATER for every dry plant. Replace that
with deadline-aware sparse watering:

- water a new plant on planting day;
- water when `consecutive_unwatered >= 1` for survival;
- water one-time crops inside their yield-bonus window;
- water an ongoing crop when fertilizer is active and its next production tick
  benefits from watering;
- remove routine daily comfort watering outside those cases.

Test the watering change alone. Verify engine semantics with focused unit probes,
then run the full paired gate.

Promotion gate:

- zero extra plant deaths;
- materially fewer WATER and movement actions;
- higher harvest count and money;
- no archetype score-rate regression beyond sampling noise.

Expected outcome: roughly 20-30 actions/day become available for productive work.

## Phase 2: make the animal-factory matchup competitive

Redesign herd bootstrap as a budgeted dawn transaction rather than a one-animal
purchase loop:

1. Forecast proceeds from SELL orders before testing affordability.
2. Reserve the day's hires, two days of wheat feed, and a minimal seed budget.
3. Reserve serviceable tiles and pre-build structures.
4. Batch-buy the largest immediately placeable herd, preferring cows and geese;
   keep sheep light if wool is already oversupplied.
5. Stop buying when remaining days cannot repay purchase, feed, travel, and care.
6. Count feed wheat only on the animal crew, not all field inventories.

Targets versus factory opponents:

- at least 8 animals by day 10-12 and 10-12 by day 15;
- no escapes and uninterrupted feed;
- fertilizer sold rather than left in the shed;
- animal-factory score-rate at least 40%, then 50%.

Keep herd bootstrap, crew feed accounting, and fertilizer sell sizing as separate
experiments so regressions can be attributed and rolled back.

## Phase 3: transactional economy planner

Make `market_orders()` simulate each queued order in execution order:

- update local cash after planned sales;
- update seed, shed, animal, hire, and land state after every order;
- reserve feed and working capital before expansion;
- reject orders that would be silent no-ops;
- value buys by remaining-season marginal profit per required worker-action.

Then optimize these decisions independently:

- hire schedule and final disband day;
- land unlock timing (only buy land that the crew can service);
- animal batch size and species mix;
- seed-spend cap and crop mix;
- sell quantities based on marginal price and opponent supply.

Promotion gate: earlier land/herd milestones, no failed buys or overflow, improved
paired score-rate, and no reduction in lower-tail liquidity.

## Phase 4: deadline-slack scheduling

Replace mostly static task priority with:

`slack = turns_to_deadline - travel_cost - remaining_actions`

Each task should carry a deadline, terminal value, action chain, inventory need,
and estimated travel/execution cost.

- Assign survival and expiring-harvest tasks globally by smallest slack.
- Keep routine work in persistent local sweeps to avoid target oscillation.
- Reserve a small animal crew while the herd is active.
- Rebalance zones only after land/crew changes, not every turn.

Promotion gate: movement below 55%, no missed survival deadlines, more completed
high-value tasks, and higher score-rate versus both factory and crop-heavy agents.

## Phase 5: automated parameter search

Only after Phases 1-4 are correct, expose 30-80 meaningful parameters in the
existing ML engine: priorities, reserve curve, hiring/land gates, coverage per
worker, herd targets, species weights, crop shares, sell floors, and endgame
cutoffs.

Use CMA-ES or successive halving with a robust objective:

1. maximize worst-archetype score-rate;
2. then maximize overall paired score-rate;
3. then maximize p10 coin difference;
4. penalize errors, deaths/escapes, overflow, and terminal unsold value heavily.

Use distinct train and held-out leagues. Do not optimize on starter/self-play
alone. Promote only after 50+ paired held-out seeds and a clean runtime check.

## Phase 6: ladder adaptation loop

For every promoted candidate:

1. Submit one clearly labeled build.
2. Wait for at least 20 public episodes; prefer 30-50 before a major conclusion.
3. Download replays/logs and classify opponents.
4. Compare paired metrics and money trajectories to the incumbent.
5. Convert the most important loss cluster into a local replay-derived opponent.
6. Make one attributable strategic change and repeat.

Milestone policy:

- **600 -> 800:** remove obvious waste and reach 40% versus factories.
- **800 -> 1200:** reach roughly 50% versus every known archetype.
- **1200 -> 1800:** beat the held-out replay-derived league; reduce worst-matchup
  variance and cash stalls.
- **1800 -> 2400:** add opponent adaptation based on visible herd, crop mix,
  market inventory, and town demand without switching the whole strategy.
- **2400 -> 3000:** mine every new high-rated loss, search parameters on the
  updated league, and accept only ladder-confirmed improvements.

## Immediate experiment queue

Run these in order, one change per branch:

1. Instrument missing diagnostics and repair low-memory tournament execution.
2. E1: sparse/deadline watering.
3. E2: transactional cash including queued sales.
4. E3: dawn herd batch bootstrap with two-day feed reserve.
5. E4: animal-crew-only carried-wheat accounting.
6. E5: deadline-slack scheduler with persistent local sweeps.
7. E6: CMA-ES over the corrected engine.

Do not prioritize another fixed crop-mix tweak, general CARE pass, opportunistic
fertilizer routing, or a large RL policy yet; existing experiments show those are
either regressions or lower-value than fixing action capacity and herd bootstrap.

## Definition of done

The goal is achieved only when a submission reaches at least 3000 on the public
leaderboard after enough completed episodes to rule out an early rating spike,
with its exact source and configuration archived and reproducible locally.
