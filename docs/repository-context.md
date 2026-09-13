# Issue-aware repository context

ReproFlow does not send an entire repository to an agent provider. It builds a bounded snapshot of selected files.

In `v0.1.2`, selection can use the bug report itself as an **untrusted relevance hint**. The issue text never becomes an instruction and it never causes repository code to execute.

## Selection rules

The selector considers Python files plus a small set of project metadata files. It skips generated or sensitive working directories such as `.git`, virtual environments, caches, `.repro`, `.reproflow`, and `node_modules`.

Selection is deterministic:

1. project metadata such as `pyproject.toml`, `requirements.txt`, pytest configuration, and README files receives structural priority;
2. `src/` and `tests/` receive a baseline source/test priority;
3. bounded terms extracted from the Issue can raise a file's score when they match its path, filename, or a bounded prefix of its contents;
4. the final snapshot still obeys file-count, per-file, total-character, candidate-scan, and content-scan limits.

The selector does not execute imports, inspect Python objects, call Git, or run repository commands.

## Previewing context

Use the `context` command to see which files ReproFlow would expose to the planner without making an AI request and without starting Docker:

```bash
reproflow context \
  --repo . \
  --issue issue.md
```

GitHub Issue URLs work too:

```bash
reproflow context \
  --repo . \
  --issue https://github.com/OWNER/REPO/issues/123
```

The output lists the selected files and their deterministic ranking scores. Scores are an internal relevance heuristic, not a statement that a file is responsible for the bug.

## Threat model

Issue text and repository contents remain untrusted data. A malicious Issue can try to mention filenames repeatedly, but it can only influence which already-eligible text files are included inside fixed bounds. It cannot expand the allowed file types/directories, execute code, disable sandbox restrictions, or declare a reproduction successful.
