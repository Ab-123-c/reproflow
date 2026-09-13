from pathlib import Path

from reproflow.capsule.loader import load_repro_spec
from reproflow.regression import generate_regression_test


def test_generated_regression_test_is_valid_python(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    spec = load_repro_spec(root / "examples" / "unicode-username" / "repro.yaml")
    output = tmp_path / "tests" / "test_generated.py"
    generate_regression_test(spec, output, repo_root=tmp_path)
    compile(output.read_text(encoding="utf-8"), str(output), "exec")
    assert "DockerSandboxRunner" in output.read_text(encoding="utf-8")
