# 06. The Claude Agent SDK

*Agent SDK Lab, article 6 of 8*

The Claude Agent SDK packages Claude Code's agent harness as a library: the loop, context
management, built-in tools (files, shell, web search), permissions, hooks, subagents and MCP. You
pass options and a prompt and iterate over the messages it streams back.

```python
async for message in query(prompt=request, options=options):
    ...   # AssistantMessage (with ToolUseBlocks), then a ResultMessage
```

## Your tools as an in-process MCP server

```python
@tool("get_story", description, json_schema("get_story"))
async def handler(args):
    output, is_error = call_tool("get_story", args)
    return {"content": [{"type": "text", "text": output}], "is_error": is_error}

server = create_sdk_mcp_server(name="kestrel", version="1.0.0", tools=[...])
```

The tools run inside your Python process; Claude sees them as `mcp__kestrel__get_story`. Lab 4
moves the same tools into a standalone MCP server that any client can use.

## Options for a narrow agent

The harness can do a lot, so the options here mostly take things away:

| Option | Why |
|---|---|
| `tools=[]` | built-in file, shell and web tools off; this agent needs only ours |
| `allowed_tools=[mcp__kestrel__...]` | our tools run without a permission prompt |
| `setting_sources=[]` | ignore user and project settings (including their hooks), so runs are reproducible |
| `output_format` (JSON schema) | the decision comes back as `structured_output` |
| `max_turns`, `max_budget_usd` | hard limits on length and spend |
| `model`, `effort` | `claude-opus-5-5`, effort set explicitly |

Start narrow and add capability deliberately. An agent that can run shell commands is a different
risk from one that can read a backlog.

## What comes back

The final `ResultMessage` reports `num_turns`, `total_cost_usd`, `usage`, `structured_output`, and
`is_error` with a `subtype`. The implementation maps those onto `RunRecord`. If there's an error or
no structured output, that is recorded as an error, never as a decision.

## Testing without running Claude Code

The SDK runs the Claude Code CLI as a subprocess, so there's no offline model to swap in. The tests
check what can be checked without it: the options, each tool handler (called directly), and the
message handling. For that last one, `query` is replaced with a scripted stream of an
`AssistantMessage` and a `ResultMessage`. Live runs are opt-in.

## When it fits

Agents that need more than your tools: reading and editing files, running commands, searching the
web, delegating to subagents. That is the Claude Code feature set, with permissions and hooks
already built.
