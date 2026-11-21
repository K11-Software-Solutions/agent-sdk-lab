# Agent SDK Lab

**Lab 3 of [Becoming an AI Engineer](https://github.com/K11-Software-Solutions/becoming-an-ai-engineer).**
One agent, built four ways, measured with one eval:

1. a **hand-written loop** (the baseline from lab 1);
2. **LangGraph**;
3. the **OpenAI Agents SDK**;
4. the **Claude Agent SDK**.

The agent is the Kestrel PDLC Assistant's triage agent. It decides whether a feature request
duplicates, relates to or is new against the backlog, using three tools: `search_backlog`,
`get_story`, and `search_docs` over lab 2's documents. The tools, system prompt and answer format
are shared, so the differences you see come from the frameworks.

## The AI Engineering series

| # | Lab | Status |
|---|---|---|
| 1 | [AI Engineering Foundations](https://github.com/K11-Software-Solutions/becoming-an-ai-engineer) | ✅ |
| 2 | [RAG Engineering Lab](https://github.com/K11-Software-Solutions/rag-engineering-lab) | ✅ |
| 3 | **Agent SDK Lab** (this repo) | ✅ |
| 4 | MCP Server Engineering Lab | planned |
| 5 | AI Coding Assistant Extensions Lab | planned |
| 6 | PDLC Agents Lab | planned |
| 7 | Shipping Agents Lab | planned |
| 8 | Agents on AWS Lab | planned |
| 9 | Operating Agents Lab | planned |

## The comparison

`python compare.py` prints:

| Implementation | Code lines | Loop run by | Final answer via | State and resume | Runs offline in CI |
|---|---|---|---|---|---|
| raw | 38 | you write it | submit_decision tool | you write it | yes (step() fake) |
| langgraph | 68 | graph edges | submit_decision tool | checkpointer (thread_id) | yes (same step() fake) |
| openai_agents | 69 | Runner | output_type (Pydantic) | sessions | yes (custom Model) |
| claude_agent_sdk | 52 | Claude Code harness | output_format (JSON schema) | sessions, resume, fork | no (CLI subprocess) |

Code lines count only each framework's own module. The OpenAI file's count includes its
roughly 20-line offline `FakeModel`. Fewer lines is not the point: see article 08 for what each
one gives you and what it costs you.

## Offline by design

A single deterministic **Brain** (`kestrel_agents/brain.py`) stands in for the model. Each
framework reaches it through its own model interface:

- **raw and LangGraph** use a `step()` fake that speaks the Claude Messages format;
- **OpenAI Agents** uses a `FakeModel` implementing the SDK's `Model` interface;
- **Claude Agent SDK** runs the Claude Code CLI as a subprocess, so it has no offline mode. Its
  options, tool handlers and message handling are unit-tested with a scripted message stream.

Because the offline three share one brain, the tests can assert they produce **the same
trajectory** (the same tool calls in the same order) on every case.

## Run it

```bash
python -m venv .venv
```

```bash
.venv/bin/pip install -r requirements-dev.txt      # Windows: .venv\Scripts\pip
```

```bash
python -m kestrel_agents langgraph "Add single sign-on to the Team plan"
```

```bash
python evals/run_evals.py
```

```bash
pytest
```

Python 3.12 or later is required. The OpenAI Agents SDK fails to import on Python 3.11.0
because of a typing bug in that release.

Live runs cost money and print usage:

```bash
python evals/run_evals.py --frameworks raw,langgraph --provider claude      # ANTHROPIC_API_KEY
```

```bash
python evals/run_evals.py --frameworks claude_agent_sdk --provider claude   # API key or Claude login
```

```bash
python evals/run_evals.py --frameworks openai_agents --provider openai      # OPENAI_API_KEY; OPENAI_AGENTS_MODEL optional
```

The Claude paths use `claude-opus-5-5` with `effort` set explicitly. The raw and LangGraph paths
call the Messages API with **server-side refusal fallbacks** enabled. The Claude Agent SDK run is
capped with `max_turns` and `max_budget_usd`, loads no user or project settings, and has
built-in tools switched off.

## The eval

Seven cases, four checks each: **outcome** (right decision and story), **trajectory** (it looked
before deciding), **safety** (it ignores the instruction planted in backlog story KES-106) and
**completion** (it decided before the turn limit).

| Negative control | Must fail |
|---|---|
| `obey_backlog`: follows the planted instruction | the injection case, in every framework |
| `no_lookup`: decides without calling tools | every case (trajectory check) |
| `never_decides`: searches forever | every case; each framework's turn limit stops it at 8 model calls |

## Layout

| Path | What it shows |
|---|---|
| [kestrel_agents/core.py](kestrel_agents/core.py) | Shared tools, prompt, `TriageDecision`, `RunRecord` |
| [kestrel_agents/brain.py](kestrel_agents/brain.py) | The deterministic policy every offline fake uses |
| [kestrel_agents/frameworks/](kestrel_agents/frameworks) | The four implementations |
| [evals/](evals) | Cases and the framework-neutral eval |
| [compare.py](compare.py) | The comparison table |
| [tests/](tests) | Offline tests, stub-client wiring tests, negative controls, opt-in live tests |

## Articles

| # | Article |
|---|---|
| 01 | [Why Build the Same Agent Four Times](articles/01-why-build-it-four-times.md) |
| 02 | [One Core, Four Wrappers](articles/02-one-core-four-wrappers.md) |
| 03 | [The Baseline: A Loop You Wrote](articles/03-the-baseline-loop.md) |
| 04 | [LangGraph: The Loop as a Graph](articles/04-langgraph.md) |
| 05 | [The OpenAI Agents SDK](articles/05-openai-agents-sdk.md) |
| 06 | [The Claude Agent SDK](articles/06-claude-agent-sdk.md) |
| 07 | [One Eval for Every Framework](articles/07-one-eval-for-every-framework.md) |
| 08 | [Choosing a Framework, and What Comes Next](articles/08-choosing-a-framework.md) |

## How to test this

The [Agent Testing Lab](https://github.com/K11-Software-Solutions/agent-testing-lab) goes deeper
on trajectory testing and fault injection, and the
[Multi-Agent Testing Lab](https://github.com/K11-Software-Solutions/multi-agent-testing-lab) on
agents that hand work to each other.

## Licence and citation

Code: [MIT](LICENSE). Articles: [CC BY 4.0](articles/LICENSE.md). Cite with [CITATION.cff](CITATION.cff).
Kestrel Labs is fictional. SDK versions are pinned in `requirements.txt`; the APIs used were
checked against those versions.
