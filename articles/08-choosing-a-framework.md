# 08. Choosing a Framework, and What Comes Next

*Agent SDK Lab, article 8 of 8*

| Implementation | Code lines | Loop run by | Final answer via | State and resume | Runs offline in CI |
|---|---|---|---|---|---|
| raw | 38 | you write it | submit_decision tool | you write it | yes (step() fake) |
| langgraph | 68 | graph edges | submit_decision tool | checkpointer (thread_id) | yes (same step() fake) |
| openai_agents | 69 | Runner | output_type (Pydantic) | sessions | yes (custom Model) |
| claude_agent_sdk | 52 | Claude Code harness | output_format (JSON schema) | sessions, resume, fork | no (CLI subprocess) |

Code size barely separates them. What separates them is what each takes off your hands, and what
it asks of you in return.

## A rule of thumb

- **Hand-written loop**: a short, bounded tool loop where you want full control and few
  dependencies.
- **LangGraph**: explicit branching, resumable long-running work, human approval steps.
- **OpenAI Agents SDK**: OpenAI models, compact declarative agents, handoffs and guardrails.
- **Claude Agent SDK**: agents that need Claude Code's abilities (files, shell, web, subagents)
  with its permissions and hooks.

## What every choice still leaves to you

Whichever you pick, these decisions stay yours, and this lab makes each one explicit:

- a limit on turns and spend;
- tool errors returned to the model, not raised;
- a validated final answer, and errors that are never passed on as answers;
- instructions inside data ignored, and tested;
- a run record you can evaluate.

## Keep the core outside the framework

Tools, prompts and the answer contract live in `core.py`. Each framework wraps them in a few
lines. When you change frameworks, or run two side by side, the expensive parts don't move.

## Next: lab 4, MCP servers

In this lab the Claude Agent SDK already reached our tools through MCP, in-process. Lab 4 moves
`search_backlog`, `get_story` and `search_docs` into a standalone MCP server. Then any MCP client
can use them: Claude Code, an IDE, or an agent built with any of these four. Lab 4 also adds auth
and tests for the server.
