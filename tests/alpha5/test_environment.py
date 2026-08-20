from reproflow.alpha5.environment import build_environment_fingerprint


def test_environment_fingerprint_is_stable_shape(tmp_path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    value = build_environment_fingerprint(tmp_path)
    assert len(value.fingerprint) == 16
    assert value.python
    assert "pyproject.toml" in value.lock_files
