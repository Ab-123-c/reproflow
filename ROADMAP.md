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

## v0.2.x — real maintainer inputs

- [ ] smarter repository context selection
- [ ] failure-target hardening
- [ ] case studies on external OSS repositories

## v0.3.x — maintainers' workflow

- [ ] testcase minimization
- [ ] regression pytest generation
- [ ] GitHub Action
