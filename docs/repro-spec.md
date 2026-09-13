# reproflow/v1 draft specification

`reproflow/v1` is a minimal, executable description of a bug reproduction.

A capsule declares:

- metadata: identity and source
- environment: runtime container image
- setup: commands baked into an ephemeral image
- files: reproduction source files
- run: the command and timeout
- failure: what evidence counts as the target failure
- verification: how many repetitions must match

An environment may also declare literal variables that are passed only to the reproduction
process:

```yaml
environment:
  image: python:3.12-slim
  variables:
    LC_ALL: C.UTF-8
```

Capsule file paths are relative POSIX paths. Absolute paths, parent-directory traversal,
backslashes, NUL bytes, and empty names are rejected before Docker is invoked.

The runtime, not an LLM, decides whether the reproduction is verified.

## Failure targets

A failure target should be specific enough to distinguish the reported bug from an unrelated experiment failure. In v0.1.0, `exception` and `crash` targets are therefore validated more strictly:

```yaml
failure:
  type: exception
  exception_class: UnicodeEncodeError
```

or:

```yaml
failure:
  type: crash
  signal: 11
```

`nonzero_exit` remains available when any non-zero command status is intentionally the target. See [failure-targets.md](failure-targets.md) for matching rules and examples.

For successful commands whose output is wrong, use `output_mismatch` with one or more of
`stdout_equals`, `stderr_equals`, `stdout_not_contains`, and `stderr_not_contains`.
