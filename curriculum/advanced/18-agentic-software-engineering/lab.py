"""Deterministic coding-agent harness that prepares, but never merges, a patch."""
from dataclasses import dataclass, field
@dataclass
class Run: issue:str; plan:list[str]=field(default_factory=list); changed:list[str]=field(default_factory=list); tests:list[str]=field(default_factory=list); events:list[str]=field(default_factory=list); pr_ready:bool=False
def understand(r): r.plan=["search payment routing", "inspect EU mapping validation", "add regression test", "run focused suite"]; r.events.append("repo-search: payment region mapping")
def edit(r): r.changed=["src/region_mapping.py", "tests/test_region_mapping.py"]; r.events.append("sandbox-edit: minimal validation patch")
def test(r): r.tests=["test_eu_mapping_rejects_mismatch: PASS", "test_checkout_contract: PASS"]; r.events.append("sandbox-test: focused suite passed")
def review(r):
    if not r.tests or "tests/test_region_mapping.py" not in r.changed: raise RuntimeError("Patch lacks test evidence")
    r.pr_ready=True; r.events.append("review: evidence-backed PR draft; CI/human merge required")
def run_demo():
 r=Run("EU checkout accepts incompatible provider-region mapping"); understand(r); edit(r); test(r); review(r); assert r.pr_ready and all("PASS" in x for x in r.tests); return r
if __name__=="__main__": print("\n".join(run_demo().events))
