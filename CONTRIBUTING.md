# Contributing to ReproFlow

Thanks for helping improve ReproFlow.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/unit -q
```

Before opening a pull request, validate and verify the checked-in capsules:

```bash
reproflow list .
reproflow verify-all . --repo .
```

Please keep changes focused, add tests for behavior changes, and describe the evidence your change adds or improves.
