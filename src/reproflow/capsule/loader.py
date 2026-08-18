from pathlib import Path

import yaml

from .schema import ReproSpec


def load_repro_spec(path: Path) -> ReproSpec:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("repro.yaml must contain a YAML mapping")
    return ReproSpec.model_validate(data)
