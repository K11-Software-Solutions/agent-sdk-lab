"""Implementation 2: LangGraph.

The same loop, drawn as a graph: a `model` node, a `tools` node, and an edge that decides where
to go next. LangGraph doesn't require LangChain models; here the model node calls the same
`step()` interface as the hand-written loop, so the two are directly comparable.

What the graph gives you over the raw loop:
- the control flow is data you can inspect and draw (`graph.get_graph().draw_mermaid()`);
- a checkpointer saves state after every node, keyed by thread_id, so a run can be inspected,
  resumed or paused for human approval;
- `recursion_limit` bounds the number of steps.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph

from kestrel_agents.core import SYSTEM_PROMPT, RunRecord, TriageDecision, call_tool
from kestrel_agents.llm import TOOLS, LLMError, cost, get_llm

MAX_STEPS = 8


class State(TypedDict):
    messages: Annotated[list, operator.add]           # appended to, never replaced
    tool_calls: Annotated[list, operator.add]
    usage: Annotated[list, operator.add]              # (model, input tokens, output tokens) per call
    pending: list                                     # tool calls from the last model turn
    decision: dict | None
    error: str


def build(llm) -> Any:
    def model_node(state: State) -> dict:
        try:
            step = llm.step(SYSTEM_PROMPT, state["messages"], TOOLS)
        except LLMError as exc:
            return {"error": str(exc), "pending": []}
        update = {"messages": [{"role": "assistant", "content": step.assistant_content}],
                  "usage": [(step.model, step.input_tokens, step.output_tokens)], "pending": step.tool_calls}
        for _, name, args in step.tool_calls:
            if name == "submit_decision":
                update["decision"] = args
        if not step.tool_calls:
            update["messages"].append({"role": "user", "content": "Finish by calling submit_decision."})
        return update

    def tools_node(state: State) -> dict:
        results, calls = [], []
        for call_id, name, args in state["pending"]:
            output, is_error = call_tool(name, args)
            calls.append((name, args))
            results.append({"type": "tool_result", "tool_use_id": call_id, "content": output, "is_error": is_error})
        return {"messages": [{"role": "user", "content": results}], "tool_calls": calls, "pending": []}

    def route(state: State) -> str:
        if state.get("decision") or state.get("error"):
            return END
        return "tools" if state["pending"] else "model"

    g = StateGraph(State)
    g.add_node("model", model_node)
    g.add_node("tools", tools_node)
    g.add_edge(START, "model")
    g.add_conditional_edges("model", route, ["tools", "model", END])
    g.add_edge("tools", "model")
    return g.compile(checkpointer=InMemorySaver())


def run(request: str, provider: str = "fake", llm=None, max_steps: int = MAX_STEPS, thread_id: str = "triage-1", **kw) -> RunRecord:
    graph = build(llm or get_llm(provider, **kw))
    rec = RunRecord("langgraph", request)
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 2 * max_steps}   # model + tools node per step
    try:
        graph.invoke({"messages": [{"role": "user", "content": request}], "tool_calls": [], "usage": [],
                      "pending": [], "decision": None, "error": ""}, config)
    except GraphRecursionError:
        rec.error = f"no decision after {max_steps} model calls (recursion limit)"
    state = graph.get_state(config).values             # read back from the checkpointer, even after an error
    rec.tool_calls = list(state.get("tool_calls", []))
    usage = state.get("usage", [])
    rec.model_calls = len(usage)
    rec.input_tokens = sum(u[1] for u in usage)
    rec.output_tokens = sum(u[2] for u in usage)
    rec.cost_usd = cost(usage[-1][0] if usage else "", rec.input_tokens, rec.output_tokens)
    rec.error = rec.error or state.get("error", "")
    if state.get("decision"):
        rec.decision = TriageDecision(**state["decision"])
    return rec
