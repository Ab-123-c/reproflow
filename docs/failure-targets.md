# Failure target hardening

ReproFlow verifies a **target failure**, not merely a failing command.

`reproflow/v1` keeps `nonzero_exit` as an explicit broad matcher, while v0.1.0 hardens the two failure types that are most likely to produce false positives:

- `exception` must include `exception_class` or at least one `stderr_contains` marker.
- `crash` must include `signal`, `exit_code`, or a distinctive stdout/stderr marker.

## Exception identity

Prefer an explicit exception class when the bug report names one:

```yaml
failure:
  type: exception
  exception_class: UnicodeEncodeError
```

You can combine it with text markers when the message itself is part of the target:

```yaml
failure:
  type: exception
  exception_class: ValueError
  stderr_contains:
    - invalid header length
```

The verifier extracts the final Python-style exception name from stderr and requires it to match. A different exception with the same non-zero exit status is rejected.

## Crash signal

For Linux-style process crashes, capsules can identify the signal explicitly:

```yaml
failure:
  type: crash
  signal: 11  # SIGSEGV; conventional container exit status 139
```

The verifier recognizes both negative subprocess return codes and conventional `128 + signal` container exit statuses.

## Broad non-zero failures

If *any* failing command is genuinely the condition you want to verify, say that explicitly:

```yaml
failure:
  type: nonzero_exit
```

That keeps broad matching available without silently treating a generic `exception` or `crash` as proof of a specific bug.

## Why this matters

A generated experiment can fail for unrelated reasons: import errors, syntax errors, missing fixtures, packaging mistakes, or resource limits. Those failures are evidence that the experiment failed, but they are not automatically evidence that the reported bug reproduced.

## Output mismatches

Some regressions do not crash; they return successfully with incorrect output. Use an
`output_mismatch` target to express that contract:

```yaml
failure:
  type: output_mismatch
  stdout_equals: "expected stable output\n"
```

The target matches only when the command exits with code `0` and the observed output differs
from the declared value. `stdout_not_contains` and `stderr_not_contains` are useful when a
specific leaked or malformed value must be absent.
