# ReproFlow v0.1.0-alpha.5 — Verified Testcase Minimization

The fifth alpha adds ReproFlow's first deterministic testcase minimizer. The important rule stays unchanged: a smaller testcase is accepted only when the normal sandbox + Verifier path proves that the target failure still reproduces.

## Highlights

- `reproflow minimize` reduces one file embedded in a verified `reproflow/v1` capsule.
- A baseline verification runs first; unverified capsules are refused.
- Every candidate reduction is executed again through Docker and checked by the deterministic Verifier.
- Minimization is bounded with `--max-checks` and `--min-length`.
- The original capsule is not overwritten unless you explicitly choose the same output path.
- `reproflow doctor` checks local runtime readiness before a reproduction run.
- `reproflow inspect --json`, `reproflow context --json`, and `reproflow doctor --json` make the CLI easier to consume from scripts and CI.

## Minimize a verified capsule

```bash
reproflow minimize examples/unicode-username/repro.yaml \
  --file repro.py \
  --max-checks 40
```

The default output is `repro.min.yaml` beside the source capsule. Re-run it normally:

```bash
reproflow run examples/unicode-username/repro.min.yaml
```

For capsules that depend on a source repository, pass the same repository to the minimizer:

```bash
reproflow minimize path/to/repro.yaml \
  --file repro.py \
  --repo .
```

## Check a Codespace or workstation

```bash
reproflow doctor
reproflow doctor --json
```

`OPENAI_API_KEY` and a GitHub token are optional for the deterministic runtime. Docker is required for `run`, `reproduce`, and `minimize`.

## Machine-readable inspection

```bash
reproflow inspect . --json
reproflow context --repo . --issue issue.md --json
```

The JSON paths are intended for automation. They do not change the evidence model: context scores are only selection hints, and only the Verifier can declare a reproduction successful.
