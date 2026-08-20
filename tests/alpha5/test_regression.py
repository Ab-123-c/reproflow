from reproflow.alpha5.regression import generate_regression_test


def test_generate_regression_from_repro_yaml(tmp_path) -> None:
    capsule = tmp_path / "capsule"
    capsule.mkdir()
    (capsule / "repro.yaml").write_text("run:\n  command: python repro.py\n", encoding="utf-8")
    (capsule / "repro.py").write_text("print('ok')\n", encoding="utf-8")
    output = tmp_path / "tests" / "test_issue_1.py"
    generated = generate_regression_test(capsule, output, issue="issue-1")
    text = generated.output_path.read_text(encoding="utf-8")
    assert "def test_issue_1" in text
    assert "python repro.py" in text
