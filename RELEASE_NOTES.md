# ReproFlow v0.1.0-alpha.2 — Bounded Issue-to-Experiment Loop

This alpha adds the first AI-assisted exploration loop while preserving ReproFlow's evidence-first boundary: providers may propose experiments, but only deterministic execution and verification can produce `VERIFIED`.

## Highlights

- Structured bug reports, experiments, planner decisions, and attempt history.
- Provider-neutral `AgentProvider` interface.
- Optional OpenAI Responses API adapter with JSON-schema output and local Pydantic validation.
- Hard planner budget with `VERIFIED`, `NOT_REPRODUCIBLE`, and `NEEDS_INFORMATION` results.
- Repository-backed Docker execution via `--repo`.
- Generated files constrained to `.reproflow/experiments/` and prevented from overwriting source content.
- Evidence ledger persisted under `.repro/`.
- New repo-backed Unicode planner demo and Docker integration test.

## Known alpha limitations

- `reproflow reproduce` currently exposes only the OpenAI provider in the CLI, although the core interface is provider-neutral.
- Repository context selection is heuristic and intentionally bounded.
- The provider still proposes the expected failure matcher; future hardening should lock target-failure semantics more tightly to independently parsed issue evidence.
- Dependency installation happens during Docker build and may use network access. No host secrets are passed by ReproFlow, but untrusted build hooks remain a security consideration.
- GitHub Issue URL ingestion, testcase minimization, regression-test generation, and GitHub Action integration are not included yet.
