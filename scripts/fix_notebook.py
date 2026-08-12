import json
import sys

file_path = "curriculum/advanced/03-agentic-rag/03_agentic_rag.ipynb"
with open(file_path, "r") as f:
    nb = json.load(f)

for cell in nb.get("cells", []):
    if cell["cell_type"] == "code":
        source = "".join(cell["source"])
        if "from langchain_community.llms.fake import FakeListLLM" in source:
            new_source = source.replace("from langchain_community.llms.fake import FakeListLLM\n", "").replace("from langchain_core.language_models.chat_models import BaseChatModel", "from langchain_core.language_models.chat_models import BaseChatModel\nfrom langchain_core.outputs import ChatResult, ChatGeneration")
            cell["source"] = [line + "\n" for line in new_source.split("\n")]
            cell["source"][-1] = cell["source"][-1].rstrip("\n")
        elif "class MockToolCallingLLM(FakeListLLM, BaseChatModel):" in source:
            new_source = source.replace("class MockToolCallingLLM(FakeListLLM, BaseChatModel):", "class MockToolCallingLLM(BaseChatModel):")
            new_source = new_source.replace('return type("ChatResult", (object,), {"generations": [type("ChatGeneration", (object,), {"message": msg})]})()', 'return ChatResult(generations=[ChatGeneration(message=msg)])')
            new_source = new_source.replace("return type('ChatResult', (object,), {'generations': [type('ChatGeneration', (object,), {'message': msg})]})()", "return ChatResult(generations=[ChatGeneration(message=msg)])")
            new_source = new_source.replace("def bind_tools(self, tools, **kwargs):", "@property\n    def _llm_type(self) -> str:\n        return \"mock_tool_calling_llm\"\n\n    def bind_tools(self, tools, **kwargs):")
            new_source = new_source.replace("llm = MockToolCallingLLM(responses=[])", "llm = MockToolCallingLLM()")
            
            cell["source"] = [line + "\n" for line in new_source.split("\n")]
            cell["source"][-1] = cell["source"][-1].rstrip("\n")

with open(file_path, "w") as f:
    json.dump(nb, f, indent=1)
    f.write("\n")
