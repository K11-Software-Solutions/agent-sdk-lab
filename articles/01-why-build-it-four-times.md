# 01. Why Build the Same Agent Four Times

*Agent SDK Lab, article 1 of 8*

Most framework comparisons build a different demo in each framework, so you can't tell whether a
difference comes from the framework or from the demo. This lab holds everything else still:

- **the same task**: triage a feature request against the backlog;
- **the same tools**: `search_backlog`, `get_story`, `search_docs`, as one set of Python functions;
- **the same prompt and answer format**: `SYSTEM_PROMPT` and `TriageDecision`;
- **the same eval**: seven cases, checking outcome, trajectory, safety and completion.

Only the framework changes.

## The four

| | What it is |
|---|---|
| Hand-written loop | Lab 1's loop: call the model, run tools, repeat. The baseline. |
| LangGraph | A library for building agents as graphs of nodes and edges, with checkpointed state. |
| OpenAI Agents SDK | A runner for agents declared as instructions, tools and an output type. |
| Claude Agent SDK | Claude Code's agent harness as a library: loop, tools, permissions, hooks, MCP. |

## What "the same" lets you see

When the three offline implementations run on the same deterministic fake, they produce **the
same tool calls in the same order** on every case, and a test asserts it. So whatever differs
between them (lines of code, where state lives, how the answer comes back, what stops a runaway
loop) is a property of the framework.

## What this lab is not

It is not a benchmark of model quality: that depends on the model, not the framework. Run the live
evals to compare models, and run them several times, because single runs vary.

## Try it

```bash
python -m kestrel_agents raw "Export the sprint report as a PDF file"
```

```bash
python -m kestrel_agents openai_agents "Export the sprint report as a PDF file"
```
