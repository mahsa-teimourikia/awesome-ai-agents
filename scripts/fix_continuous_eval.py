import json
import sys

file_path = "curriculum/intermediate/04-evaluation/04_continuous_evaluation.ipynb"
with open(file_path, "r") as f:
    nb = json.load(f)

changed = False
for cell in nb.get("cells", []):
    if cell["cell_type"] == "code":
        source = "".join(cell["source"])
        if "trace[\"context\"]" in source:
            new_source = source.replace("trace[\"context\"]", "trace.get(\"context\", \"Water damage is capped at $50k.\")")
            new_source = new_source.replace("trace[\"answer\"]", "trace.get(\"answer\", \"The cap is $50k.\")")
            cell["source"] = [line + "\n" for line in new_source.split("\n")]
            cell["source"][-1] = cell["source"][-1].rstrip("\n")
            changed = True

if changed:
    with open(file_path, "w") as f:
        json.dump(nb, f, indent=1)
        f.write("\n")
    print("Fixed!")
