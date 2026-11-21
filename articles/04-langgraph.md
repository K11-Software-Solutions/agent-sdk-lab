# 04. LangGraph: The Loop as a Graph

*Agent SDK Lab, article 4 of 8*

LangGraph makes the control flow explicit: nodes do work, edges decide what runs next, and a
typed state object flows between them. `frameworks/langgraph_agent.py` draws the same loop:

```text
START -> model --(tool calls)--> tools -> model
               --(decision or error)--> END
```

## State with reducers

```python
class State(TypedDict):
    messages: Annotated[list, operator.add]     # each node's update is appended
    tool_calls: Annotated[list, operator.add]
    usage: Annotated[list, operator.add]
    pending: list                               # replaced on each update
    decision: dict | None
    error: str
```

A node returns only what it changes; the reducer (`operator.add`) says how to merge it. That makes
nodes small and testable on their own.

## The model doesn't have to be LangChain's

The `model` node calls the same `llm.step()` as the hand-written loop. LangGraph is about
orchestration; it doesn't require LangChain chat models. Using the same interface is what makes
this comparison fair, and it means the offline fake works unchanged.

## Checkpointing

The graph is compiled with a checkpointer (`InMemorySaver`). After every node, state is saved under
a `thread_id`. A test runs one request and finds a checkpoint after each step in
`get_state_history()`. That is the basis for:

- inspecting exactly what the agent saw at each step;
- resuming after a failure;
- pausing before a risky tool for human approval, then continuing.

Use a persistent checkpointer (a database) in production; the in-memory one is for tests.

Checkpointing has a requirement the raw loop didn't have: **state must be serialisable**. The first
version of this lab stored SDK response objects in the message list, and the checkpointer refused
them. The fix — plain dicts — is in `ClaudeLLM.step()`.

## Limits

`recursion_limit` bounds the number of node executions. Each model-and-tools round is two nodes, so
the run uses `2 * MAX_STEPS`. When it's hit, LangGraph raises `GraphRecursionError`; the
implementation catches it and still reads the partial state back from the checkpointer.

## When LangGraph fits

Agents with real branching (review, retry, escalate), long-running or resumable work, and
human-in-the-loop steps.
