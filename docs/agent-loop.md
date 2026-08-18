# Bounded agent loop

ReproFlow alpha.2 separates exploration from proof:

```text
untrusted issue.md
      ↓
structured BugReport
      ↓
repository snapshot (bounded)
      ↓
AgentProvider proposes PlannerDecision
      ↓
Experiment files under .reproflow/experiments/
      ↓
Docker execution against copied source repository
      ↓
ExecutionEvidence
      ↓
Verifier
      ↓
VERIFIED / next attempt / stop
```

The loop has a hard experiment budget. Provider output cannot directly produce the `VERIFIED` state; only `VerificationResult.reproduced` can do that.

Attempt history is fed back to the provider as untrusted evidence, with stdout/stderr tails bounded before inclusion in the next planning prompt.
