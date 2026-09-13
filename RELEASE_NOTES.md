# ReproFlow v0.1.0 — Maintainer workflow and CI readiness

This iteration turns the alpha runtime into a practical maintainer workflow. Capsules can be
scaffolded, discovered, batch-verified, exported as stable JSON, and converted into reviewable
pytest regression tests. Each verification can also produce a Markdown evidence report.

See [`CHANGELOG.md`](CHANGELOG.md) for the complete list of changes.

## Failure Target Hardening

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
