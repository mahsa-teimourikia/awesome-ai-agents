"""Run the tool-contract and error-handling scenarios for this lesson."""
from pathlib import Path
import runpy
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))
from agentops_lab.tool_engineering import *  # noqa: F401,F403

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parents[2] / "shared" / "agentops_lab" / "tool_engineering.py"), run_name="__main__")
