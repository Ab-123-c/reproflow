# ReproFlow v0.1.0-alpha.5

Alpha 5 adds a maintainer-facing reproduction lifecycle layer without replacing the existing reproduction engine.

## Added in Alpha 5

- **Run history** in `.reproflow/history.json`, with per-run artifact directories.
- **Repro Score** (0–100) for repeatability, minimality, environment locking, failure precision, and portability.
- **Environment fingerprinting** based on Python/runtime metadata, installed packages, and lock-file hashes.
- **Generic regression-test generation** from a Reproduction Capsule.
- **Alpha 5 utility CLI** available as `python -m reproflow.alpha5.cli`.

## Commands

```bash
python -m reproflow.alpha5.cli fingerprint . --output .repro/environment.json

python -m reproflow.alpha5.cli score .repro/issue-1842 \
  --runs 3 \
  --matching-failures 3 \
  --source-size 120 \
  --minimized-size 8 \
  --failure-signature UnicodeEncodeError

python -m reproflow.alpha5.cli regression .repro/issue-1842 \
  --issue issue-1842 \
  --output tests/regression/test_issue_1842.py

python -m reproflow.alpha5.cli record \
  --issue "unicode parser crash" \
  --status VERIFIED \
  --runs 3 \
  --successful-runs 3 \
  --score 96 \
  --capsule .repro/issue-1842

python -m reproflow.alpha5.cli history
```

## Recommended integration into the existing `reproflow` CLI

Keep Alpha 5's implementation under `reproflow.alpha5` and have the existing CLI delegate to these functions. This avoids duplicating storage and score logic while preserving Alpha 1–4 behavior.

Suggested top-level commands:

```text
reproflow history
reproflow fingerprint
reproflow score <capsule>
reproflow regression <capsule>
```

## Definition of done

Alpha 5 is ready to tag when:

1. Existing Alpha 1–4 tests still pass.
2. `pytest tests/alpha5 -q` passes.
3. A real reproduction capsule receives an environment fingerprint and a Repro Score.
4. A regression test can be generated from that capsule.
5. A successful or failed run can be recorded and shown by `history`.
