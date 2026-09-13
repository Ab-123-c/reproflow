from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import ALPHA_VERSION
from .environment import build_environment_fingerprint, write_environment_fingerprint
from .history import HistoryStore, RunRecord, RunStatus
from .regression import generate_regression_test
from .score import ScoreInput, calculate_repro_score


def _capsule_score_input(capsule: Path, args: argparse.Namespace) -> ScoreInput:
    source_size = args.source_size
    minimized_size = args.minimized_size
    has_env_fp = (capsule / "environment.json").exists()
    has_env_lock = any((capsule / name).exists() for name in ("Dockerfile", "uv.lock", "requirements.txt"))
    has_runner = any((capsule / name).exists() for name in ("repro.yaml", "repro.json", "reproduce.sh"))
    has_signature = bool(args.failure_signature) or (capsule / "actual.txt").exists()
    return ScoreInput(
        total_runs=args.runs,
        matching_failures=args.matching_failures,
        source_size=source_size,
        minimized_size=minimized_size,
        has_environment_fingerprint=has_env_fp,
        has_environment_lock=has_env_lock,
        has_stable_failure_signature=has_signature,
        has_portable_runner=has_runner,
    )


def cmd_history(args: argparse.Namespace) -> int:
    records = HistoryStore(args.repo).list(limit=args.limit)
    if not records:
        print("No ReproFlow runs recorded yet.")
        return 0
    print("Reproduction History\n")
    for record in records:
        score = f" | Score: {record.score}/100" if record.score is not None else ""
        print(f"#{record.run_id} {record.status.value}")
        print(f"Issue: {record.issue}")
        print(f"Runs: {record.successful_runs}/{record.runs}{score}")
        if record.failure_signature:
            print(f"Signature: {record.failure_signature}")
        print()
    return 0


def cmd_fingerprint(args: argparse.Namespace) -> int:
    if args.output:
        result = write_environment_fingerprint(args.repo, args.output)
    else:
        result = build_environment_fingerprint(args.repo)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"Environment fingerprint: {result.fingerprint}")
        print(f"Python: {result.python}")
        print(f"OS: {result.os}")
        print(f"Dependencies: {len(result.dependencies)}")
        print(f"Lock files: {len(result.lock_files)}")
        if args.output:
            print(f"Written: {args.output}")
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    capsule = Path(args.capsule).resolve()
    result = calculate_repro_score(_capsule_score_input(capsule, args))
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"Repro Score: {result.total}/100\n")
        print(f"Repeatability      {result.repeatability:>2}/30")
        print(f"Minimality         {result.minimality:>2}/20")
        print(f"Environment lock   {result.environment_lock:>2}/20")
        print(f"Failure precision  {result.failure_precision:>2}/20")
        print(f"Portability        {result.portability:>2}/10")
    return 0


def cmd_regression(args: argparse.Namespace) -> int:
    result = generate_regression_test(args.capsule, args.output, issue=args.issue)
    print(f"Regression test generated: {result.output_path}")
    print(f"Command: {result.command}")
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    store = HistoryStore(args.repo)
    run_id = args.run_id or store.next_run_id()
    status = RunStatus(args.status)
    record = RunRecord(
        run_id=run_id,
        issue=args.issue,
        status=status,
        runs=args.runs,
        successful_runs=args.successful_runs,
        failure_signature=args.failure_signature,
        score=args.score,
        environment_hash=args.environment_hash,
        model=args.model,
        capsule_path=args.capsule,
    )
    store.append(record)
    print(f"Recorded run #{record.run_id}: {record.status.value}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="reproflow-alpha5", description="ReproFlow Alpha 5 utilities")
    parser.add_argument("--version", action="version", version=ALPHA_VERSION)
    sub = parser.add_subparsers(dest="command", required=True)

    p_history = sub.add_parser("history", help="Show reproduction history")
    p_history.add_argument("--repo", default=".")
    p_history.add_argument("--limit", type=int, default=20)
    p_history.set_defaults(func=cmd_history)

    p_fp = sub.add_parser("fingerprint", help="Fingerprint the current environment")
    p_fp.add_argument("repo", nargs="?", default=".")
    p_fp.add_argument("--output")
    p_fp.add_argument("--json", action="store_true")
    p_fp.set_defaults(func=cmd_fingerprint)

    p_score = sub.add_parser("score", help="Calculate a Repro Score")
    p_score.add_argument("capsule")
    p_score.add_argument("--runs", type=int, default=3)
    p_score.add_argument("--matching-failures", type=int, default=3)
    p_score.add_argument("--source-size", type=int)
    p_score.add_argument("--minimized-size", type=int)
    p_score.add_argument("--failure-signature")
    p_score.add_argument("--json", action="store_true")
    p_score.set_defaults(func=cmd_score)

    p_reg = sub.add_parser("regression", help="Generate a pytest regression test")
    p_reg.add_argument("capsule")
    p_reg.add_argument("--issue", default="reproduction")
    p_reg.add_argument("--output", default="tests/regression/test_reproduction.py")
    p_reg.set_defaults(func=cmd_regression)

    p_record = sub.add_parser("record", help="Append a run to .reproflow/history.json")
    p_record.add_argument("--repo", default=".")
    p_record.add_argument("--run-id")
    p_record.add_argument("--issue", required=True)
    p_record.add_argument("--status", choices=[s.value for s in RunStatus], required=True)
    p_record.add_argument("--runs", type=int, default=0)
    p_record.add_argument("--successful-runs", type=int, default=0)
    p_record.add_argument("--failure-signature")
    p_record.add_argument("--score", type=int)
    p_record.add_argument("--environment-hash")
    p_record.add_argument("--model")
    p_record.add_argument("--capsule")
    p_record.set_defaults(func=cmd_record)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
