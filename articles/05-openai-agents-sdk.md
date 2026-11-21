# 05. The OpenAI Agents SDK

*Agent SDK Lab, article 5 of 8*

The OpenAI Agents SDK is declarative: describe the agent, then run it.

```python
agent = Agent(
    name="Kestrel triage",
    instructions=SYSTEM_PROMPT,
    tools=[search_backlog, get_story, search_docs],
    output_type=TriageDecision,
)
result = await Runner.run(agent, request, max_turns=8)
decision = result.final_output          # a TriageDecision
```

## Tools from functions

`@function_tool` turns a typed Python function into a tool. The SDK reads the type hints for the
schema (strict by default) and the docstring for the description, including per-argument text
under `Args:`. Write docstrings for the model, not just for colleagues.

## The answer is the output type

There's no `submit_decision` tool. With `output_type=TriageDecision`, the model's final message must
match the Pydantic model, and the SDK validates it. It's the same idea as structured outputs in
lab 1, applied to the end of an agent run.

## Limits and errors

`max_turns` caps the run; exceeding it raises `MaxTurnsExceeded`. The exception carries `run_data`
with the items and usage so far. The implementation uses that to still record what the agent did
before it was stopped.

## Running it offline

The SDK calls models through a `Model` interface. `FakeModel` implements `get_response()` on top of
the shared Brain: it reads the request and the `function_call_output` items, asks the Brain, and
returns either a `ResponseFunctionToolCall` or a final message with the decision as JSON. So the
real `Runner`, tool execution, schema validation and turn limit all run in CI with no network.

Tracing uploads run data to OpenAI by default; the offline path calls `set_tracing_disabled(True)`.

## Provider

Live runs use an OpenAI model. Set `OPENAI_AGENTS_MODEL` to choose one; otherwise the SDK's default
is used. Cost isn't reported in dollars, only tokens, so `RunRecord.cost_usd` stays empty rather
than guessing a price.

## When it fits

Teams on OpenAI models who want a small, readable agent definition, with handoffs between agents
and guardrails built in.
