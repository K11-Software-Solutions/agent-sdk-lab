"""A one-turn model interface for the two implementations that own their loop (raw and LangGraph).

    step(system, messages, tools) -> Step

Messages and tools use the Claude Messages API format. ClaudeLLM calls the API with explicit
effort and server-side refusal fallbacks (beta); FakeLLM asks the shared Brain.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from kestrel_agents.brain import Brain
from kestrel_agents.core import TOOL_SPECS, json_schema

DEFAULT_MODEL = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"
PRICES_PER_MTOK = {"claude-opus-5-5": (4.00, 20.00), "claude-sonnet-5-5": (2.00, 10.00), "claude-haiku-5-5": (0.10, 0.50)}

SUBMIT = {"name": "submit_decision", "description": "Record the triage decision. Call exactly once, at the end.", "strict": True,
          "input_schema": {"type": "object", "properties": {
              "decision": {"type": "string", "enum": ["duplicate", "related", "new"]},
              "story_id": {"type": ["string", "null"], "description": "Existing story for duplicate or related, else null"},
              "reason": {"type": "string"}},
              "required": ["decision", "story_id", "reason"], "additionalProperties": False}}
TOOLS = [{"name": n, "description": d, "strict": True, "input_schema": json_schema(n)} for n, (d, _) in TOOL_SPECS.items()] + [SUBMIT]


class LLMError(Exception):
    pass


def cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pin, pout = PRICES_PER_MTOK.get(model, (0.0, 0.0))
    return (input_tokens * pin + output_tokens * pout) / 1_000_000


@dataclass
class Step:
    tool_calls: list[tuple[str, str, dict]]          # (id, name, input)
    assistant_content: Any
    model: str = "fake"
    input_tokens: int = 0
    output_tokens: int = 0
    text: str = ""
    raw: Any = field(default=None, repr=False)


class ClaudeLLM:
    name = "claude"

    def __init__(self, model: str = DEFAULT_MODEL, effort: str = "medium", client: Any = None):
        import anthropic
        self.client = client or anthropic.Anthropic()
        self.model, self.effort = model, effort

    def step(self, system: str, messages: list, tools: list[dict]) -> Step:
        resp = self.client.beta.messages.create(
            model=self.model, max_tokens=16000, system=system, messages=messages, tools=tools,
            output_config={"effort": self.effort}, betas=[FALLBACK_BETA], fallbacks="default")
        if resp.stop_reason in ("refusal", "max_tokens"):
            raise LLMError(f"stop_reason {resp.stop_reason}")
        calls = [(b.id, b.name, dict(b.input)) for b in resp.content if b.type == "tool_use"]
        text = "".join(b.text for b in resp.content if b.type == "text")
        # Plain dicts, not SDK objects: they go back to the API unchanged and LangGraph can checkpoint them.
        content = [blk.model_dump(mode="json", exclude_none=True) for blk in resp.content]
        return Step(calls, content, resp.model, resp.usage.input_tokens, resp.usage.output_tokens, text)


class FakeLLM:
    name = "fake"

    def __init__(self, behaviour: str | None = None):
        self.brain = Brain(behaviour)
        self.n = 0

    def step(self, system: str, messages: list, tools: list[dict]) -> Step:
        request = messages[0]["content"]
        names = {b["id"]: b["name"] for m in messages if m["role"] == "assistant"
                 for b in m["content"] if isinstance(b, dict) and b.get("type") == "tool_use"}
        observations = [(names[b["tool_use_id"]], b["content"]) for m in messages
                        if m["role"] == "user" and isinstance(m["content"], list) for b in m["content"]]
        action = self.brain.next(request, observations)
        self.n += 1
        name, args = (action.tool, action.args) if action.tool else ("submit_decision", action.decision)
        call_id = f"toolu_fake_{self.n}"
        content = [{"type": "tool_use", "id": call_id, "name": name, "input": args}]
        return Step([(call_id, name, args)], content, "fake", 200 + 50 * len(observations), 40)


def get_llm(provider: str = "fake", **kwargs):
    if provider == "claude":
        return ClaudeLLM(**kwargs)
    if provider == "fake":
        return FakeLLM(kwargs.get("behaviour"))
    raise ValueError(f"unknown provider {provider!r}")


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)
