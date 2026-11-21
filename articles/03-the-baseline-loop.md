# 03. The Baseline: A Loop You Wrote

*Agent SDK Lab, article 3 of 8*

`frameworks/raw.py` is 38 lines of code. It is lab 1's loop with a third tool, and it is the
yardstick for the other three.

```text
for up to MAX_STEPS model calls:
    step = llm.step(system, messages, tools)
    if it called submit_decision: done
    run each tool, send all results back in one user message
```

## What you decide yourself

- **When it ends**: when the model calls `submit_decision`, a tool whose input schema *is* the
  answer format.
- **How long it may run**: `MAX_STEPS = 8`.
- **What a tool failure looks like to the model**: an `is_error` tool result it can recover from.
- **What a refusal or a cut-off reply becomes**: an error on the record, never a decision.
- **What gets recorded**: every tool call, every model call's tokens, the cost.

## What you don't get

Persistence (resume after a crash), streaming, parallel tool execution, human approval steps,
tracing, sub-agents. Each is some work to add, and every team that adds them adds them slightly
differently. That's the case for a framework.

## The Claude call

The model side is `ClaudeLLM.step()`: `claude-opus-5-5`, explicit `effort`, server-side refusal
fallbacks, and a check of `stop_reason`. One detail matters as soon as anything else stores the
conversation: the response's content blocks are converted to plain dicts before they're appended.
They go back to the API unchanged, and they can be serialised. Article 04 shows why that matters.

## When the baseline is the right answer

A short, well-bounded tool loop where you need full control and few dependencies. Many
production agents are exactly this, plus logging.
