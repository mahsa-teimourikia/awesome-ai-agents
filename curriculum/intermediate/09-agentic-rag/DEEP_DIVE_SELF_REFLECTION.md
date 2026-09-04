# Deep dive: corrective and self-reflective retrieval

Retrieval evaluators can signal that evidence is missing, irrelevant, stale, or conflicting. That signal may justify a bounded corrective action; it is not ground truth and must not create an open-ended loop.

## Corrective RAG (CRAG)

The [CRAG paper](https://arxiv.org/abs/2401.15884) introduces a lightweight retrieval evaluator that assigns a confidence signal to retrieved documents. Different confidence regions trigger different knowledge-retrieval actions. The paper also explores web search as an extension to a limited static corpus and a decompose-then-recompose step that filters retrieved information.

That research architecture does **not** imply a universal three-label LangGraph recipe or “bad internal retrieval → always search the web.” In an operational system, corrective actions are policy-dependent:

- use a different approved internal source;
- rewrite once within a query-rewrite budget;
- run a bounded graph or structured lookup for a named evidence gap;
- use an approved, minimized public-web query only after egress checks; or
- abstain when evidence or budget remains insufficient.

Course 09 expresses correction as `EvidenceGap → one allowed retrieval → re-evaluate`. The deterministic sufficiency gate can identify missing incident, dependency, or mitigation evidence, staleness, and conflict without asking the producing model whether it “feels confident.”

## Self-RAG

The original [Self-RAG paper](https://arxiv.org/abs/2310.11511) trains a language model to retrieve on demand, generate, and critique retrieved passages and its generations using special reflection tokens. Those tokens provide inference-time control over retrieval and generation behavior.

Self-RAG is not simply a prompt that emits canonical hidden XML tags such as `<is_relevant>` or `<is_supported>`, and the paper does not promise perfectly supported output. Its reported results are empirical results for the studied models, datasets, and metrics. A production team must reproduce evaluation on its own domain and deployment.

## Reflection is a fallible signal

A model-based retriever judge can fail because it:

- shares biases or missing knowledge with the generator;
- accepts a relevant passage that does not entail the claim;
- follows an instruction embedded in retrieved content;
- overlooks stale or cross-tenant evidence;
- becomes poorly calibrated after corpus/model changes.

Use deterministic checks where possible: source allowlists, tenant binding, evidence IDs, version matching, freshness windows, typed gaps, citation completeness, and hard budgets. Calibrate semantic graders against labeled examples and record retriever/judge disagreement for review.

## Bounded controller pattern

```text
retrieve approved initial sources
    ↓
evaluate typed evidence gap
    ├── sufficient → verify claims/citations → answer
    ├── named repair + budget → one corrective retrieval → re-evaluate
    ├── conflict → one reconciliation retrieval or state uncertainty
    └── no budget / unresolved gap → abstain
```

Enforce `max_query_rewrites`, `max_corrective_retrievals`, `max_hops`, query count, web count, cost, and deadline in application code. A prompt requesting “no more than two tries” is not a control boundary.

## Optional LangGraph adapter

LangGraph is a widely used open-source framework for representing conditional state transitions, persistence, and interrupts. It can adapt the pattern above into nodes such as `retrieve_initial`, `evaluate_gap`, `retrieve_dependency`, `verify_citations`, and `abstain`.

Keep the important rules outside the graph adapter:

- trusted `RetrievalContext` and source registry;
- tenant, authorization, data-classification, and web-egress checks;
- budget admission;
- evidence sufficiency and freshness;
- claim/evidence and citation verification;
- approval gating for consequential actions.

The graph helps orchestrate the controller. It does not make retrieval correct or safe by itself.

## Evaluation

Evaluate the complete trajectory, not only final answer quality:

- gap classification precision/recall;
- unnecessary corrective retrievals;
- required-evidence recall gained per extra query;
- stale/conflict detection;
- citation completeness and unsupported claim rate;
- latency/cost distributions and budget exhaustion;
- tenant violations, web exfiltration, and unsafe action attempts;
- abstention quality when evidence cannot be repaired.

More reflection is not automatically better. The useful question is whether a bounded evaluator improves evidence-grounded outcomes enough to justify its additional failure modes, latency, and cost.
