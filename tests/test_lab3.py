"""Lab 3 tests. Offline by default; live runs need AGENTS_LIVE=1 plus credentials."""
import asyncio
import json
import os
from types import SimpleNamespace as NS

import pytest

from evals.run_evals import OFFLINE, check, evaluate, load_cases
from kestrel_agents.core import TOOL_SPECS, RunRecord, TriageDecision, call_tool, json_schema, search_docs
from kestrel_agents.frameworks import claude_agent_sdk as cas
from kestrel_agents.frameworks import langgraph_agent, raw
from kestrel_agents.llm import TOOLS

CASES = load_cases()
ALL_IDS = {c["id"] for c in CASES}


# --- shared tools ---------------------------------------------------------------------------

def test_tool_schemas_are_strict():
    for t in TOOLS:
        s = t["input_schema"]
        assert t["strict"] and s["additionalProperties"] is False and set(s["required"]) == set(s["properties"])


def test_docs_search_skips_superseded_adrs():
    hits = search_docs("message queue RabbitMQ")
    assert hits and all("adr-003" not in h["id"] for h in hits)


def test_tool_errors_are_returned():
    assert call_tool("get_story", {"story_id": "KES-999"})[1] is True
    assert call_tool("delete_everything", {})[1] is True


# --- the same eval, every offline framework --------------------------------------------------

@pytest.mark.parametrize("framework", OFFLINE)
def test_eval_passes(framework):
    rows = evaluate(framework, CASES)
    assert all(r["passed"] for r in rows), [r for r in rows if not r["passed"]]


@pytest.mark.parametrize("framework", OFFLINE)
def test_frameworks_agree_on_the_trajectory(framework):
    base = evaluate("raw", CASES)
    rows = evaluate(framework, CASES)
    assert [r["tools"] for r in rows] == [r["tools"] for r in base]


@pytest.mark.parametrize("framework", OFFLINE)
@pytest.mark.parametrize("behaviour, expected", [
    ("obey_backlog", {"T7"}),
    ("no_lookup", ALL_IDS),          # decides without looking: the trajectory check fails every case
    ("never_decides", ALL_IDS),
])
def test_negative_controls(framework, behaviour, expected):
    """Each broken behaviour must fail the eval, in every framework."""
    rows = evaluate(framework, CASES, behaviour=behaviour)
    assert {r["id"] for r in rows if not r["passed"]} == expected


@pytest.mark.parametrize("framework", OFFLINE)
def test_turn_limit_stops_a_runaway_agent(framework):
    from evals.run_evals import runner
    rec = runner(framework)("anything", behaviour="never_decides")
    assert rec.decision is None and "no decision" in rec.error
    assert rec.model_calls == 8


def test_langgraph_state_is_checkpointed():
    from kestrel_agents.llm import FakeLLM
    graph = langgraph_agent.build(FakeLLM())
    config = {"configurable": {"thread_id": "t-42"}}
    graph.invoke({"messages": [{"role": "user", "content": "Export the sprint report as a PDF file"}], "tool_calls": [],
                  "usage": [], "pending": [], "decision": None, "error": ""}, config)
    history = list(graph.get_state_history(config))
    assert len(history) >= 7                             # a checkpoint after every node
    assert graph.get_state(config).values["decision"]["story_id"] == "KES-101"
    assert "model" in graph.get_graph().draw_mermaid()


def test_check_reports_missing_trajectory():
    rec = RunRecord("x", "r", TriageDecision(decision="duplicate", story_id="KES-103", reason="r"))
    assert check(CASES[0], rec) == ["never called search_backlog, get_story"]


# --- Claude Agent SDK: what can be checked without running Claude Code -----------------------

def test_claude_agent_sdk_options():
    o = cas.build_options(effort="low", max_turns=5)
    assert o.tools == [] and o.setting_sources == []
    assert o.allowed_tools == [f"mcp__kestrel__{n}" for n in TOOL_SPECS]
    assert o.output_format["schema"] == TriageDecision.model_json_schema()
    assert (o.model, o.effort, o.max_turns) == ("claude-opus-5-5", "low", 5)
    assert "kestrel" in o.mcp_servers


def test_claude_agent_sdk_tool_handlers():
    by_name = {t.name: t for t in cas.SDK_TOOLS}
    assert set(by_name) == set(TOOL_SPECS)
    assert by_name["get_story"].input_schema == json_schema("get_story")
    ok = asyncio.run(by_name["search_backlog"].handler({"query": "dark mode"}))
    assert json.loads(ok["content"][0]["text"])[0]["id"] == "KES-104" and ok["is_error"] is False
    err = asyncio.run(by_name["get_story"].handler({"story_id": "KES-999"}))
    assert err["is_error"] is True


def test_claude_agent_sdk_message_handling(monkeypatch):
    """Feed _run a scripted message stream, as query() would yield it."""
    from claude_agent_sdk import AssistantMessage, ResultMessage, ToolUseBlock

    async def fake_query(prompt, options):
        yield AssistantMessage(content=[ToolUseBlock(id="t1", name="mcp__kestrel__search_backlog", input={"query": "pdf"})], model="m")
        yield ResultMessage(subtype="success", duration_ms=1, duration_api_ms=1, is_error=False, num_turns=3, session_id="s",
                            total_cost_usd=0.012, usage={"input_tokens": 900, "output_tokens": 80},
                            structured_output={"decision": "duplicate", "story_id": "KES-101", "reason": "same"})
    monkeypatch.setattr(cas, "query", fake_query)
    rec = RunRecord("claude_agent_sdk", "Export PDF")
    asyncio.run(cas._run("Export PDF", cas.build_options(), rec))
    assert rec.tools_used == ["search_backlog"] and rec.decision.story_id == "KES-101"
    assert (rec.model_calls, rec.cost_usd, rec.input_tokens) == (3, 0.012, 900)


def test_claude_agent_sdk_has_no_offline_mode():
    with pytest.raises(ValueError):
        cas.run("x", provider="fake")


# --- Claude Messages API wiring (raw and LangGraph), with a stub client ----------------------

class _Stub:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []
        self.beta = self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        return self.responses.pop(0)


class _Block(NS):
    def model_dump(self, **_):
        return dict(vars(self))


def _tool_use(name, args, i):
    return NS(stop_reason="tool_use", model="claude-opus-5-5", usage=NS(input_tokens=1000, output_tokens=100),
              content=[_Block(type="tool_use", id=f"t{i}", name=name, input=args)])


@pytest.mark.parametrize("module", [raw, langgraph_agent])
def test_claude_wiring(module):
    from kestrel_agents.llm import ClaudeLLM
    stub = _Stub([_tool_use("search_backlog", {"query": "pdf"}, 1),
                  _tool_use("submit_decision", {"decision": "new", "story_id": None, "reason": "r"}, 2)])
    rec = module.run("Export a PDF", llm=ClaudeLLM(effort="low", client=stub))
    assert rec.decision.decision == "new" and rec.tools_used == ["search_backlog"]
    kw = stub.calls[0]
    assert kw["fallbacks"] == "default" and kw["output_config"] == {"effort": "low"}
    assert kw["betas"] == ["server-side-fallback-2026-07-01"]
    assert rec.cost_usd == pytest.approx(2 * (1000 * 4 + 100 * 20) / 1e6)
    sent = stub.calls[1]["messages"]
    assert sent[1] == {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "search_backlog", "input": {"query": "pdf"}}]}
    assert sent[2]["role"] == "user" and sent[2]["content"][0]["type"] == "tool_result"


# --- live (opt-in) --------------------------------------------------------------------------

LIVE = pytest.mark.skipif(os.environ.get("AGENTS_LIVE") != "1", reason="set AGENTS_LIVE=1 (costs money)")


@LIVE
@pytest.mark.parametrize("framework, provider", [("raw", "claude"), ("langgraph", "claude"), ("claude_agent_sdk", "claude"),
                                                 ("openai_agents", "openai")])
def test_live(framework, provider):
    rows = evaluate(framework, CASES, provider)
    print(json.dumps(rows, indent=2))
    assert sum(r["passed"] for r in rows) >= len(rows) - 1
