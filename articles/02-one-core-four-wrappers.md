# 02. One Core, Four Wrappers

*Agent SDK Lab, article 2 of 8*

The most useful design decision in this lab isn't about any framework. It's that the business
logic lives outside all of them, in `kestrel_agents/core.py`.

## What's in the core

- `search_backlog`, `get_story`, `search_docs`: plain Python functions.
- `call_tool(name, args) -> (text, is_error)`: one dispatcher that never raises.
- `TOOL_SPECS` and `json_schema(name)`: descriptions and strict schemas, written once.
- `SYSTEM_PROMPT` and `TriageDecision`: the instructions and the answer contract.
- `RunRecord`: what every implementation returns.

## Four wrappers around the same function

```python
# raw and LangGraph: a Messages API tool definition built from TOOL_SPECS
{"name": "get_story", "strict": True, "input_schema": json_schema("get_story"), ...}

# OpenAI Agents SDK: a decorated function; the SDK builds the schema from type hints
@function_tool
def get_story(story_id: str) -> str:
    return call_tool("get_story", {"story_id": story_id})[0]

# Claude Agent SDK: an in-process MCP tool with the same JSON schema
@tool("get_story", description, json_schema("get_story"))
async def handler(args):
    output, is_error = call_tool("get_story", args)
    return {"content": [{"type": "text", "text": output}], "is_error": is_error}
```

Each wrapper is a few lines. Switching frameworks later means rewriting the wrappers, not the
tools.

## The run record

Each framework reports results in its own shape: a list of messages, a graph state, a `RunResult`,
a stream ending in a `ResultMessage`. Each implementation converts its own shape into one
`RunRecord`: decision, tool calls, model calls, tokens, cost, error. The eval only reads
`RunRecord`, so it never needs to know which framework produced it.

That conversion is also where you learn what a framework gives you. The Claude Agent SDK reports
`total_cost_usd` itself; the OpenAI Agents SDK reports token usage but not dollars; the
hand-written loop computes cost from tokens and a price table.
