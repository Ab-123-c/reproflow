# Changelog

## v0.1.0-alpha.6

- Harden failure targets so a generic `exception` or `crash` can no longer verify an unrelated non-zero exit.
- Add `exception_class` matching for Python-style traceback identities.
- Add `signal` matching for Linux/container crashes, including conventional `128 + signal` exit statuses.
- Keep `nonzero_exit` as the explicit opt-in matcher when any failing command is intentionally sufficient.
- Include the observed exception/signal in deterministic failure signatures.
- Strengthen the OpenAI planner prompt to propose target-specific failure constraints.
- Add failure-target documentation and unit coverage for false-positive rejection.

## v0.1.0-alpha.5

- Add deterministic testcase minimization for a selected file inside a verified `reproflow/v1` capsule.
- Re-run the Docker sandbox and deterministic Verifier for every accepted minimization step; model output is never used as the minimization oracle.
- Refuse minimization when the baseline capsule is not already verified.
- Add bounded minimization controls with `--max-checks` and `--min-length`, and write a separate minimized capsule by default.
- Add `reproflow doctor` for Python, Docker daemon, optional OpenAI package/key, and GitHub token readiness checks.
- Add `--json` output to `reproflow inspect`, `reproflow context`, and `reproflow doctor` for scripts and future GitHub Actions.
- Add unit tests for minimizer bounds/behavior and doctor readiness modeling.

## v0.1.0-alpha.4

- Rank bounded repository context using deterministic relevance hints extracted from the untrusted Issue.
- Keep project metadata structurally prioritized while promoting matching Python source/test paths and bounded content.
- Record selection terms, per-file scores, and candidate counts in `RepositorySnapshot`.
- Add a candidate-scan bound in addition to existing file-count and character budgets.
- Add `reproflow context --repo ... --issue ...` to preview planner-visible files without AI or Docker.
- Make the reproduction planner use the same issue-aware snapshot builder.
- Continue excluding `.git`, virtual environments, caches, `.repro`, `.reproflow`, and `node_modules`.
- Add repository-context documentation and unit coverage for ranking, determinism, bounds, and generated-directory exclusion.

## v0.1.0-alpha.3

- Accept a local bug-report file or a `https://github.com/<owner>/<repo>/issues/<number>` URL through `reproflow reproduce --issue`.
- Add a GitHub REST API issue loader with optional `GH_TOKEN` / `GITHUB_TOKEN` authentication.
- Load a bounded number of issue comments with `--github-max-comments` (default 20, maximum 100).
- Restrict remote issue ingestion to GitHub.com and construct `api.github.com` requests internally.
- Add response, file-size, body, comment, and total-rendered-text limits before planner ingestion.
- Reject pull-request payloads in the Issue input path.
- Add deterministic output slugs such as `github-owner-repo-123` for remote issues.
- Add GitHub Issue ingestion documentation and unit tests.

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
