from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from reproflow import __version__
from reproflow.capsule.loader import load_repro_spec
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
) -> None:
    """Execute and verify a reproduction capsule in Docker."""
    try:
        spec = load_repro_spec(spec_path)
    except (ValidationError, ValueError) as exc:
        console.print(f"[red]INVALID[/red]\n{exc}")
        raise typer.Exit(code=2) from exc

    console.print(f"\n[bold]ReproFlow[/bold] {__version__}")
    console.print(f"[bold]{spec.metadata.title}[/bold]\n")

    verifier = Verifier(DockerSandboxRunner())
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


if __name__ == "__main__":
    app()
