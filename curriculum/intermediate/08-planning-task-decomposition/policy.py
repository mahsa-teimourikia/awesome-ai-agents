from pydantic import BaseModel, Field

class SubTask(BaseModel):
    task_id: int = Field(description="The order of execution (1, 2, 3...).")
    description: str = Field(description="The specific action to take.")
    expected_tool: str = Field(description="The tool the worker should probably use.")

class Plan(BaseModel):
    subtasks: list[SubTask] = Field(description="The sequential DAG of subtasks required to achieve the goal.")
