# Contender portfolio ledger

Companion to `experiments/LEDGER.md` (the single-lineage table). One row per
contender agent. See `PLAN_CONTENDERS.md` for the roster and the promotion gate.

**Columns**
- **Agent** — file in `contenders/`.
- **Archetype** — which ladder strategy it mirrors (`PLAN_3000_v4.md` section 2.1).
- **Local vs main.py** — paired `test.py` OVERALL: score-rate, own-coins mean, diff.
- **Worst matchup** — lowest score-rate vs any single benchmark opponent.
- **Err / ms** — must be 0 / ≤4.
- **Ladder** — Kaggle score once submitted (`download_episodes.py`).
- **Status** — `infra` / `candidate` / `submittable` / `submitted` / `shelved`.

| Agent | Archetype | Local vs main.py | Worst matchup | Err / ms | Ladder | Status |
|---|---|---|---|---|---|---|
| `_engine.py` | — (shared `make_agent(config)` fork of `main.py` v5) | — | — | 0 / ≤4 | — | infra |
| `c_v5clone.py` | v5 neutrality check | 50.0% score, +0 mean diff (3-0-3 / 6g) | — | 0 / ≤4 | — | infra — verifies `_engine.py` == v5 |
| `c_wheatflood.py` | wheat flood (ladder 35k–111k) | RR 4g: overall 0.31, mean 8.6k, worst 0.00 vs main; only beats starter | vs main 0.00 | 0 / ≤4 | — | **dominated** — shelve as sparring-only or rework the wheat margin |
| `c_animalfactory.py` | animal + fertilizer factory (ladder 38k–74k) | RR 4g: overall 0.69, mean 35k, beats c_wheatflood .75 / c_premium 1.00; loses to main | vs main 0.00 | 0 / ≤4 | — | candidate — strongest new contender; run the full gate |
| `c_premium.py` | premium concentration (our closest losses) | RR 4g: overall 0.50, mean 33k, p10 22k, move% 63 & sell/day 15 (lazy by design); C2 hard-counters it 0-3 | vs main / c_animalfactory 0.00 | 0 / ≤4 | — | candidate — low-variance coin-flip opponent; hard-countered by C2 |
| `tournament.py` | round-robin harness (repo root) | validated 4g/pair 5-agent | — | 0 / — | — | infra |

## Notes

### 2026-09-02 — Phase 0 + C1 built

- **`_engine.py`** = `main.py` v5 refactored to `make_agent(config)`. Pure helpers
  (`price_at`, zones, `build_tasks`, `assign`, animal crew) are module-level and
  byte-identical to v5; the policy layer (`choose_crops`, `market_orders`,
  `agent`) is a closure over the config. New knobs added for the portfolio:
  `hire_fn`, `land_ok_fn`, `animal_target_fn`, `crop_cfg`, `crop_caps_fn`,
  `plant_water_slack`, `sell_*` caps/keeps + overrides, `seed_cap`,
  `seed_lookahead`. Defaults reproduce v5.
- **`c_v5clone.py`** neutrality check **passed**: `test.py --games 6 --candidate
  contenders/c_v5clone.py --incumbent main.py --opponents main.py` →
  W/T/L 3-0-3, **mean diff +0**, 0 errors, move% 64 / sell-day 40 / unsold 5
  (all == v5). Any future non-neutral result here means `_engine.py` drifted.
- **`c_wheatflood.py`** (C1): runs clean (0 err, ≤4 ms). Diagnostic vs starter —
  land expansion to 4 quadrants and the 13-hand ramp both work, and after adding
  `seed_cap`/`seed_lookahead` the field fills early (day 9: 71/74 tiles). **But
  own-money stays flat at $1–5k the whole game** (ends ~$8–10k): a ~70-tile
  one-time-crop wheat field with 13 paid hands + heavy reseeding roughly
  *breaks even* at base wheat price (~$25). The ladder wheat-floods that scored
  35–110k did it against weak opponents who left the wheat price scarce; against
  `main.py` / `bot_animalfarm` the margin collapses — exactly the playbook's
  "monoculture collapses vs a diversified agent" (`06 section 2`).
- Tried within-session (all flat, OVERALL ~8.4k): raising `seed_cap`/
  `seed_lookahead` (fixed mid-game fill but not money); a wheat sell floor
  (`sell_keep_override WHEAT 0.60` instead of 0.0) to stop self-crashing the
  price. Neither moved the result — the constraint is the wheat *margin*, not
  fill or sell timing.
- **Open for C1:** either accept it as a validated-weak sparring partner + a
  ladder bet only when the ladder is full of passive agents, or push it further
  (scarcity-aware wheat sell floor instead of dumping into any price; fewer
  hands so the crew cost stops eating the wheat revenue). Decide from the first
  round-robin + ladder read before spending more on it.

### 2026-09-02 — C2, C3, and `tournament.py`

- **`c_animalfactory.py`** (C2) and **`c_premium.py`** (C3) built as `_engine.py`
  configs; both run clean (0 err, ≤4 ms) and neither collapses vs strong
  opposition (unlike C1). C2 = custom day-ramped herd cap (2→6→12→16, opp-
  conditional) so the money gate paces cow buys; C3 = 5 hands / 2 quads /
  strawberry+tomato hold / low `plant_water_slack`.
- **`tournament.py`** built (round-robin, both seats, score-rate + mean-coin
  matrices + per-agent worst-matchup). Validated on a 4-game/pair, 5-agent run:

  ```
  rank: main > c_animalfactory > c_premium > c_wheatflood > starter
  SCORE-RATE           main c_wheatf c_animal c_premiu  starter
  main                   --     1.00     1.00     1.00     1.00
  c_wheatflood         0.00       --     0.25     0.00     1.00
  c_animalfactory      0.00     0.75       --     1.00     1.00
  c_premium            0.00     1.00     0.00       --     1.00
  PER-AGENT         overall  worst   worst_vs   meanC   p10C  move%
  main                 1.00   1.00   c_wheatfl  51518  35279   65%
  c_animalfactory      0.69   0.00        main  34888  11079   64%
  c_premium            0.50   0.00        main  33442  22341   63%
  c_wheatflood         0.31   0.00        main   8580   7637   59%
  ```

  Small sample (4g/pair) — `main` sweeping 1.00 is partly that. But the
  structure is real and is the discriminating signal the single-lineage local
  gate never gave: **C2 > C3 > C1**, C2 hard-counters C3 (3-0), C1 is dominated
  by everything except starter, and none of the new contenders beats `main.py`
  yet.

**Next:** (1) full gate — `python tournament.py --games 24` on the default pool
(add `main_v5.py`, `main_p3.py`, `bots/bot_melonmono.py`, `bots/bot_premium.py`);
(2) if C2/C3 still lose to `main.py`, tune them one knob at a time vs the
matrix; (3) C1 — shelve as sparring-only or rework the wheat margin; (4) build
C4 `c_monopolist.py` (`_engine.py` needs a passive/active switch first).
