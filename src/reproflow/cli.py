from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from reproflow import __version__
from reproflow.agent.planner import ReproductionPlanner
from reproflow.agent.provider import ProviderError
from reproflow.capsule.loader import load_repro_spec
from reproflow.capsule.writer import write_planning_result
from reproflow.issue.source import IssueSourceError, load_issue_source
from reproflow.repo.detector import detect_repository
from reproflow.sandbox.docker import DockerSandboxRunner, DockerUnavailableError
from reproflow.verifier.verifier import Verifier

app = typer.Typer(name="reproflow", help="Turn bug reports into verified reproductions.")
console = Console()


@app.command()
def inspect(
    repo: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
) -> None:
    """Inspect a Python repository using deterministic detection."""
    try:
        profile = detect_repository(repo)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=2) from exc
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


@app.command("validate")
def validate_command(
    spec_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
) -> None:
    """Validate a reproflow/v1 YAML reproduction capsule."""
    try:
        spec = load_repro_spec(spec_path)
    except (ValidationError, ValueError) as exc:
        console.print(f"[red]INVALID[/red]\n{exc}")
        raise typer.Exit(code=2) from exc
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
) -> None:
    """Execute and verify a reproduction capsule in Docker."""
    try:
        spec = load_repro_spec(spec_path)
    except (ValidationError, ValueError) as exc:
        console.print(f"[red]INVALID[/red]\n{exc}")
        raise typer.Exit(code=2) from exc
    console.print(f"\n[bold]ReproFlow[/bold] {__version__}")
    console.print(f"[bold]{spec.metadata.title}[/bold]\n")
    verifier = Verifier(DockerSandboxRunner(source_root=repo))
    try:
        result = verifier.verify(spec)
    except DockerUnavailableError as exc:
        console.print(f"[red]Docker unavailable:[/red] {exc}")
        raise typer.Exit(code=3) from exc
    except RuntimeError as exc:
        console.print(f"[red]Execution failed:[/red] {exc}")
        raise typer.Exit(code=4) from exc
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
) -> None:
    """Turn a local or GitHub bug report into bounded experiments and verified evidence."""
    if provider != "openai":
        console.print(f"[red]Unknown provider:[/red] {provider}")
        raise typer.Exit(code=2)

    try:
        loaded_issue = load_issue_source(issue, max_comments=github_max_comments)
    except IssueSourceError as exc:
        console.print(f"[red]Issue source error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

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
        console.print(f"[red]Provider error:[/red] {exc}")
        raise typer.Exit(code=5) from exc
    except DockerUnavailableError as exc:
        console.print(f"[red]Docker unavailable:[/red] {exc}")
        raise typer.Exit(code=3) from exc
    except RuntimeError as exc:
        console.print(f"[red]Execution failed:[/red] {exc}")
        raise typer.Exit(code=4) from exc

    if output is None:
        if result.final_spec is not None:
            name = result.final_spec.metadata.id
        else:
            name = loaded_issue.slug
        output = repo / ".repro" / name

    repro_path = write_planning_result(result, output)
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


if __name__ == "__main__":
    app()
