import os
path = "curriculum/advanced/27-agent-observability/agent_observability.ipynb"
with open(path) as f:
    text = f.read()

# Since it's JSON, the literal string has \"
bad_str = "print(f\\\"Recorded LLM Event: {event[\\\"model\\\"]}, Cost: ${event[\\\"cost\\\"]}, Total Tokens: {event[\\\"prompt_tokens\\\"] + event[\\\"completion_tokens\\\"]}\\\")"
good_str = "print(f\\\"Recorded LLM Event: {event['model']}, Cost: ${event['cost']}, Total Tokens: {event['prompt_tokens'] + event['completion_tokens']}\\\")"

new_text = text.replace(bad_str, good_str)

if new_text != text:
    with open(path, "w") as f:
        f.write(new_text)
    print("Patched f-string quotes.")
else:
    print("Failed to patch.")
