# Deep Dive: Judge Biases

LLMs are not objective math functions. They inherit massive biases from their pre-training data. When using an LLM-as-a-Judge, you must design your evaluation harness to mitigate these biases.

## 1. Position Bias
When doing Pairwise Evaluation ("Which is better, Answer A or Answer B?"), LLMs have a strong tendency to prefer **Answer A**, simply because it appeared first in the context window. 

**Mitigation:** You must run every pairwise evaluation *twice*.
- Run 1: `Prompt(A, B)` -> LLM chooses A.
- Run 2: `Prompt(B, A)` -> LLM chooses A (which was originally B).
If the LLM flips its answer based on position, the result is a **Tie**. You can only declare a winner if the LLM chooses the *content* regardless of its position.

## 2. Verbosity Bias
LLMs equate "longer" with "better." If Answer A is a concise, mathematically perfect 2-sentence response, and Answer B is a 5-paragraph essay containing subtle hallucinations, the LLM Judge will often score Answer B higher.

**Mitigation:** The rubric must explicitly penalize unnecessary verbosity. You must add an anchor: *"If the answer exceeds 3 sentences for a simple query, deduct 1 point."*

## 3. Self-Enhancement Bias
If you use GPT-4 to generate Answer A, and Claude to generate Answer B, and then use GPT-4 as the Judge... GPT-4 will prefer Answer A. LLMs prefer the style, cadence, and formatting of their own outputs.

**Mitigation:** Always use a different model family for the Judge than the one that generated the agent's output. If your Agent is powered by Claude, your Judge should be GPT-4 or Gemini.
