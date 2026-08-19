# Security Policy

ReproFlow processes untrusted repository content, issue text, model output, and reproduction code.

## Current alpha security boundary

- Issue text, GitHub Issue bodies/comments, and repository snapshots are treated as data, not agent instructions.
- GitHub Issue ingestion accepts only `https://github.com/<owner>/<repo>/issues/<number>` and constructs requests to `api.github.com` internally.
- GitHub input is size-bounded before it reaches the planner; comments are capped by count and per-comment length.
- Repository context selection treats Issue terms only as bounded relevance hints; they cannot expand eligible file types/directories or execute repository code.
- Repository context scanning is bounded by candidate count, per-file scan length, selected-file count, and total selected characters.
- `GH_TOKEN` / `GITHUB_TOKEN` are used only as GitHub API authorization headers and are not intentionally copied into planner text or reproduction capsules.
- The model can propose experiments but cannot declare a reproduction successful.
- Generated experiment files are restricted to `.reproflow/experiments/` and cannot overwrite copied source files.
- The reproduction phase runs without network access, with a read-only root filesystem, dropped Linux capabilities, `no-new-privileges`, CPU/memory/PID limits, and a timeout.
- Host secrets and the Docker socket are not mounted into the reproduction container.

The GitHub Issue fetch occurs in the host CLI process before sandbox execution. The dependency/setup phase is currently performed during `docker build` and may have network access. A malicious repository can therefore execute package build logic inside that build environment. Do not pass secrets through Docker build args, build secrets, capsule files, or environment variables. Future releases should further isolate dependency acquisition from untrusted build hooks.

For security-sensitive reports, avoid filing a public proof-of-concept that exposes real credentials or private data. Use GitHub private vulnerability reporting when enabled for the repository.
