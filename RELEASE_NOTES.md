# ReproFlow v0.1.3 — Evidence validation release

This release adds a deterministic validation gate for persisted verification evidence and a global
version query for scripts and CI. Capsules can be scaffolded, discovered, batch-verified, exported
as stable JSON, and converted into reviewable pytest regression tests. Each verification can also
produce a Markdown evidence report and an SVG badge.

See [`CHANGELOG.md`](CHANGELOG.md) for the complete list of changes.


## 0.1.3 highlights

- Validate `reproflow/evidence/v1` documents with `reproflow evidence --check`.
- Detect malformed payloads and inconsistent status, repetition, or execution summaries.
- Emit a JSON validation result and a non-zero exit code for CI or release gates.
- Print the installed runtime version with `reproflow --version`.
- Compare explicit Docker images with `reproflow matrix` and export per-capsule evidence from `verify-all --output`.
- Use `list --strict` in CI and invoke ReproFlow with `python -m reproflow` when a console script is unavailable.

## 0.1.2 baseline

- Persist `reproflow/evidence/v1` evidence with repeatability, execution, failure, and environment details.
- Inspect saved evidence with `reproflow evidence` and generate a badge with `reproflow badge`.
- Enable `.github/workflows/reproflow-issue.yml` to reproduce opened or reopened issues. Set the optional `OPENAI_API_KEY` repository secret for AI planning.

## v0.1.0 feature baseline

The sixth alpha makes the Verifier stricter about *which* failure was reproduced. A command that exits non-zero for an unrelated reason should not be accepted as evidence for a reported exception or crash.

## Highlights

- `exception` targets now require a concrete discriminator: preferably `exception_class`, or a distinctive `stderr_contains` marker.
- `crash` targets now require a signal, exact exit code, or distinctive output marker.
- Linux/container signal matching understands conventional `128 + signal` statuses such as `139` for `SIGSEGV`.
- `nonzero_exit` remains available as an explicit broad target.
- Failure signatures include the observed exception or signal when available.
- The AI planner is told to emit target-specific expectations instead of generic failures.

## Exception example

```yaml
failure:
  type: exception
  exception_class: UnicodeEncodeError
  stderr_contains:
    - UnicodeEncodeError
```

An unrelated `ValueError`, import failure, or syntax error will now fail verification even though the process also exits non-zero.

## Crash example

```yaml
failure:
  type: crash
  signal: 11
```

For Docker/Linux execution this matches the conventional `139` (`128 + 11`) exit status and records `SIGSEGV` in the stable failure signature.

## Compatibility note

Existing capsules that already use `stderr_contains` for exceptions continue to validate. Capsules that used only `type: exception` or only `type: crash` must now state what identifies the target failure. Use `type: nonzero_exit` if broad non-zero matching was actually intended.

See `docs/failure-targets.md` for the full matching model.
