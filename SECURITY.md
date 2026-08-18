# Security Policy

ReproFlow processes untrusted repository content, issue text, model output, and reproduction code.

## Current alpha security boundary

- Issue text and repository snapshots are treated as data, not agent instructions.
- The model can propose experiments but cannot declare a reproduction successful.
- Generated experiment files are restricted to `.reproflow/experiments/` and cannot overwrite copied source files.
- The reproduction phase runs without network access, with a read-only root filesystem, dropped Linux capabilities, `no-new-privileges`, CPU/memory/PID limits, and a timeout.
- Host secrets and the Docker socket are not mounted into the reproduction container.

The dependency/setup phase is currently performed during `docker build` and may have network access. A malicious repository can therefore execute package build logic inside that build environment. Do not pass secrets through Docker build args, build secrets, capsule files, or environment variables. Future releases should further isolate dependency acquisition from untrusted build hooks.

For security-sensitive reports, avoid filing a public proof-of-concept that exposes real credentials or private data. Use GitHub private vulnerability reporting when enabled for the repository.
