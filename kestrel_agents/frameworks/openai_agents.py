"""Implementation 3: the OpenAI Agents SDK.

The SDK runs the loop. You declare an Agent (instructions, tools, output type) and call
Runner.run. Tools are plain Python functions; the SDK builds strict JSON schemas from their type
hints and docstrings. The final answer is the agent's `output_type`, a Pydantic model, rather
than a "submit" tool.

Provider: an OpenAI model by default (OPENAI_API_KEY; set OPENAI_AGENTS_MODEL to choose one,
otherwise the SDK's default is used). Offline, `FakeModel` implements the SDK's `Model`
interface on top of the shared Brain, so this file runs in CI with no network.
"""
from __future__ import annotations

import asyncio
import json
import os

from agents import Agent, MaxTurnsExceeded, Runner, function_tool, set_tracing_disabled
from agents.items import ModelResponse
from agents.models.interface import Model
from agents.usage import Usage
from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage, ResponseOutputText

from kestrel_agents.brain import Brain
from kestrel_agents.core import SYSTEM_PROMPT, RunRecord, TriageDecision, call_tool

MAX_TURNS = 8


@function_tool
def search_backlog(query: str) -> str:
    """Search the backlog for stories sharing terms with the query. Returns id, title, status and matching term count.

    Args:
        query: Key terms from the request.
    """
    return call_tool("search_backlog", {"query": query})[0]


@function_tool
def get_story(story_id: str) -> str:
    """Read one backlog story in full by its id, for example KES-104.

    Args:
        story_id: The story id.
    """
    return call_tool("get_story", {"story_id": story_id})[0]


@function_tool
def search_docs(query: str) -> str:
    """Search Kestrel's handbook, ADRs, runbooks, product and security pages. Returns the two best sections.

    Args:
        query: What to look up.
    """
    return call_tool("search_docs", {"query": query})[0]


def build_agent(model=None) -> Agent:
    return Agent(name="Kestrel triage", instructions=SYSTEM_PROMPT, tools=[search_backlog, get_story, search_docs],
                 output_type=TriageDecision, model=model or os.environ.get("OPENAI_AGENTS_MODEL") or None)


class FakeModel(Model):
    """The SDK's Model interface, answered by the shared Brain instead of an API."""

    def __init__(self, behaviour: str | None = None):
        self.brain, self.n = Brain(behaviour), 0

    async def get_response(self, system_instructions, input, model_settings, tools, output_schema, handoffs,
                           tracing, *, previous_response_id=None, conversation_id=None, prompt=None):
        items = [input] if isinstance(input, str) else input
        request = next(i["content"] for i in items if isinstance(i, dict) and i.get("role") == "user")
        names = {i["call_id"]: i["name"] for i in items if isinstance(i, dict) and i.get("type") == "function_call"}
        observations = [(names[i["call_id"]], i["output"]) for i in items
                        if isinstance(i, dict) and i.get("type") == "function_call_output"]
        action = self.brain.next(request, observations)
        self.n += 1
        if action.tool:
            out = ResponseFunctionToolCall(type="function_call", id=f"fc_{self.n}", call_id=f"call_{self.n}",
                                           name=action.tool, arguments=json.dumps(action.args), status="completed")
        else:
            out = ResponseOutputMessage(type="message", id=f"msg_{self.n}", role="assistant", status="completed",
                                        content=[ResponseOutputText(type="output_text", text=json.dumps(action.decision), annotations=[])])
        usage = Usage(requests=1, input_tokens=200 + 50 * len(observations), output_tokens=40, total_tokens=240 + 50 * len(observations))
        return ModelResponse(output=[out], usage=usage, response_id=None)

    def stream_response(self, *args, **kwargs):
        raise NotImplementedError("the fake does not stream")


def run(request: str, provider: str = "fake", max_turns: int = MAX_TURNS, behaviour: str | None = None, **_) -> RunRecord:
    rec = RunRecord("openai_agents", request)
    if provider == "fake":
        set_tracing_disabled(True)                     # tracing uploads to OpenAI; off for offline runs
        agent = build_agent(FakeModel(behaviour))
    else:
        agent = build_agent()
    try:
        result = asyncio.run(Runner.run(agent, request, max_turns=max_turns))
        rec.decision = result.final_output
        usage = result.context_wrapper.usage
        items = result.new_items
    except MaxTurnsExceeded as exc:
        rec.error = f"no decision after {max_turns} turns (MaxTurnsExceeded)"
        data = exc.run_data
        usage = data.context_wrapper.usage if data else Usage()
        items = data.new_items if data else []
    for item in items:
        raw = getattr(item, "raw_item", None)
        if getattr(item, "type", "") == "tool_call_item" and getattr(raw, "name", None):
            rec.tool_calls.append((raw.name, json.loads(raw.arguments)))
    rec.model_calls, rec.input_tokens, rec.output_tokens = usage.requests, usage.input_tokens, usage.output_tokens
    return rec                                          # cost_usd stays None: OpenAI prices are not in this lab
