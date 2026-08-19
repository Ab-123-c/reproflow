# ReproFlow v0.1.0-alpha.4 — Issue-aware Repository Context

The fourth alpha improves what the planner sees before it proposes experiments. Instead of taking the first structurally convenient Python files, ReproFlow now ranks a bounded repository snapshot against the untrusted bug report.

## Highlights

- Repository context selection is deterministic and issue-aware.
- Project metadata remains structurally prioritized.
- Relevant Python source and test files can be promoted when bounded Issue terms match their paths, filenames, or a bounded prefix of their contents.
- Snapshot construction now records selection terms, per-file scores, total candidate count, and whether a bound truncated the result.
- Candidate scanning itself is bounded, in addition to existing selected-file and character budgets.
- `.git`, virtual environments, caches, `.repro`, `.reproflow`, and `node_modules` remain excluded.
- `reproflow context` previews the exact selected file list without initializing an AI provider or starting Docker.
- The reproduction planner uses the same issue-aware selector, so the preview and actual planner path share one implementation.

## Example

```bash
reproflow context \
  --repo . \
  --issue https://github.com/OWNER/REPO/issues/123
```

Example output includes a deterministic score beside each selected file. The score is only a relevance heuristic for context allocation. It is not evidence that the file caused the bug.

Then run the normal reproduction loop:

```bash
reproflow reproduce \
  --repo . \
  --issue https://github.com/OWNER/REPO/issues/123 \
  --max-attempts 5
```

Issue text and repository contents remain untrusted data. The selector does not execute repository code, and the deterministic Verifier remains the only component allowed to declare a reproduction successful.
