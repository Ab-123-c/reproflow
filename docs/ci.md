# CI integration

ReproFlow exposes JSON output so CI jobs can make decisions without scraping terminal text.

## Validate capsules

```bash
reproflow list . --json
reproflow validate examples/unicode-username/repro.yaml --json
```

`reproflow list` reports malformed capsules as `valid: false`; this makes a repository-wide
validation step fail visibly before a Docker run starts.

## Verify a batch

```bash
reproflow verify-all . --repo . --json > reproflow-verification.json
```

The command exits with status `1` when any capsule is invalid, cannot run, or does not
reproduce. The JSON document contains per-capsule status, repeatability, and stable failure
signatures.

## Persist and publish evidence

```bash
reproflow run repro.yaml --output .repro/my-bug
```

The output directory contains `verification.json` and `report.md`. Upload that directory as a
CI artifact or paste the Markdown report into a bug tracker. `reproflow report` can render a
previously saved result later without Docker.

Before publishing an artifact, validate the persisted contract and fail the job on drift:

```bash
reproflow evidence .repro/my-bug --check
```

The check prints a JSON summary and returns status `2` when the evidence is malformed or its
status, repetition, or execution aggregates are inconsistent.

This repository includes `.github/workflows/reproflow.yml`, which validates, verifies, and
uploads the batch evidence on pushes and pull requests.

## Issue automation

The optional `.github/workflows/reproflow-issue.yml` workflow reacts to opened and reopened Issues. It runs the planner and deterministic verifier, uploads `.repro/github-issue` as an artifact, and posts a short status comment. Add an `OPENAI_API_KEY` repository secret when using the AI planner; without it the workflow still records a diagnostic result. The workflow uses read-only contents access and issue-comment permission only.

## Environment matrix

Compare a capsule across explicit Docker images and keep a machine-readable matrix artifact:

```bash
reproflow matrix examples/unicode-username/repro.yaml \
  --image python:3.11-slim --image python:3.12-slim \
  --repo . --output .repro/matrix.json --json
```

The command exits `1` if any image cannot reproduce the failure and emits
`reproflow/matrix/v1` rows with repeatability, signatures, and environment hashes.

To inspect or publish the result locally:

```bash
reproflow evidence .repro/github-issue --json
reproflow badge .repro/github-issue --output reproflow-badge.svg
```
