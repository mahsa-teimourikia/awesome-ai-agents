"""Run the single-agent and specialist-team comparison for this lesson."""
from pathlib import Path
import runpy
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "advanced" / "05-incident-response-capstone"))
from agentops_lab.multi_agent_team import *  # noqa: F401,F403

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parents[2] / "advanced" / "05-incident-response-capstone" / "agentops_lab" / "multi_agent_team.py"), run_name="__main__")
