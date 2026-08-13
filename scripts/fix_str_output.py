import json
import sys

file_path = "curriculum/intermediate/04-evaluation/01_building_eval_datasets.ipynb"
with open(file_path, "r") as f:
    nb = json.load(f)

for cell in nb.get("cells", []):
    if cell["cell_type"] == "code":
        source = "".join(cell["source"])
        if "from langchain_core.output_parsers import JsonOutputParser" in source:
            new_source = source.replace("from langchain_core.output_parsers import JsonOutputParser", "from langchain_core.output_parsers import JsonOutputParser, StrOutputParser")
            cell["source"] = [line + "\n" for line in new_source.split("\n")]
            cell["source"][-1] = cell["source"][-1].rstrip("\n")

with open(file_path, "w") as f:
    json.dump(nb, f, indent=1)
    f.write("\n")
