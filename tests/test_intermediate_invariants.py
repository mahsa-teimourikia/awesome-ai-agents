import pytest
import sys
import os
import importlib.util
from pydantic import ValidationError

def get_policy(course_dir: str):
    module_name = f"policy_{course_dir.replace('/', '_')}"
    file_path = os.path.join(os.getcwd(), course_dir, "policy.py")
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    policy = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = policy
    spec.loader.exec_module(policy)
    return policy

def test_course_01_refund_input():
    policy = get_policy('curriculum/intermediate/01-tool-engineering')
    RefundInput = policy.RefundInput

    # Valid
    valid = RefundInput(user_id=123, amount=50.0, reason="defective")
    assert valid.amount == 50.0

def test_course_03_human_approval():
    policy = get_policy('curriculum/intermediate/03-human-approval-permissions')
    RefundInput = policy.RefundInput
    process_refund_safe = policy.process_refund_safe

    req = RefundInput(user_id=123, amount=50.0, idempotency_key="unique_key_1")
    
    # Success first time
    res1 = process_refund_safe(user_id=req.user_id, amount=req.amount, idempotency_key=req.idempotency_key)
    assert res1 == "Refund processed successfully."

    # Idempotent success second time
    res2 = process_refund_safe(user_id=req.user_id, amount=req.amount, idempotency_key=req.idempotency_key)
    assert res2 == "Refund already processed (Idempotent success)."

def test_course_04_customer_response():
    policy = get_policy('curriculum/intermediate/04-guardrails-untrusted-content')
    CustomerResponse = policy.CustomerResponse

    # Valid
    valid = CustomerResponse(tone="polite", message="We apologize for the issue.")
    assert valid.tone == "polite"

    # Competitor mention
    with pytest.raises(ValidationError, match="Message contains a mention of a competitor"):
        CustomerResponse(tone="polite", message="We are better than competitor_a")

    # Invalid tone
    with pytest.raises(ValidationError, match="Unacceptable tone"):
        CustomerResponse(tone="angry", message="We apologize for the issue.")

def test_course_05_agent_evaluation():
    policy = get_policy('curriculum/intermediate/05-agent-evaluation')
    EvaluationScore = policy.EvaluationScore
    TrajectoryScore = policy.TrajectoryScore

    # Just testing schema initialization
    eval_score = EvaluationScore(is_correct=True, justification="Good job")
    assert eval_score.is_correct

    traj_score = TrajectoryScore(is_efficient=False, penalty_reason="Too many loops")
    assert not traj_score.is_efficient

def test_course_08_planning():
    policy = get_policy('curriculum/intermediate/08-planning-task-decomposition')
    SubTask = policy.SubTask
    Plan = policy.Plan

    task = SubTask(task_id=1, description="Do work", expected_tool="web_search")
    plan = Plan(subtasks=[task])
    assert len(plan.subtasks) == 1
    assert plan.subtasks[0].task_id == 1
