"""Implementation 1: the agent loop written by hand (lab 1's loop, with three tools).

You own every decision: the step limit, how tool errors go back, how the loop ends, what is
recorded. Nothing is hidden, and nothing is done for you.
"""
from __future__ import annotations

from kestrel_agents.core import SYSTEM_PROMPT, RunRecord, TriageDecision, call_tool
from kestrel_agents.llm import TOOLS, LLMError, cost, get_llm

MAX_STEPS = 8


def run(request: str, provider: str = "fake", llm=None, max_steps: int = MAX_STEPS, **kw) -> RunRecord:
    llm = llm or get_llm(provider, **kw)
    rec = RunRecord("raw", request)
    messages: list = [{"role": "user", "content": request}]
    model = ""
    for _ in range(max_steps):
        try:
            step = llm.step(SYSTEM_PROMPT, messages, TOOLS)
        except LLMError as exc:
            rec.error = str(exc)
            break
        model = step.model
        rec.model_calls += 1
        rec.input_tokens += step.input_tokens
        rec.output_tokens += step.output_tokens
        messages.append({"role": "assistant", "content": step.assistant_content})
        if not step.tool_calls:
            messages.append({"role": "user", "content": "Finish by calling submit_decision."})
            continue
        results = []
        for call_id, name, args in step.tool_calls:
            if name == "submit_decision":
                rec.decision = TriageDecision(**args)
                break
            rec.tool_calls.append((name, args))
            output, is_error = call_tool(name, args)
            results.append({"type": "tool_result", "tool_use_id": call_id, "content": output, "is_error": is_error})
        if rec.decision:
            break
        messages.append({"role": "user", "content": results})
    else:
        rec.error = f"no decision after {max_steps} model calls"
    rec.cost_usd = cost(model, rec.input_tokens, rec.output_tokens)
    return rec
