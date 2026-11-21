"""Print the comparison table: code size per implementation, and what each one hands you.

    python compare.py

Code size counts lines of executable code in each framework module (no blank lines, comments
or docstrings). The shared tools, prompt and record in core.py are the same for all four and
are not counted.
"""
from __future__ import annotations

import ast
from pathlib import Path

FRAMEWORKS = Path(__file__).parent / "kestrel_agents" / "frameworks"

ROWS = [
    ("raw", "raw.py", "you write it", "submit_decision tool", "you write it", "yes (step() fake)"),
    ("langgraph", "langgraph_agent.py", "graph edges", "submit_decision tool", "checkpointer (thread_id)", "yes (same step() fake)"),
    ("openai_agents", "openai_agents.py", "Runner", "output_type (Pydantic)", "sessions", "yes (custom Model)"),
    ("claude_agent_sdk", "claude_agent_sdk.py", "Claude Code harness", "output_format (JSON schema)", "sessions, resume, fork", "no (CLI subprocess)"),
]


def code_lines(path: Path) -> int:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    doc_lines = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and ast.get_docstring(node):
            d = node.body[0]
            doc_lines.update(range(d.lineno, d.end_lineno + 1))
    count = 0
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if s and not s.startswith("#") and i not in doc_lines:
            count += 1
    return count


def table() -> str:
    head = "| Implementation | Code lines | Loop run by | Final answer via | State and resume | Runs offline in CI |\n|---|---|---|---|---|---|"
    rows = [f"| {n} | {code_lines(FRAMEWORKS / f)} | {loop} | {final} | {state} | {offline} |" for n, f, loop, final, state, offline in ROWS]
    return "\n".join([head, *rows])


if __name__ == "__main__":
    print(table())
