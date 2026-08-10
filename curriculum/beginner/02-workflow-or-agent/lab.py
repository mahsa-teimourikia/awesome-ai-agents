"""Run the workflow-versus-agent comparison used by this lesson."""
from pathlib import Path
import runpy
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))
from agentops_lab.workflow_or_agent import *  # noqa: F401,F403

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parents[2] / "shared" / "agentops_lab" / "workflow_or_agent.py"), run_name="__main__")
