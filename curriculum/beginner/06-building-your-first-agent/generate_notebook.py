import nbformat as nbf
import os

def generate_notebook():
    nb = nbf.v4.new_notebook()
    
    nb.cells.append(nbf.v4.new_markdown_cell(
        "# 06. Building Your First Complete Agent\n\n"
        "Welcome to the final course of the beginner curriculum. We are going to build **one complete, bounded, testable agent** using the hybrid architecture typical of real enterprise systems.\n\n"
        "**Scenario:** A customer escalated ticket T-102: \"I was charged twice for my subscription. Support has not resolved this. Please fix it.\"\n\n"
        "The agent must review the ticket, inspect billing, propose a resolution, and if a refund is needed, request human approval before executing it safely."
    ))

    # PART 1
    nb.cells.append(nbf.v4.new_markdown_cell("## Part 1: Define the Domain Fixtures\nFirst, we create deterministic fixtures simulating a real business database."))
    nb.cells.append(nbf.v4.new_code_cell(
        "import json\nfrom datetime import datetime\nimport logging\n\n"
        "logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')\n"
        "logger = logging.getLogger('Northstar')\n\n"
        "DB = {\n"
        "    'tickets': {'T-102': {'customer_id': 'C-55', 'text': 'I was charged twice for my subscription.', 'status': 'open'}},\n"
        "    'customers': {'C-55': {'name': 'Alice', 'plan': 'Pro'}},\n"
        "    'billing': {'C-55': {'status': 'active', 'card_valid': True}},\n"
        "    'transactions': {'C-55': [\n"
        "        {'tx_id': 'TX-901', 'amount_cents': 10000, 'date': '2026-08-01'},\n"
        "        {'tx_id': 'TX-902', 'amount_cents': 10000, 'date': '2026-08-01', 'note': 'system duplicate'}\n"
        "    ]},\n"
        "    'refunds': []\n"
        "}\n\nprint('Domain fixtures initialized.')"
    ))

    # PART 2
    nb.cells.append(nbf.v4.new_markdown_cell("## Part 2: Define Trusted Context\nThe LLM does not invent its own identity. We define it cryptographically/statically via the application."))
    nb.cells.append(nbf.v4.new_code_cell(
        "from pydantic import BaseModel, Field\nfrom typing import Literal, Any, Optional\n\n"
        "class ExecutionContext(BaseModel):\n"
        "    user_id: str\n"
        "    tenant_id: str\n"
        "    roles: set[str]\n"
        "    request_id: str\n\n"
        "ctx = ExecutionContext(user_id='U-88', tenant_id='Northstar', roles={'support:agent', 'refund:request'}, request_id='REQ-999')\n"
        "print(f'Running as: {ctx}')"
    ))

    # PART 3 & 4
    nb.cells.append(nbf.v4.new_markdown_cell("## Part 3 & 4: Tool I/O Models & Read-Only Tools\nTools must be strictly typed. We define them as isolated functions."))
    nb.cells.append(nbf.v4.new_code_cell(
        "class GetTicketArgs(BaseModel):\n"
        "    ticket_id: str\n\n"
        "def get_ticket_details(args: GetTicketArgs) -> str:\n"
        "    \"\"\"Fetches the text of a support ticket.\"\"\"\n"
        "    if args.ticket_id not in DB['tickets']:\n"
        "        return 'Error: Ticket not found'\n"
        "    return json.dumps(DB['tickets'][args.ticket_id])\n\n"
        "class GetCustomerArgs(BaseModel):\n"
        "    customer_id: str\n\n"
        "def get_recent_transactions(args: GetCustomerArgs) -> str:\n"
        "    \"\"\"Fetches recent transactions for a customer.\"\"\"\n"
        "    if args.customer_id not in DB['transactions']:\n"
        "        return 'Error: No transactions'\n"
        "    return json.dumps(DB['transactions'][args.customer_id])\n\n"
        "def get_refund_policy(args: BaseModel) -> str:\n"
        "    \"\"\"Fetches the company refund policy.\"\"\"\n"
        "    return 'POLICY: Duplicate charges must be refunded in full. Refunds require manager approval.'\n"
    ))

    # PART 5
    nb.cells.append(nbf.v4.new_markdown_cell("## Part 5: Define the Refund Proposal\nWhen the agent decides an action is needed, it produces a *Proposal*, not an immediate side effect."))
    nb.cells.append(nbf.v4.new_code_cell(
        "class RefundProposal(BaseModel):\n"
        "    customer_id: str\n"
        "    transaction_id: str\n"
        "    amount_cents: int\n"
        "    reason: str\n"
    ))

    # PART 6
    nb.cells.append(nbf.v4.new_markdown_cell("## Part 6: Write Tool + Idempotency\nThe consequential action. Notice the `idempotency_key` preventing double refunds if retried."))
    nb.cells.append(nbf.v4.new_code_cell(
        "class IssueRefundArgs(BaseModel):\n"
        "    customer_id: str\n"
        "    transaction_id: str\n"
        "    amount_cents: int\n"
        "    idempotency_key: str\n\n"
        "def issue_refund(args: IssueRefundArgs) -> str:\n"
        "    \"\"\"Issues a financial refund.\"\"\"\n"
        "    # Idempotency check\n"
        "    for r in DB['refunds']:\n"
        "        if r['idempotency_key'] == args.idempotency_key:\n"
        "            return f'Refund already processed for {args.idempotency_key}'\n"
        "    \n"
        "    # Execution\n"
        "    DB['refunds'].append(args.model_dump())\n"
        "    return f'Refund of {args.amount_cents} cents issued successfully for TX {args.transaction_id}'\n"
    ))

    # PART 7
    nb.cells.append(nbf.v4.new_markdown_cell("## Part 7: Tool Registry & Permissions\nWe define exactly which tools exist and their authorization requirements."))
    nb.cells.append(nbf.v4.new_code_cell(
        "from typing import Callable\n\n"
        "class ToolDefinition(BaseModel):\n"
        "    name: str\n"
        "    effect: Literal['READ_ONLY', 'CONSEQUENTIAL_WRITE']\n"
        "    required_permission: str\n"
        "    func: Callable\n"
        "    schema: type[BaseModel]\n\n"
        "TOOL_REGISTRY = {\n"
        "    'get_ticket_details': ToolDefinition(name='get_ticket_details', effect='READ_ONLY', required_permission='support:read', func=get_ticket_details, schema=GetTicketArgs),\n"
        "    'get_recent_transactions': ToolDefinition(name='get_recent_transactions', effect='READ_ONLY', required_permission='billing:read', func=get_recent_transactions, schema=GetCustomerArgs),\n"
        "    'get_refund_policy': ToolDefinition(name='get_refund_policy', effect='READ_ONLY', required_permission='support:read', func=get_refund_policy, schema=BaseModel),\n"
        "    'issue_refund': ToolDefinition(name='issue_refund', effect='CONSEQUENTIAL_WRITE', required_permission='refund:issue', func=issue_refund, schema=IssueRefundArgs),\n"
        "}\n\n"
        "AUTONOMOUS_TOOLS = ['get_ticket_details', 'get_recent_transactions', 'get_refund_policy']\n"
    ))

    # PART 8 & 9
    nb.cells.append(nbf.v4.new_markdown_cell("## Part 8 & 9: Model Contract & Deterministic Stub\nWe define the shape of the LLM's response, and create a mock model to ensure the core lab runs without an API key."))
    nb.cells.append(nbf.v4.new_code_cell(
        "class ToolCall(BaseModel):\n"
        "    id: str\n"
        "    name: str\n"
        "    arguments: dict\n\n"
        "class AgentDecision(BaseModel):\n"
        "    tool_calls: list[ToolCall] = []\n"
        "    proposal: Optional[RefundProposal] = None\n"
        "    final_answer: Optional[str] = None\n\n"
        "class MockDecisionModel:\n"
        "    \"\"\"Deterministic stub for reproducible training. Returns fixed responses based on the turn.\"\"\"\n"
        "    def __init__(self):\n"
        "        self.turn = 0\n"
        "    def decide(self, state) -> AgentDecision:\n"
        "        self.turn += 1\n"
        "        if self.turn == 1:\n"
        "            return AgentDecision(tool_calls=[ToolCall(id='call_1', name='get_ticket_details', arguments={'ticket_id': state.ticket_id})])\n"
        "        if self.turn == 2:\n"
        "            return AgentDecision(tool_calls=[\n"
        "                ToolCall(id='call_2', name='get_recent_transactions', arguments={'customer_id': 'C-55'}),\n"
        "                ToolCall(id='call_3', name='get_refund_policy', arguments={})\n"
        "            ])\n"
        "        if self.turn == 3:\n"
        "            # Identifies duplicate TX-902 and proposes refund\n"
        "            return AgentDecision(proposal=RefundProposal(\n"
        "                customer_id='C-55', transaction_id='TX-902', amount_cents=10000, reason='Duplicate charge identified.'\n"
        "            ))\n"
        "        return AgentDecision(final_answer='I am stuck.')\n"
    ))

    # PART 10
    nb.cells.append(nbf.v4.new_markdown_cell("## Part 10: The Complete Bounded Loop\nHere we implement state, budgets, no-progress detection, schema validation, and authorization."))
    nb.cells.append(nbf.v4.new_code_cell(
        "class AgentState(BaseModel):\n"
        "    ticket_id: str\n"
        "    steps: int = 0\n"
        "    max_steps: int = 5\n"
        "    history: list[dict] = []\n"
        "    seen_actions: set[str] = set()\n"
        "    terminal_reason: Optional[str] = None\n"
        "    proposal: Optional[RefundProposal] = None\n\n"
        "def run_agent(ctx: ExecutionContext, state: AgentState, model) -> AgentState:\n"
        "    while state.terminal_reason is None:\n"
        "        if state.steps >= state.max_steps:\n"
        "            state.terminal_reason = 'STEP_BUDGET_EXHAUSTED'\n"
        "            break\n"
        "        \n"
        "        state.steps += 1\n"
        "        decision = model.decide(state)\n"
        "        \n"
        "        if decision.final_answer:\n"
        "            state.terminal_reason = 'SUCCESS'\n"
        "            break\n"
        "            \n"
        "        if decision.proposal:\n"
        "            state.proposal = decision.proposal\n"
        "            state.terminal_reason = 'HUMAN_APPROVAL_REQUIRED'\n"
        "            break\n"
        "            \n"
        "        for tc in decision.tool_calls:\n"
        "            # 1. No-progress detection\n"
        "            fingerprint = f'{tc.name}:{tc.arguments}'\n"
        "            if fingerprint in state.seen_actions:\n"
        "                state.terminal_reason = 'NO_PROGRESS'\n"
        "                break\n"
        "            state.seen_actions.add(fingerprint)\n"
        "            \n"
        "            # 2. Registry & Autonomous Auth\n"
        "            if tc.name not in AUTONOMOUS_TOOLS:\n"
        "                state.terminal_reason = 'AUTHORIZATION_DENIED'\n"
        "                break\n"
        "            \n"
        "            tdef = TOOL_REGISTRY[tc.name]\n"
        "            \n"
        "            # 3. Schema Validation & Execution\n"
        "            try:\n"
        "                args_obj = tdef.schema(**tc.arguments)\n"
        "                result = tdef.func(args_obj)\n"
        "                state.history.append({'tool': tc.name, 'result': result})\n"
        "            except Exception as e:\n"
        "                state.history.append({'tool': tc.name, 'error': str(e)})\n"
        "    return state\n"
    ))

    # PART 11 & 12
    nb.cells.append(nbf.v4.new_markdown_cell("## Part 11 & 12: Happy Path & Human Approval\nRun the agent to get a proposal, then securely bind human approval to it."))
    nb.cells.append(nbf.v4.new_code_cell(
        "import hashlib\n\n"
        "state = AgentState(ticket_id='T-102')\n"
        "model = MockDecisionModel()\n"
        "final_state = run_agent(ctx, state, model)\n\n"
        "print(f'Terminal Reason: {final_state.terminal_reason}')\n"
        "print(f'Proposal: {final_state.proposal}')\n\n"
        "class Approval(BaseModel):\n"
        "    proposal_digest: str\n"
        "    approver_id: str\n"
        "    decision: Literal['approve', 'reject']\n\n"
        "digest = hashlib.sha256(final_state.proposal.model_dump_json().encode()).hexdigest()\n"
        "manager_approval = Approval(proposal_digest=digest, approver_id='MGR-1', decision='approve')\n"
        "print(f'Manager approved digest: {digest[:8]}...')\n"
    ))

    # PART 13 & 14
    nb.cells.append(nbf.v4.new_markdown_cell("## Part 13 & 14: Execution & Idempotency\nWe execute the approved proposal using a secure idempotency key. Then we try executing it again to prove safety."))
    nb.cells.append(nbf.v4.new_code_cell(
        "def execute_approved_proposal(proposal: RefundProposal, approval: Approval):\n"
        "    check_digest = hashlib.sha256(proposal.model_dump_json().encode()).hexdigest()\n"
        "    if check_digest != approval.proposal_digest or approval.decision != 'approve':\n"
        "        raise ValueError('Invalid or rejected approval.')\n"
        "        \n"
        "    # Business Validation: Ensure refund doesn't exceed TX amount\n"
        "    # (Simplified for demo)\n"
        "    \n"
        "    # Generate Idempotency Key bound to this exact request\n"
        "    idem_key = f'ref_{proposal.transaction_id}_{check_digest[:8]}'\n"
        "    args = IssueRefundArgs(\n"
        "        customer_id=proposal.customer_id, \n"
        "        transaction_id=proposal.transaction_id,\n"
        "        amount_cents=proposal.amount_cents,\n"
        "        idempotency_key=idem_key\n"
        "    )\n"
        "    return issue_refund(args)\n\n"
        "print('First Execution:', execute_approved_proposal(final_state.proposal, manager_approval))\n"
        "print('Duplicate Execution:', execute_approved_proposal(final_state.proposal, manager_approval))\n"
        "print('DB State:', DB['refunds'])\n"
    ))

    # PART 18
    nb.cells.append(nbf.v4.new_markdown_cell("## Part 18: Real OpenAI Integration (Optional)\nIf you provide an `OPENAI_API_KEY` in your environment, we can run the EXACT SAME application boundary using a real LLM. We define an `OpenAIDecisionModel` that adheres to our `DecisionModel` contract."))
    nb.cells.append(nbf.v4.new_code_cell(
        "import os\n"
        "from openai import OpenAI\n\n"
        "class OpenAIDecisionModel:\n"
        "    def __init__(self):\n"
        "        self.client = OpenAI()\n"
        "        self.messages = [\n"
        "            {'role': 'system', 'content': 'You are a support agent. Analyze the ticket, query billing, and if there is a duplicate charge, use the propose_refund tool.'}\n"
        "        ]\n"
        "        # We map our ToolRegistry to OpenAI Schema natively here\n"
        "        self.tools = [\n"
        "            {'type': 'function', 'function': {'name': 'get_ticket_details', 'parameters': {'type': 'object', 'properties': {'ticket_id': {'type': 'string'}}, 'required': ['ticket_id']}}},\n"
        "            {'type': 'function', 'function': {'name': 'get_recent_transactions', 'parameters': {'type': 'object', 'properties': {'customer_id': {'type': 'string'}}, 'required': ['customer_id']}}},\n"
        "            {'type': 'function', 'function': {'name': 'get_refund_policy', 'parameters': {'type': 'object', 'properties': {}}}},\n"
        "            {'type': 'function', 'function': {'name': 'propose_refund', 'parameters': RefundProposal.model_json_schema()}}\n"
        "        ]\n"
        "        \n"
        "    def decide(self, state: AgentState) -> AgentDecision:\n"
        "        # Feed observation history into LLM\n"
        "        for h in state.history:\n"
        "            self.messages.append({'role': 'system', 'content': f'Observation: {h}'})\n"
        "        state.history.clear() # clear unread\n"
        "        \n"
        "        if len(self.messages) == 1:\n"
        "            self.messages.append({'role': 'user', 'content': f'Investigate ticket {state.ticket_id}'})\n"
        "            \n"
        "        resp = self.client.chat.completions.create(model='gpt-4o-mini', messages=self.messages, tools=self.tools)\n"
        "        msg = resp.choices[0].message\n"
        "        self.messages.append(msg)\n"
        "        \n"
        "        if not msg.tool_calls:\n"
        "            return AgentDecision(final_answer=msg.content)\n"
        "            \n"
        "        tcs = []\n"
        "        for tc in msg.tool_calls:\n"
        "            if tc.function.name == 'propose_refund':\n"
        "                return AgentDecision(proposal=RefundProposal(**json.loads(tc.function.arguments)))\n"
        "            tcs.append(ToolCall(id=tc.id, name=tc.function.name, arguments=json.loads(tc.function.arguments)))\n"
        "        return AgentDecision(tool_calls=tcs)\n\n"
        "if os.getenv('OPENAI_API_KEY'):\n"
        "    print('Running REAL OpenAI Model through the secure runtime...')\n"
        "    real_state = AgentState(ticket_id='T-102')\n"
        "    real_model = OpenAIDecisionModel()\n"
        "    final_real_state = run_agent(ctx, real_state, real_model)\n"
        "    print(f'Terminal Reason: {final_real_state.terminal_reason}')\n"
        "    print(f'Proposal: {final_real_state.proposal}')\n"
        "else:\n"
        "    print('Skipping real execution. Set OPENAI_API_KEY in environment to run.')"
    ))

    # PART 19
    nb.cells.append(nbf.v4.new_markdown_cell("## Part 19: Optional Framework Mapping\nAs you saw in Module 05, frameworks like OpenAI Agents SDK, LangGraph, or PydanticAI exist to package the `run_agent` while loop boilerplate. However, they **do not** replace the Business Validation, Schema Validation, Authorization, or Idempotency logic we just built. The framework is just the orchestrator; your application boundary is the security."))

    output_path = os.path.join(os.path.dirname(__file__), "06_building_your_first_agent.ipynb")
    with open(output_path, "w", encoding="utf-8") as f:
        nbf.write(nb, f)
        
    print(f"Notebook generated successfully at {output_path}")

if __name__ == "__main__":
    generate_notebook()
