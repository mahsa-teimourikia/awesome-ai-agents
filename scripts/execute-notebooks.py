#!/usr/bin/env python3
"""Execute canonical credential-free course notebooks in a real Jupyter kernel."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError


ROOT = Path(__file__).resolve().parents[1]
TRACKS = ("beginner", "intermediate", "advanced")


def notebook_paths(track_filter: str | None = None) -> list[Path]:
    """Return the canonical curriculum notebook manifest."""
    tracks = (track_filter,) if track_filter else TRACKS
    return [
        path
        for track in tracks
        for path in sorted((ROOT / "curriculum" / track).glob("*/*.ipynb"))
    ]


def execute(path: Path, timeout: int) -> tuple[str, float, str]:
    """Execute a notebook and return (status, runtime, error message)."""
    notebook = nbformat.read(path, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=timeout,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
        allow_errors=False,
    )
    start_time = time.time()
    try:
        client.execute()
        return ("PASS", time.time() - start_time, "")
    except CellExecutionError as error:
        runtime = time.time() - start_time
        cell_index = getattr(error, "exec_count", "Unknown")
        message = f"Cell {cell_index}: {error.ename}: {error.evalue}"
        print(f"\n[FAILED] {path.relative_to(ROOT)}\n  {message}")
        return ("FAIL", runtime, message)
    except Exception as error:  # pragma: no cover - diagnostic boundary
        runtime = time.time() - start_time
        message = f"Unexpected Error: {error}"
        print(f"\n[FAILED] {path.relative_to(ROOT)}\n  {message}")
        return ("FAIL", runtime, message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=90, help="per-cell timeout in seconds")
    parser.add_argument("--list", action="store_true", help="print the notebook manifest")
    parser.add_argument("--track", choices=TRACKS, help="run one curriculum track")
    parser.add_argument("--exclude", action="append", default=[], help="exclude path substrings")
    parser.add_argument("paths", nargs="*", type=Path, help="specific notebooks or directories")
    args = parser.parse_args()

    if args.paths:
        paths: list[Path] = []
        for target in args.paths:
            if target.is_file() and target.suffix == ".ipynb":
                paths.append(target.resolve())
            elif target.is_dir():
                paths.extend(sorted(path.resolve() for path in target.rglob("*.ipynb")))
    else:
        paths = notebook_paths(args.track)

    paths = list(dict.fromkeys(path for path in paths if not any(
        exclusion in str(path) for exclusion in args.exclude
    )))
    if not paths:
        raise SystemExit("No notebook execution targets found")

    if args.list:
        print("\n".join(str(path.relative_to(ROOT)) for path in paths))
        return

    results = []
    failed = False
    for index, path in enumerate(paths, start=1):
        print(f"[{index}/{len(paths)}] execute {path.relative_to(ROOT)}", flush=True)
        status, runtime, message = execute(path, args.timeout)
        results.append((path.relative_to(ROOT), status, runtime, message))
        failed |= status == "FAIL"

    print(f"\nExecuted {len(paths)} credential-free course notebooks.")

    summary_path = ROOT / "notebook_execution_summary.md"
    with summary_path.open("w", encoding="utf-8") as summary:
        summary.write("# Notebook Execution Summary\n\n")
        summary.write("| Course / Notebook | Result | Runtime (s) | Error |\n")
        summary.write("| --- | --- | --- | --- |\n")
        for path, status, runtime, message in results:
            icon = "✅" if status == "PASS" else "❌"
            safe_message = message.replace("|", "\\|").replace("\n", " ") if message else ""
            summary.write(f"| `{path}` | {icon} {status} | {runtime:.1f} | {safe_message} |\n")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
