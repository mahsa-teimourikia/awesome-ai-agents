import json

class MockToolCallFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments

class MockToolCall:
    def __init__(self, id, name, arguments):
        self.id = id
        self.type = "function"
        self.function = MockToolCallFunction(name, arguments)

class MockMessage:
    def __init__(self, content=None, parsed=None, tool_calls=None):
        self.content = content
        self.parsed = parsed
        self.tool_calls = tool_calls
        self.role = "assistant"

class MockChoice:
    def __init__(self, message):
        self.message = message
        self.finish_reason = "stop" if not message.tool_calls else "tool_calls"

class MockCompletion:
    def __init__(self, message):
        self.choices = [MockChoice(message)]

class MockCompletions:
    def create(self, model, messages, tools=None, **kwargs):
        last_msg = messages[-1]["content"] if messages and "content" in messages[-1] else ""
        last_msg_str = str(last_msg).lower()
        
        # 1. Check for specific tool calling scenarios
        if tools:
            tool_names = [t["function"]["name"] for t in tools]
            
            if "check_server_health" in tool_names and ("down" in last_msg_str or "failing" in last_msg_str):
                return MockCompletion(MockMessage(
                    tool_calls=[MockToolCall("call_123", "check_server_health", '{"region": "us-east"}')]
                ))
            
            if "check_user" in tool_names and "locked" in last_msg_str:
                return MockCompletion(MockMessage(
                    tool_calls=[MockToolCall("call_123", "check_user", '{"user_id": "cust_123"}')]
                ))
                
            if "prepare_refund" in tool_names and "refund" in last_msg_str:
                return MockCompletion(MockMessage(
                    tool_calls=[MockToolCall("call_123", "prepare_refund", '{"amount": 50.0}')]
                ))

        # 2. Default Text Responses
        if "plan" in last_msg_str or "decompose" in last_msg_str:
            return MockCompletion(MockMessage("1. Check logs.\\n2. Restart server.\\n3. Notify user."))
            
        if "latency" in last_msg_str:
            return MockCompletion(MockMessage("I have investigated the latency. The database is heavily loaded. I recommend scaling up the read replicas."))
            
        return MockCompletion(MockMessage("I am a Mock Agent. I have received your request and simulated a successful response. Please set an OPENAI_API_KEY to use the real models!"))

    def parse(self, model, messages, response_format, **kwargs):
        # Raise an exception so that the notebook's try/except fallback logic executes
        raise NotImplementedError("MockOpenAI does not support dynamic Pydantic generation. Triggering fallback.")


class MockChat:
    def __init__(self):
        self.completions = MockCompletions()

class MockBetaChat:
    def __init__(self):
        self.completions = MockCompletions()

class MockBeta:
    def __init__(self):
        self.chat = MockBetaChat()

class MockOpenAI:
    def __init__(self, **kwargs):
        self.chat = MockChat()
        self.beta = MockBeta()
        print("🔧 Initialized MockOpenAI Client (Network requests disabled)")
