from pydantic import BaseModel, Field

class EvaluationScore(BaseModel):
    is_correct: bool = Field(description="True if the agent accurately answered the user's intent. False otherwise.")
    justification: str = Field(description="A 1-sentence explanation of why you gave this score.")

class TrajectoryScore(BaseModel):
    is_efficient: bool = Field(description="True if the agent solved the problem without redundant or hallucinated tool calls.")
    penalty_reason: str = Field(default="None")
