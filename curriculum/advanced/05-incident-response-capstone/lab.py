"""Run the incident-response capstone harness for this lesson."""
from pathlib import Path
import runpy
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "advanced" / "05-incident-response-capstone"))
from agentops_lab.capstone_incident_response import *  # noqa: F401,F403

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parents[2] / "advanced" / "05-incident-response-capstone" / "agentops_lab" / "capstone_incident_response.py"), run_name="__main__")
