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

This repository includes `.github/workflows/reproflow.yml`, which validates, verifies, and
uploads the batch evidence on pushes and pull requests.
