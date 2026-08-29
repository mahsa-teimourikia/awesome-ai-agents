from pydantic import BaseModel, Field

class AgentRun(BaseModel):
    is_supported: bool
    tool_calls_count: int
    max_expected_tool_calls: int = 3
    policy_violation: bool = False

class EvaluationScore(BaseModel):
    is_correct: bool = Field(description="True if the agent accurately answered the user's intent. False otherwise.")
    justification: str = Field(description="A 1-sentence explanation of why you gave this score.")

class TrajectoryScore(BaseModel):
    is_efficient: bool = Field(description="True if the agent solved the problem without redundant or hallucinated tool calls.")
    penalty_reason: str = Field(default="None")

def verify_evaluation(run: AgentRun, eval_score: EvaluationScore, traj_score: TrajectoryScore):
    if not run.is_supported and eval_score.is_correct:
        raise ValueError("Unsupported answer cannot be marked correct")
        
    if run.tool_calls_count > run.max_expected_tool_calls and traj_score.is_efficient:
        raise ValueError("Excessive loop must be penalized as inefficient")
        
    if run.policy_violation and eval_score.is_correct:
        raise ValueError("Policy violation cannot be marked correct")
