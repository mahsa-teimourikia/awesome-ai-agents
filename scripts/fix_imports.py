import json
import sys
import glob

def fix_notebook(file_path):
    with open(file_path, "r") as f:
        nb = json.load(f)

    changed = False
    for cell in nb.get("cells", []):
        if cell["cell_type"] == "code":
            source = "".join(cell["source"])
            new_source = source
            if "from langchain.retrievers import EnsembleRetriever" in new_source:
                new_source = new_source.replace("from langchain.retrievers import EnsembleRetriever", "from langchain.retrievers.ensemble import EnsembleRetriever")
                changed = True
            if "from langchain.retrievers import ContextualCompressionRetriever" in new_source:
                new_source = new_source.replace("from langchain.retrievers import ContextualCompressionRetriever", "from langchain.retrievers.contextual_compression import ContextualCompressionRetriever")
                changed = True
                
            if changed and source != new_source:
                cell["source"] = [line + "\n" for line in new_source.split("\n")]
                cell["source"][-1] = cell["source"][-1].rstrip("\n")

    if changed:
        with open(file_path, "w") as f:
            json.dump(nb, f, indent=1)
            f.write("\n")
        print(f"Fixed {file_path}")

for file_path in glob.glob("curriculum/**/*.ipynb", recursive=True):
    fix_notebook(file_path)
