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

The runtime, not an LLM, decides whether the reproduction is verified.
