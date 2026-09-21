---
description: Run one Kaggriculture ladder iteration through the subagent crew (analyst → skeptic → builder → reviewer → gatekeeper → bookkeeper)
---

Run ONE iteration of the ladder loop (`docs/LADDER_RUNBOOK.md`) by delegating
each phase to its subagent. You are the orchestrator: pass each agent only the
previous agent's conclusion (not transcripts), keep your own context small, and
obey `CLAUDE.md` workflow rules.

Optional focus / starting stage: $ARGUMENTS
(e.g. `readback`, `gate agents/main_v96_x.py`, or a hypothesis to start from)

Pipeline - strictly sequential, stop at the first failed stage:

1. **ladder-bookkeeper** - readback of the pending sub (episode count, verdict
   if >= 20 eps). If it is < 20 eps and nothing is queued to build, stop here.
2. **ladder-analyst** - max 3 ranked hypotheses.
3. **ladder-skeptic** - PASS / KILL / LOCAL-ONLY each. All killed -> record the
   kills via ladder-bookkeeper and stop.
4. Show me the surviving pick and its $/game in 3 lines, then continue without
   waiting unless the pick is economy/crop tuning (that needs my approval).
5. **ladder-builder** - one `ENABLE_*` hunk in a new `agents/main_v<NN>_*.py`.
6. **ladder-reviewer** - BLOCK -> send the findings back to ladder-builder
   (max 2 rounds), then re-review.
7. **ladder-gatekeeper** - one gate at a time. It runs in the background; do
   not poll, resume when notified.
8. **ladder-bookkeeper** - record the result (LEDGER + AGENT_MISTAKES + State).
   On gate PASS, decide submit / no-submit yourself per the auto-submit
   preconditions (only if clearly better than live); if submitting, stage the
   flag on `main.py`, then tell the bookkeeper explicitly to "submit".

Never run two builders or two gates in parallel. End with a <= 15-line summary:
sub id + ep count, last judged read, what was built/gated, verdict, next action.
