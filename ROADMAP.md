# Roadmap

## v0.1.0-alpha.1 — deterministic reproduction runtime

- [x] Python repository inspection
- [x] `reproflow/v1` schema
- [x] Docker sandbox
- [x] deterministic failure matching
- [x] repeated verification

## v0.1.0-alpha.2 — bounded issue-to-experiment loop

- [x] structured `BugReport` model
- [x] provider-neutral `AgentProvider`
- [x] optional OpenAI Responses API adapter
- [x] bounded experiment loop
- [x] repository-backed Docker build context
- [x] attempt history and evidence ledger
- [x] VERIFIED / NOT_REPRODUCIBLE / NEEDS_INFORMATION outcomes

## v0.1.0-alpha.3 — GitHub Issue ingestion

- [x] accept local Issue files or GitHub Issue URLs through the same `--issue` option
- [x] GitHub REST API loader for public and token-authenticated issues
- [x] bounded issue-comment ingestion
- [x] strict github.com URL allowlist and input-size limits
- [x] stable output slug for remote issues
- [x] unit tests for URL parsing, auth headers, comments, PR rejection, and errors

## v0.1.0-alpha.4 — issue-aware repository context

- [x] deterministic Issue-term extraction
- [x] path/content relevance ranking inside bounded snapshots
- [x] candidate-scan limit in addition to file/character budgets
- [x] context-selection metadata for transparency
- [x] `reproflow context` preview command
- [x] planner integration using the same selector

## v0.1.0-alpha.5 — verified testcase minimization

- [x] bounded deterministic text minimizer
- [x] capsule-file minimization using the normal Docker + Verifier oracle
- [x] baseline verification before minimization
- [x] runtime readiness command (`reproflow doctor`)
- [x] JSON output for inspect/context/doctor

## v0.1.0-alpha.6 — failure-target hardening

- [x] require target-specific exception/crash constraints
- [x] explicit Python exception-class matching
- [x] Linux/container signal matching
- [x] false-positive rejection tests
- [x] target-aware deterministic failure signatures

## v0.2.x — real maintainer inputs

- [x] smarter repository context selection (first bounded heuristic in alpha.4)
- [x] failure-target hardening (alpha.6)
- [ ] case studies on external OSS repositories

## v0.3.x — maintainers' workflow

- [x] testcase minimization (first verified capsule-file minimizer in alpha.5)
- [ ] regression pytest generation
- [ ] GitHub Action
