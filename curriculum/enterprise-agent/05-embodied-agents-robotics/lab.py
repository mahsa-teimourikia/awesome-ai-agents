"""Safe, deterministic embodied-agent simulation; it controls no physical hardware."""
from dataclasses import dataclass
@dataclass
class RobotState: object_seen:bool=True; clear_path:bool=True; force_newtons:float=0.0; holding:bool=False; events:list[str]=None
def run_demo():
 s=RobotState(events=[]); s.events += ["sense: red bin detected", "plan: navigate then pick", "safety: workspace-clear"]
 if not s.clear_path or s.force_newtons>10: s.events.append("stop-and-escalate"); return s
 s.events += ["act: bounded navigation", "observe: at bin", "act: low-force grasp", "observe: grasp verified"]; s.holding=True; assert s.holding; return s
if __name__=="__main__": print("\n".join(run_demo().events))
