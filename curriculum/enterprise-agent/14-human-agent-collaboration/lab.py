"""Risk-tiered human-agent collaboration controller."""
from dataclasses import dataclass
@dataclass
class Case: risk:str; confidence:float; action:str
def oversight(c:Case)->dict:
 mode={"low":"autonomous-assist","medium":"monitor-and-notify","high":"approval-required","critical":"human-decision"}[c.risk]
 if c.confidence<.65 and c.risk in {"medium","high"}: mode="escalate-human"
 return {"mode":mode,"explanation":f"{c.action}; confidence={c.confidence}","audit":True}
def run_demo():
 x=oversight(Case("high",.82,"prepare rollback")); assert x["mode"]=="approval-required"; return x
if __name__=="__main__": print(run_demo())
