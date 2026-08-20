from reproflow.doctor import DoctorReport


def test_runtime_ready_requires_python_and_docker() -> None:
    report = DoctorReport(
        python_version="3.12.1",
        python_supported=True,
        docker_cli=True,
        docker_daemon=True,
        docker_version="27.0.0",
        openai_package=False,
        openai_api_key=False,
        github_token=False,
    )
    assert report.runtime_ready is True
    assert report.to_dict()["runtime_ready"] is True
