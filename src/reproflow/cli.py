from __future__ import annotations

import json
from pathlib import Path
import re

import yaml

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from reproflow import __version__
from reproflow.agent.planner import ReproductionPlanner
from reproflow.agent.provider import ProviderError
from reproflow.capsule.loader import load_repro_spec
from reproflow.capsule.writer import write_planning_result
from reproflow.doctor import collect_doctor_report
from reproflow.issue.source import IssueSourceError, load_issue_source
from reproflow.minimizer import minimize_text
from reproflow.regression import generate_regression_test
from reproflow.report import load_verification_result, render_verification_markdown, write_verification_report
from reproflow.repo.context import build_repository_snapshot
from reproflow.repo.detector import detect_repository
from reproflow.sandbox.docker import DockerSandboxRunner, DockerUnavailableError
from reproflow.verifier.verifier import Verifier

app = typer.Typer(name="reproflow", help="Turn bug reports into verified reproductions.")
console = Console()


@app.command()
def inspect(
    repo: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Inspect a Python repository using deterministic detection."""
    try:
        profile = detect_repository(repo)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=2) from exc
    if as_json:
        _print_json(profile.model_dump(mode="json"), indent=2, sort_keys=True)
        return
    console.print(f"\n[bold]ReproFlow[/bold] {__version__}\n")
    table = Table(title="Repository", show_header=False)
    table.add_row("Language", profile.language)
    table.add_row("Python", profile.python_version or "unknown")
    table.add_row("Package manager", profile.package_manager or "unknown")
    table.add_row("Test framework", profile.test_framework or "unknown")
    console.print(table)
    if profile.install_command:
        console.print(f"\n[bold]Install[/bold]\n  {profile.install_command}")
    if profile.test_command:
        console.print(f"\n[bold]Test[/bold]\n  {profile.test_command}")


@app.command("context")
def context_command(
    repo: Path = typer.Option(
        Path("."),
        "--repo",
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Python repository to inspect for planner context.",
    ),
    issue: str = typer.Option(
        ...,
        "--issue",
        help="Path to a text/Markdown bug report or a GitHub Issue URL.",
    ),
    github_max_comments: int = typer.Option(
        20,
        "--github-max-comments",
        min=0,
        max=100,
        help="Maximum GitHub Issue comments to load. Use 0 for the issue body only.",
    ),
    max_files: int = typer.Option(
        40,
        "--max-files",
        min=1,
        max=100,
        help="Maximum files in the previewed repository snapshot.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Preview the bounded, issue-aware repository context without AI or Docker."""
    try:
        loaded_issue = load_issue_source(issue, max_comments=github_max_comments)
        snapshot = build_repository_snapshot(
            repo,
            issue_text=loaded_issue.text,
            max_files=max_files,
        )
    except (IssueSourceError, ValueError) as exc:
        console.print(f"[red]Context error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    if as_json:
        payload = {
            "issue_source": loaded_issue.display_name,
            "candidate_count": snapshot.candidate_count,
            "selected_count": len(snapshot.files),
            "truncated": snapshot.truncated,
            "selection_terms": snapshot.selection_terms,
            "files": [
                {
                    "path": name,
                    "score": snapshot.selection_scores.get(name, 0),
                    "chars": len(text),
                }
                for name, text in snapshot.files.items()
            ],
        }
        _print_json(payload, indent=2, sort_keys=True)
        return

    console.print(f"\n[bold]ReproFlow[/bold] {__version__}")
    console.print(f"[bold]Issue source:[/bold] {loaded_issue.display_name}")
    console.print(
        f"[bold]Candidates:[/bold] {snapshot.candidate_count}   "
        f"[bold]Selected:[/bold] {len(snapshot.files)}   "
        f"[bold]Truncated:[/bold] {'yes' if snapshot.truncated else 'no'}"
    )
    if snapshot.selection_terms:
        console.print(
            "[bold]Selection terms:[/bold] " + ", ".join(snapshot.selection_terms)
        )

    table = Table(title="Planner context")
    table.add_column("Score", justify="right")
    table.add_column("File")
    table.add_column("Chars", justify="right")
    for name, text in snapshot.files.items():
        table.add_row(str(snapshot.selection_scores.get(name, 0)), name, str(len(text)))
    console.print(table)
    console.print(
        "\n[dim]Scores are deterministic relevance hints, not evidence that a file causes the bug.[/dim]"
    )


@app.command("doctor")
def doctor_command(
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Check whether the local machine is ready to run ReproFlow."""
    report = collect_doctor_report()
    if as_json:
        _print_json(report.to_dict(), indent=2, sort_keys=True)
        return

    console.print(f"\n[bold]ReproFlow doctor[/bold] {__version__}\n")
    table = Table(show_header=False)
    table.add_row("Python", f"{report.python_version} {'✓' if report.python_supported else '✗'}")
    table.add_row("Docker CLI", "✓" if report.docker_cli else "✗")
    docker_status = "✓" if report.docker_daemon else "✗"
    if report.docker_version:
        docker_status += f" ({report.docker_version})"
    table.add_row("Docker daemon", docker_status)
    table.add_row("OpenAI package", "✓" if report.openai_package else "optional / not installed")
    table.add_row("OPENAI_API_KEY", "set" if report.openai_api_key else "not set")
    table.add_row("GitHub token", "set" if report.github_token else "optional / not set")
    console.print(table)
    if report.runtime_ready:
        console.print("\n[bold green]Runtime ready[/bold green]")
    else:
        console.print("\n[bold yellow]Runtime not ready[/bold yellow]")
        raise typer.Exit(code=1)


@app.command("minimize")
def minimize_command(
    spec_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
    target_file: str = typer.Option(..., "--file", help="Capsule file to minimize."),
    repo: Path | None = typer.Option(
        None,
        "--repo",
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Optional source repository used by the capsule.",
    ),
    output: Path | None = typer.Option(None, "--output", help="Output YAML path."),
    max_checks: int = typer.Option(30, "--max-checks", min=1, max=500),
    min_length: int = typer.Option(1, "--min-length", min=0),
) -> None:
    """Minimize one capsule file while preserving a verified failure."""
    try:
        spec = load_repro_spec(spec_path)
    except (ValidationError, ValueError) as exc:
        console.print(f"[red]INVALID[/red]\n{exc}")
        raise typer.Exit(code=2) from exc

    if target_file not in spec.files:
        available = ", ".join(sorted(spec.files)) or "(none)"
        console.print(f"[red]Unknown capsule file:[/red] {target_file}")
        console.print(f"Available: {available}")
        raise typer.Exit(code=2)

    verifier = Verifier(DockerSandboxRunner(source_root=repo))
    console.print(f"\n[bold]Baseline verification[/bold] {target_file}")
    try:
        baseline = verifier.verify(spec)
    except DockerUnavailableError as exc:
        console.print(f"[red]Docker unavailable:[/red] {exc}")
        raise typer.Exit(code=3) from exc
    except RuntimeError as exc:
        console.print(f"[red]Execution failed:[/red] {exc}")
        raise typer.Exit(code=4) from exc

    if not baseline.reproduced:
        console.print("[red]Refusing to minimize:[/red] baseline capsule is not verified.")
        raise typer.Exit(code=1)

    original = spec.files[target_file]

    def still_reproduces(candidate: str) -> bool:
        candidate_files = dict(spec.files)
        candidate_files[target_file] = candidate
        candidate_spec = spec.model_copy(update={"files": candidate_files})
        return verifier.verify(candidate_spec).reproduced

    try:
        result = minimize_text(
            original,
            still_reproduces,
            max_checks=max_checks,
            min_length=min_length,
        )
    except RuntimeError as exc:
        console.print(f"[red]Execution failed while minimizing:[/red] {exc}")
        raise typer.Exit(code=4) from exc

    minimized_files = dict(spec.files)
    minimized_files[target_file] = result.minimized
    minimized_spec = spec.model_copy(update={"files": minimized_files})
    if output is None:
        output = spec_path.with_name(f"{spec_path.stem}.min{spec_path.suffix}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        yaml.safe_dump(
            minimized_spec.model_dump(mode="json", by_alias=True),
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    console.print("\n[bold green]MINIMIZED[/bold green]")
    console.print(f"Chars: {len(original)} → {len(result.minimized)}")
    console.print(f"Removed: {result.removed_chars} ({result.reduction_ratio:.1%})")
    console.print(f"Verifier checks: {result.checks}/{max_checks}")
    console.print(f"Accepted reductions: {result.accepted_reductions}")
    if result.exhausted_budget:
        console.print("[yellow]Check budget exhausted; result may not be globally minimal.[/yellow]")
    console.print(f"Output: {output}")


@app.command("validate")
def validate_command(
    spec_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Validate a reproflow/v1 YAML reproduction capsule."""
    try:
        spec = load_repro_spec(spec_path)
    except (ValidationError, ValueError) as exc:
        if as_json:
            _print_json({"valid": False, "path": str(spec_path), "error": str(exc)})
            raise typer.Exit(code=2) from exc
        console.print(f"[red]INVALID[/red]\n{exc}")
        raise typer.Exit(code=2) from exc
    if as_json:
        _print_json(
            {
                "valid": True,
                "path": str(spec_path),
                "schema": spec.schema_,
                "id": spec.metadata.id,
                "title": spec.metadata.title,
            },
            ensure_ascii=False,
        )
        return
    console.print(f"[green]VALID[/green] {spec.metadata.id}: {spec.metadata.title}")


@app.command("run")
def run_command(
    spec_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
    repo: Path | None = typer.Option(
        None,
        "--repo",
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Optional source repository to copy into the isolated build context.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Directory for verification.json and report.md evidence.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Execute and verify a reproduction capsule in Docker."""
    try:
        spec = load_repro_spec(spec_path)
    except (ValidationError, ValueError) as exc:
        if as_json:
            _print_json({"status": "INVALID", "error": str(exc)})
            raise typer.Exit(code=2) from exc
        console.print(f"[red]INVALID[/red]\n{exc}")
        raise typer.Exit(code=2) from exc
    if not as_json:
        console.print(f"\n[bold]ReproFlow[/bold] {__version__}")
        console.print(f"[bold]{spec.metadata.title}[/bold]\n")
    verifier = Verifier(DockerSandboxRunner(source_root=repo))
    try:
        result = verifier.verify(spec)
    except DockerUnavailableError as exc:
        if as_json:
            _print_json({"status": "DOCKER_UNAVAILABLE", "error": str(exc)})
            raise typer.Exit(code=3) from exc
        console.print(f"[red]Docker unavailable:[/red] {exc}")
        raise typer.Exit(code=3) from exc
    except RuntimeError as exc:
        if as_json:
            _print_json({"status": "EXECUTION_ERROR", "error": str(exc)})
            raise typer.Exit(code=4) from exc
        console.print(f"[red]Execution failed:[/red] {exc}")
        raise typer.Exit(code=4) from exc
    if output is not None:
        write_verification_report(result, output, title=spec.metadata.title, spec_path=spec_path)
    if as_json:
        payload = result.model_dump(mode="json")
        payload["status"] = "VERIFIED" if result.reproduced else "NOT_REPRODUCED"
        payload["spec"] = str(spec_path)
        _print_json(payload, ensure_ascii=False)
        raise typer.Exit(code=0 if result.reproduced else 1)
    for index, run in enumerate(result.runs, start=1):
        status = "[green]MATCH[/green]" if run.matched else "[red]NO MATCH[/red]"
        code = "timeout" if run.evidence.timed_out else str(run.evidence.exit_code)
        console.print(f"Run {index}/{result.total_runs}: {status} (exit={code})")
        if not run.matched:
            for reason in run.reasons:
                console.print(f"  - {reason}")
    console.print()
    if result.reproduced:
        console.print("[bold green]VERIFIED REPRODUCTION[/bold green]")
        console.print(f"Repeatability: {result.successful_runs}/{result.total_runs}")
        if result.stable_signature:
            console.print(f"Failure signature: {result.stable_signature}")
        raise typer.Exit(code=0)
    console.print("[bold red]NOT REPRODUCED[/bold red]")
    console.print(f"Matched runs: {result.successful_runs}/{result.total_runs}")
    raise typer.Exit(code=1)


@app.command("report")
def report_command(
    evidence: Path = typer.Argument(
        ...,
        exists=True,
        help="Evidence directory or verification.json produced by ReproFlow.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit the stored verification JSON."),
) -> None:
    """Render a saved verification result for humans or CI tooling."""
    path = evidence / "verification.json" if evidence.is_dir() else evidence
    try:
        result = load_verification_result(path)
    except ValueError as exc:
        console.print(f"[red]Report error:[/red] {exc}")
        raise typer.Exit(code=2) from exc
    if as_json:
        _print_json(result.model_dump(mode="json"), ensure_ascii=False, indent=2)
        return
    console.print(render_verification_markdown(result))


@app.command("list")
def list_command(
    root: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """List reproduction capsules discovered below a directory."""
    capsules: list[dict[str, object]] = []
    for path in _discover_capsules(root):
        try:
            spec = load_repro_spec(path)
        except (ValidationError, ValueError) as exc:
            capsules.append({"path": str(path), "valid": False, "error": str(exc)})
            continue
        capsules.append(
            {
                "path": str(path),
                "valid": True,
                "id": spec.metadata.id,
                "title": spec.metadata.title,
                "failure": spec.failure.type,
                "repetitions": spec.verification.repetitions,
            }
        )
    if as_json:
        _print_json(capsules, ensure_ascii=False, indent=2)
        return
    if not capsules:
        console.print("No capsules found.")
        return
    table = Table(title="Reproduction capsules")
    table.add_column("Status")
    table.add_column("ID")
    table.add_column("Failure")
    table.add_column("Path")
    for item in capsules:
        if not item["valid"]:
            table.add_row("[red]INVALID[/red]", "-", "-", str(item["path"]))
        else:
            table.add_row(
                "[green]VALID[/green]",
                str(item["id"]),
                str(item["failure"]),
                str(item["path"]),
            )
    console.print(table)


@app.command("verify-all")
def verify_all_command(
    root: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
    repo: Path | None = typer.Option(
        None,
        "--repo",
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Source repository copied into each sandbox.",
    ),
    stop_on_failure: bool = typer.Option(False, "--stop-on-failure"),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Verify every capsule below a directory and return a CI-friendly summary."""
    entries: list[dict[str, object]] = []
    for path in _discover_capsules(root):
        entry: dict[str, object] = {"path": str(path)}
        try:
            spec = load_repro_spec(path)
            entry["id"] = spec.metadata.id
            entry["title"] = spec.metadata.title
            result = Verifier(DockerSandboxRunner(source_root=repo)).verify(spec)
            entry.update(
                {
                    "status": "VERIFIED" if result.reproduced else "NOT_REPRODUCED",
                    "successful_runs": result.successful_runs,
                    "total_runs": result.total_runs,
                    "stable_signature": result.stable_signature,
                }
            )
            if stop_on_failure and not result.reproduced:
                entries.append(entry)
                break
        except (ValidationError, ValueError) as exc:
            entry.update({"status": "INVALID", "error": str(exc)})
        except DockerUnavailableError as exc:
            entry.update({"status": "DOCKER_UNAVAILABLE", "error": str(exc)})
            entries.append(entry)
            break
        except RuntimeError as exc:
            entry.update({"status": "EXECUTION_ERROR", "error": str(exc)})
        entries.append(entry)

    failed = [entry for entry in entries if entry.get("status") != "VERIFIED"]
    if as_json:
        _print_json(
            {
                "total": len(entries),
                "passed": len(entries) - len(failed),
                "failed": len(failed),
                "capsules": entries,
            },
            ensure_ascii=False,
            indent=2,
        )
    else:
        for entry in entries:
            status = entry.get("status", "UNKNOWN")
            console.print(f"{status:18} {entry['path']}")
        console.print(f"\nPassed: {len(entries) - len(failed)}/{len(entries)}")
    if failed:
        raise typer.Exit(code=1)


@app.command("init")
def init_command(
    path: Path = typer.Argument(Path("repro.yaml"), help="Capsule path to create."),
    capsule_id: str | None = typer.Option(None, "--id", help="Capsule identifier."),
    title: str = typer.Option("Reproduction capsule", "--title", help="Human-readable title."),
    image: str = typer.Option("python:3.12-slim", "--image", help="Docker image."),
) -> None:
    """Create a valid starter capsule that can be edited and verified immediately."""
    if path.exists():
        console.print(f"[red]Refusing to overwrite existing file:[/red] {path}")
        raise typer.Exit(code=2)
    inferred = re.sub(r"[^A-Za-z0-9._-]+", "-", path.stem).strip("-._") or "reproduction"
    from reproflow.capsule.schema import Metadata, Environment, FailureExpectation, ReproSpec, RunSpec
    from reproflow.capsule.writer import write_repro_spec

    spec = ReproSpec(
        schema="reproflow/v1",
        metadata=Metadata(id=capsule_id or inferred, title=title),
        environment=Environment(image=image),
        files={"repro.py": "raise RuntimeError('replace with the failing case')\n"},
        run=RunSpec(command="python repro.py", timeout_seconds=30),
        failure=FailureExpectation(type="exception", exception_class="RuntimeError"),
    )
    write_repro_spec(spec, path)
    console.print(f"[green]Created[/green] {path}")
    console.print("Edit repro.py and run: reproflow run " + str(path))


@app.command("generate-regression")
def generate_regression_command(
    spec_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
    output: Path | None = typer.Option(None, "--output", help="Generated pytest path."),
    repo: Path | None = typer.Option(
        None,
        "--repo",
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Source repository root used by the capsule.",
    ),
    verify: bool = typer.Option(
        True,
        "--verify",
        "--no-verify",
        help="Verify before generating.",
    ),
) -> None:
    """Generate a reviewable pytest regression test from a reproduction capsule."""
    try:
        spec = load_repro_spec(spec_path)
    except (ValidationError, ValueError) as exc:
        console.print(f"[red]INVALID[/red]\n{exc}")
        raise typer.Exit(code=2) from exc
    source_root = repo or spec_path.parent
    if verify:
        try:
            result = Verifier(DockerSandboxRunner(source_root=repo)).verify(spec)
        except DockerUnavailableError as exc:
            console.print(f"[red]Docker unavailable:[/red] {exc}")
            raise typer.Exit(code=3) from exc
        except RuntimeError as exc:
            console.print(f"[red]Execution failed:[/red] {exc}")
            raise typer.Exit(code=4) from exc
        if not result.reproduced:
            console.print("[red]Refusing to generate:[/red] capsule is not verified.")
            raise typer.Exit(code=1)
    if output is None:
        output = source_root / "tests" / f"test_reproflow_{_slug(spec.metadata.id)}.py"
    generated = generate_regression_test(spec, output, repo_root=source_root)
    console.print(f"[green]Generated regression test:[/green] {generated}")


@app.command("reproduce")
def reproduce_command(
    repo: Path = typer.Option(
        Path("."),
        "--repo",
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Python repository to reproduce the bug against.",
    ),
    issue: str = typer.Option(
        ...,
        "--issue",
        help="Path to a text/Markdown bug report or a GitHub Issue URL.",
    ),
    provider: str = typer.Option(
        "openai", "--provider", help="Agent provider (currently: openai)."
    ),
    model: str = typer.Option("gpt-5.6-luna", "--model", help="Provider model name."),
    max_attempts: int = typer.Option(5, "--max-attempts", min=1, max=20),
    repetitions: int = typer.Option(3, "--repetitions", min=1, max=20),
    github_max_comments: int = typer.Option(
        20,
        "--github-max-comments",
        min=0,
        max=100,
        help="Maximum GitHub Issue comments to load. Use 0 to load the issue body only.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Evidence output directory. Defaults to .repro/<experiment-id-or-issue>.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Turn a local or GitHub bug report into bounded experiments and verified evidence."""
    if provider != "openai":
        if as_json:
            _print_json({"status": "UNKNOWN_PROVIDER", "error": provider})
            raise typer.Exit(code=2)
        console.print(f"[red]Unknown provider:[/red] {provider}")
        raise typer.Exit(code=2)

    try:
        loaded_issue = load_issue_source(issue, max_comments=github_max_comments)
    except IssueSourceError as exc:
        if as_json:
            _print_json({"status": "ISSUE_SOURCE_ERROR", "error": str(exc)})
            raise typer.Exit(code=2) from exc
        console.print(f"[red]Issue source error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    if not as_json:
        console.print(f"[bold]Issue source:[/bold] {loaded_issue.display_name}")

    try:
        from reproflow.agent.openai_provider import OpenAIProvider

        agent_provider = OpenAIProvider(model=model)
        planner = ReproductionPlanner(
            agent_provider,
            max_attempts=max_attempts,
            repetitions=repetitions,
        )
        result = planner.reproduce(repo_root=repo, issue_text=loaded_issue.text)
    except ProviderError as exc:
        if as_json:
            _print_json({"status": "PROVIDER_ERROR", "error": str(exc)})
            raise typer.Exit(code=5) from exc
        console.print(f"[red]Provider error:[/red] {exc}")
        raise typer.Exit(code=5) from exc
    except DockerUnavailableError as exc:
        if as_json:
            _print_json({"status": "DOCKER_UNAVAILABLE", "error": str(exc)})
            raise typer.Exit(code=3) from exc
        console.print(f"[red]Docker unavailable:[/red] {exc}")
        raise typer.Exit(code=3) from exc
    except RuntimeError as exc:
        if as_json:
            _print_json({"status": "EXECUTION_ERROR", "error": str(exc)})
            raise typer.Exit(code=4) from exc
        console.print(f"[red]Execution failed:[/red] {exc}")
        raise typer.Exit(code=4) from exc

    if output is None:
        if result.final_spec is not None:
            name = result.final_spec.metadata.id
        else:
            name = loaded_issue.slug
        output = repo / ".repro" / name

    repro_path = write_planning_result(result, output)
    if as_json:
        payload = result.model_dump(mode="json")
        payload["output"] = str(output)
        payload["capsule"] = str(repro_path) if repro_path is not None else None
        _print_json(payload, ensure_ascii=False)
    else:
        console.print(f"\n[bold]Result:[/bold] {result.status}")
        console.print(f"Attempts: {len(result.history.attempts)}/{max_attempts}")
        if result.message:
            console.print(result.message)
        console.print(f"Evidence: {output}")
        if repro_path is not None:
            console.print(f"Capsule: {repro_path}")
            console.print(f"Re-run: reproflow run {repro_path} --repo {repo}")
    if result.status == "VERIFIED":
        raise typer.Exit(code=0)
    if result.status == "NEEDS_INFORMATION":
        raise typer.Exit(code=2)
    raise typer.Exit(code=1)


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")
    return (slug or "capsule")[:100]


def _discover_capsules(root: Path) -> list[Path]:
    skip = {".git", ".venv", "venv", "node_modules", ".pytest_cache", ".repro", ".reproflow"}
    paths: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".yaml", ".yml"}:
            continue
        relative = path.relative_to(root)
        if any(part in skip for part in relative.parts):
            continue
        if path.stem.startswith("repro") or path.name.endswith(".repro.yaml"):
            paths.append(path)
    return sorted(paths, key=lambda path: str(path.relative_to(root)))


def _print_json(value: object, **kwargs: object) -> None:
    """Write JSON without Rich's terminal line wrapping corrupting long strings."""
    typer.echo(json.dumps(value, **kwargs))


if __name__ == "__main__":
    app()
