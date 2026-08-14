# Deep Dive: Public Benchmarks

The AI industry is flooded with leaderboards. A foundational model provider will claim they achieve "State of the Art on SWE-bench". 

It is critical for enterprise engineers to understand what these benchmarks actually measure, and why a high score does NOT equal production readiness.

## Major Public Benchmarks

### 1. SWE-bench
**What it measures:** An agent is given a GitHub issue and a codebase, and must generate a patch that passes the repository's unit tests.
**The Catch:** Real enterprise software engineering is rarely just about passing unit tests. It involves negotiating with stakeholders, interpreting vague JIRA tickets, and understanding unwritten architectural guidelines. A high SWE-bench score proves coding capability, but not operational autonomy.

### 2. WebArena
**What it measures:** An agent must navigate a simulated e-commerce or forum website using browser automation, filling out forms and clicking buttons to achieve a goal.
**The Catch:** The simulated websites in WebArena are static. Real websites have A/B tests, CAPTCHAs, cookie banners, and rapidly changing DOMs. A 90% score on WebArena often translates to a 20% success rate on the live internet.

### 3. τ-bench (Tau-Bench)
**What it measures:** Customer service tool usage. The agent must interact with a simulated database (e.g., flight bookings) and adhere strictly to a company policy document.
**The Catch:** This is the closest to an enterprise scenario, but the mocked databases do not simulate the latency, 500 errors, or rate limits that cause agents to enter destructive retry-loops in production.

## The Data Contamination Problem
The biggest risk with public benchmarks is **Data Contamination**. Because SWE-bench is built from public GitHub issues, those issues were likely in the training data of the LLM itself. The model might not be "reasoning" through the bug fix; it might just be reciting the patch it memorized during pre-training.

This is why enterprises must build their own custom, private benchmarks.
