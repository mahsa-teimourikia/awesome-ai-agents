import json
import sys

file_path = "curriculum/intermediate/06-qdrant-local/06_qdrant_local.ipynb"
with open(file_path, "r") as f:
    nb = json.load(f)

changed = False
for cell in nb.get("cells", []):
    if cell["cell_type"] == "code":
        source = "".join(cell["source"])
        if "qdrant = QdrantVectorStore(" in source:
            # Replace the instantiation and add_documents
            new_source = source.replace(
"""# LangChain integration for Qdrant
qdrant = QdrantVectorStore(
    client=client, 
    collection_name=\"support_docs\", 
    embedding=embeddings
)

# Add documents
qdrant.add_documents(corpus)
print(\"Documents indexed into Qdrant in-memory collection.\")""", 
"""# LangChain integration for Qdrant
# from_documents automatically creates the collection and indexes the data
qdrant = QdrantVectorStore.from_documents(
    corpus,
    embeddings,
    location=\":memory:\",
    collection_name=\"support_docs\",
)
print(\"Documents indexed into Qdrant in-memory collection.\")"""
            )
            if new_source != source:
                cell["source"] = [line + "\n" for line in new_source.split("\n")]
                cell["source"][-1] = cell["source"][-1].rstrip("\n")
                changed = True

if changed:
    with open(file_path, "w") as f:
        json.dump(nb, f, indent=1)
        f.write("\n")
    print("Fixed!")
else:
    print("Not changed.")
