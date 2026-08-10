"""Run the state and memory experiment used by this lesson."""
from pathlib import Path
import runpy
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))
from agentops_lab.state_memory_langgraph import *  # noqa: F401,F403

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parents[2] / "shared" / "agentops_lab" / "state_memory_langgraph.py"), run_name="__main__")
