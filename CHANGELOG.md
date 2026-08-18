# Changelog

## v0.1.0-alpha.2

- Add structured BugReport, Experiment, PlannerDecision, AttemptHistory, and PlanningResult models.
- Add provider-neutral AgentProvider plus optional OpenAI Responses API adapter.
- Add bounded issue-to-experiment planner with VERIFIED / NOT_REPRODUCIBLE / NEEDS_INFORMATION states.
- Add bounded repository snapshots for planner context.
- Allow Docker execution against a copied source repository via `--repo`.
- Prevent generated experiment files from overwriting source content and constrain them to `.reproflow/experiments/`.
- Persist bug parsing, attempt evidence, result summaries, and verified capsules under `.repro/`.
- Add repository-backed planner demo and integration test.

## v0.1.0-alpha.1

- Initial deterministic reproduction runtime.
- Add repository inspection, reproflow/v1 schema, Docker sandbox, verifier, repeated verification, and Unicode demo.
