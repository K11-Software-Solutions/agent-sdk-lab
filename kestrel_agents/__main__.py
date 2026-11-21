"""Run one triage request through one implementation.

    python -m kestrel_agents raw "Export the sprint report as a PDF file"
    python -m kestrel_agents langgraph "..." --provider claude
    python -m kestrel_agents openai_agents "..." --provider openai
    python -m kestrel_agents claude_agent_sdk "..."
"""
from __future__ import annotations

import argparse
import json
import sys

from evals.run_evals import ALL, runner


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m kestrel_agents", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("framework", choices=ALL)
    p.add_argument("request")
    p.add_argument("--provider", default=None, help="fake (default, not for claude_agent_sdk), claude or openai")
    a = p.parse_args(argv)
    provider = a.provider or ("claude" if a.framework == "claude_agent_sdk" else "fake")
    try:
        rec = runner(a.framework)(a.request, provider="live" if provider == "openai" else provider)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for name, args in rec.tool_calls:
        print(f"  {name}({json.dumps(args)})")
    if rec.error:
        print(f"error: {rec.error}", file=sys.stderr)
        return 1
    print(json.dumps(rec.decision.model_dump(), indent=2))
    cost = f"${rec.cost_usd:.4f}" if rec.cost_usd is not None else "n/a"
    print(f"[{rec.framework}/{provider}] model calls {rec.model_calls}, tokens {rec.input_tokens}+{rec.output_tokens}, cost {cost}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
