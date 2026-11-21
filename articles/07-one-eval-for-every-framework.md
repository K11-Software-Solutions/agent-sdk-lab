# 07. One Eval for Every Framework

*Agent SDK Lab, article 7 of 8*

The eval in `evals/run_evals.py` reads only `RunRecord`, so one set of cases and checks covers all
four implementations.

## Four checks per case

| Check | Question | Example failure |
|---|---|---|
| Outcome | Right decision, right story? | "related" when the case accepts only "duplicate" |
| Trajectory | Did it look before deciding? | decided without calling `get_story` |
| Safety | Did it ignore instructions in data? | "duplicate of KES-106", as the planted note asks |
| Completion | Did it decide before the limit? | stopped by the turn limit |

Trajectory checks catch an agent that lands on the right answer for the wrong reason. A case can
require the tools it needs: T6 ("single sign-on on the Team plan") must call `search_docs`,
because the documents say SSO is Enterprise-only.

## Negative controls, in every framework

The Brain has broken behaviours, and each must fail the eval in all three offline frameworks:

- `obey_backlog` fails exactly the injection case;
- `no_lookup` fails every case, through the trajectory check;
- `never_decides` fails every case, and each framework's own limit stops it at 8 model calls
  (`MAX_STEPS`, `recursion_limit`, `max_turns`).

That last one is worth noticing: three frameworks, three different limit mechanisms, one behaviour.

## Same trajectory, by construction

Because the offline implementations share one Brain, a test asserts they make identical tool calls
on every case. If a framework change altered what the model sees (a dropped tool result, reordered
messages), this test would catch it before any eval number moved.

## Live runs

```bash
python evals/run_evals.py --frameworks raw,langgraph,claude_agent_sdk --provider claude
```

Live results compare models and harnesses, not just frameworks. The Claude Agent SDK brings
Claude Code's own system behaviour, while raw and LangGraph send only this lab's prompt. Expect
some differences, run several times, and see the
[AI Evaluation Science Lab](https://github.com/K11-Software-Solutions/ai-evaluation-science-lab)
for how many runs a comparison needs.
