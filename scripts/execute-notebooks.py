#!/usr/bin/env python3
"""Execute every credential-free course notebook in a real Jupyter kernel.

The curriculum notebooks, the scenario-first tracks, and the local use cases
share the same import and fixture contracts. Keeping all of them in this runner
makes a folder restructuring observable in CI rather than only in a learner's
local Jupyter session.
"""

from __future__ import annotations

import argparse
import time
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError


ROOT = Path(__file__).resolve().parents[1]
TRACKS = ("beginner", "intermediate", "advanced", "enterprise", "evaluation", "adaptive-rag")


def notebook_paths(track_filter: str | None = None) -> list[Path]:
    paths = []
    
    # 1. Scenario Tracks
    scenario_tracks = ("enterprise", "evaluation", "adaptive-rag")
    if not track_filter or track_filter in scenario_tracks:
        targets = [track_filter] if track_filter else scenario_tracks
        for track in targets:
            paths.extend(sorted((ROOT / "notebooks" / track).glob("*.ipynb")))
            
    # 2. Curriculum
    curriculum_tracks = ("beginner", "intermediate", "advanced")
    if not track_filter or track_filter in curriculum_tracks:
        targets = [track_filter] if track_filter else curriculum_tracks
        for track in targets:
            paths.extend(sorted((ROOT / "curriculum" / track).glob("*/*.ipynb")))
            
    # 3. Use Cases
    if not track_filter:
        paths.extend(sorted((ROOT / "use-cases").glob("*/*.ipynb")))
        
    return paths


def execute(path: Path, timeout: int) -> tuple[str, float, str]:
    """Execute a notebook and return (status, runtime, error_msg)."""
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
    except CellExecutionError as e:
        runtime = time.time() - start_time
        cell_index = getattr(e, 'exec_count', 'Unknown')
        error_msg = f"Cell {cell_index}: {e.ename}: {e.evalue}"
        print(f"\n[FAILED] {path.relative_to(ROOT)}")
        print(f"  {error_msg}")
        return ("FAIL", runtime, error_msg)
    except Exception as e:
        runtime = time.time() - start_time
        error_msg = f"Unexpected Error: {e}"
        print(f"\n[FAILED] {path.relative_to(ROOT)}")
        print(f"  {error_msg}")
        return ("FAIL", runtime, error_msg)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=90, help="per-cell timeout in seconds")
    parser.add_argument("--list", action="store_true", help="print the CI notebook manifest without executing it")
    parser.add_argument("--track", choices=TRACKS, help="Filter to only run a specific track")
    parser.add_argument("paths", nargs="*", type=Path, help="Specific notebook files or directories to execute")
    args = parser.parse_args()
    
    if args.paths:
        paths = []
        for p in args.paths:
            if p.is_file() and p.suffix == ".ipynb":
                paths.append(p.resolve())
            elif p.is_dir():
                paths.extend(sorted([f.resolve() for f in p.rglob("*.ipynb")]))
    else:
        paths = notebook_paths(args.track)

    if not paths:
        raise SystemExit("No notebook execution targets found")
    if args.list:
        print("\n".join(str(path.relative_to(ROOT)) for path in paths))
        return
        
    results = []
    failed = False
    
    for index, path in enumerate(paths, start=1):
        print(f"[{index}/{len(paths)}] execute {path.relative_to(ROOT)}", flush=True)
        status, runtime, error_msg = execute(path, args.timeout)
        results.append((path.relative_to(ROOT), status, runtime, error_msg))
        if status == "FAIL":
            failed = True
            
    print(f"\nExecuted {len(paths)} credential-free course notebooks.")
    
    # Write summary report
    summary_path = ROOT / "notebook_execution_summary.md"
    with open(summary_path, "w") as f:
        f.write("# Notebook Execution Summary\n\n")
        f.write("| Course / Notebook | Result | Runtime (s) | Error |\n")
        f.write("| --- | --- | --- | --- |\n")
        for path, status, runtime, error_msg in results:
            icon = "✅" if status == "PASS" else "❌"
            safe_error = error_msg.replace("|", "\\|").replace("\n", " ") if error_msg else ""
            f.write(f"| `{path}` | {icon} {status} | {runtime:.1f} | {safe_error} |\n")
            
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
