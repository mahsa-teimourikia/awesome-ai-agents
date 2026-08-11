"""Deterministic digital-twin-style counterfactual planner."""
from dataclasses import dataclass
@dataclass(frozen=True)
class State: conversion:float; error_rate:float; confidence:float
def predict(s:State, action:str)->State:
 if action=="rollback": return State(.97,.01,.82)
 if action=="route_traffic": return State(.91,.04,.72)
 return State(s.conversion,s.error_rate,.35)
def plan(s:State):
 candidates={a:predict(s,a) for a in ("rollback","route_traffic","wait")}; choice=max(candidates,key=lambda a:(candidates[a].conversion-candidates[a].error_rate)*candidates[a].confidence); return choice,candidates
def run_demo():
 choice,c=plan(State(.69,.12,.88)); assert choice=="rollback"; return choice,c
if __name__=="__main__": print(run_demo())
