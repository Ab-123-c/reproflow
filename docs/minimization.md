# Verified testcase minimization

`reproflow minimize` is a bounded delta-debugging-style reducer for a file embedded in a `reproflow/v1` capsule.

The minimizer does **not** decide by syntax, model judgment, or a changed exit code alone. It uses the existing deterministic Verifier as its oracle:

1. Load the capsule.
2. Verify the original capsule first.
3. Delete a bounded chunk from the selected file.
4. Execute the candidate in the normal Docker sandbox.
5. Accept the deletion only if the configured failure expectation is still reproduced.
6. Repeat until no more deletion is accepted at the current granularity or the check budget is exhausted.

This means minimization can be slow: each check may run the capsule multiple times according to its `verification.repetitions` policy. That cost is intentional because a smaller testcase is useful only if it still carries executable evidence.

## Example

```bash
reproflow minimize examples/unicode-username/repro.yaml \
  --file repro.py \
  --max-checks 40
```

For a capsule that needs a source repository:

```bash
reproflow minimize .repro/issue-123/repro.yaml \
  --file repro.py \
  --repo . \
  --max-checks 30
```

By default a `repro.yaml` input produces `repro.min.yaml`. Use `--output` to choose another path.

## Bounds

- `--max-checks` limits how many candidate reductions can invoke the Verifier.
- `--min-length` prevents the selected file from being reduced below a chosen character count.
- The baseline must already be verified. ReproFlow refuses to minimize a capsule that does not reproduce before reduction starts.

## Security boundary

The selected capsule file remains untrusted input. Candidate contents are never executed directly on the host by the minimizer; they flow through the same sandbox runner and Verifier used by `reproflow run`.
