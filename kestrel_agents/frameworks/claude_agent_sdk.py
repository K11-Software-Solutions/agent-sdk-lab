"""Implementation 4: the Claude Agent SDK.

The Claude Agent SDK is Claude Code's agent harness as a library: the loop, context management,
built-in tools (files, shell, web), permissions, hooks, subagents and MCP. You give it options
and a prompt; it streams messages back.

Our tools run in-process as an SDK MCP server. Claude sees them as `mcp__kestrel__<name>`.
The final answer uses `output_format` (a JSON schema), returned as `structured_output`.

Settings chosen for a narrow, predictable agent:
- tools=[]                built-in tools off: this agent only needs ours
- allowed_tools           our three tools run without permission prompts
- setting_sources=[]      ignore ~/.claude and project settings, so runs are reproducible
- max_turns, max_budget_usd   hard limits on length and spend

This implementation needs the Claude Code runtime (bundled with the package) and credentials
(ANTHROPIC_API_KEY or a Claude login). It does not run in CI; its tool handlers and options do.
"""
from __future__ import annotations

import asyncio

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, ResultMessage, ToolUseBlock,
                              create_sdk_mcp_server, query, tool)

from kestrel_agents.core import SYSTEM_PROMPT, TOOL_SPECS, RunRecord, TriageDecision, call_tool, json_schema

SERVER = "kestrel"
PREFIX = f"mcp__{SERVER}__"
MAX_TURNS = 8


def _make_tool(name: str):
    description, _ = TOOL_SPECS[name]

    @tool(name, description, json_schema(name))
    async def handler(args: dict) -> dict:
        output, is_error = call_tool(name, args)
        return {"content": [{"type": "text", "text": output}], "is_error": is_error}
    return handler


SDK_TOOLS = [_make_tool(n) for n in TOOL_SPECS]


def build_options(model: str = "claude-opus-5-5", effort: str = "medium", max_turns: int = MAX_TURNS,
                  max_budget_usd: float = 0.50) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={SERVER: create_sdk_mcp_server(name=SERVER, version="1.0.0", tools=SDK_TOOLS)},
        tools=[],
        allowed_tools=[PREFIX + n for n in TOOL_SPECS],
        setting_sources=[],
        output_format={"type": "json_schema", "schema": TriageDecision.model_json_schema()},
        model=model,
        effort=effort,
        max_turns=max_turns,
        max_budget_usd=max_budget_usd,
    )


async def _run(request: str, options: ClaudeAgentOptions, rec: RunRecord) -> None:
    async for message in query(prompt=request, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    rec.tool_calls.append((block.name.removeprefix(PREFIX), dict(block.input)))
        elif isinstance(message, ResultMessage):
            rec.model_calls = message.num_turns
            rec.cost_usd = message.total_cost_usd
            usage = message.usage or {}
            rec.input_tokens = usage.get("input_tokens", 0)
            rec.output_tokens = usage.get("output_tokens", 0)
            if message.is_error or message.structured_output is None:
                rec.error = f"{message.subtype}: {message.errors or message.terminal_reason or 'no structured output'}"
            else:
                rec.decision = TriageDecision.model_validate(message.structured_output)


def run(request: str, provider: str = "claude", **kw) -> RunRecord:
    if provider != "claude":
        raise ValueError("the Claude Agent SDK runs Claude Code; there is no offline mode (see the tests for what is checked offline)")
    rec = RunRecord("claude_agent_sdk", request)
    asyncio.run(_run(request, build_options(**{k: v for k, v in kw.items() if k in ("model", "effort", "max_turns", "max_budget_usd")}), rec))
    return rec
