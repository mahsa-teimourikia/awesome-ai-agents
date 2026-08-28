from pydantic import BaseModel, Field, model_validator
from typing import Literal, List, Set

class SubTask(BaseModel):
    task_id: int = Field(description="The order of execution (1, 2, 3...).")
    description: str = Field(description="The specific action to take.")
    expected_tool: Literal["web_search", "calculator", "database_query"] = Field(description="The tool the worker should probably use.")
    dependencies: List[int] = Field(default_factory=list, description="IDs of tasks that must be completed before this task.")

class Plan(BaseModel):
    subtasks: list[SubTask] = Field(description="The sequential DAG of subtasks required to achieve the goal.")

    @model_validator(mode='after')
    def validate_dag(self):
        task_ids = set()
        for task in self.subtasks:
            if task.task_id in task_ids:
                raise ValueError(f"Duplicate task ID: {task.task_id}")
            task_ids.add(task.task_id)
            
        for task in self.subtasks:
            for dep in task.dependencies:
                if dep not in task_ids:
                    raise ValueError(f"Task {task.task_id} depends on missing task {dep}")
                if dep == task.task_id:
                    raise ValueError(f"Task {task.task_id} depends on itself")
        
        # Check for cycles
        visited = set()
        path = set()
        
        def visit(task_id: int):
            if task_id in path:
                raise ValueError("Cycle detected in plan DAG")
            if task_id in visited:
                return
                
            path.add(task_id)
            task_node = next(t for t in self.subtasks if t.task_id == task_id)
            for dep in task_node.dependencies:
                visit(dep)
            path.remove(task_id)
            visited.add(task_id)
            
        for task in self.subtasks:
            visit(task.task_id)
            
        return self
