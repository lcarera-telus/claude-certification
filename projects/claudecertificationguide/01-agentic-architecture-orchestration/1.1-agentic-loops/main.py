"""Exercise 1.1 — Agentic Loops.

A manual tool-use loop: Claude gets a calculator tool and a web-search stub,
and we hand-write the request -> tool_use -> tool_result -> request cycle
instead of using the SDK's tool runner, to see the mechanics directly.
"""

import ast
import operator
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "common"))
from client import DEFAULT_MODEL, get_client  # noqa: E402

TOOLS = [
    {
        "name": "calculator",
        "description": "Evaluate a basic arithmetic expression and return the result.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "An arithmetic expression, e.g. '12 * (3 + 4)'",
                }
            },
            "required": ["expression"],
        },
    },
    {
        "name": "web_search",
        "description": "Search the web for a query and return a list of mock results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"}
            },
            "required": ["query"],
        },
    },
]

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("unsupported expression")


def calculator(expression: str) -> str:
    try:
        result = _eval_node(ast.parse(expression, mode="eval").body)
    except Exception as exc:
        return f"error: could not evaluate '{expression}' ({exc})"
    return str(result)


def web_search(query: str) -> str:
    return (
        f"Mock results for '{query}':\n"
        "1. https://example.com/a - Overview and background\n"
        "2. https://example.com/b - Recent developments\n"
        "3. https://example.com/c - Frequently asked questions\n"
        "4. https://example.com/d - Population of Lanus is 1000\n"
    )


def execute_tool(name: str, tool_input: dict) -> str:
    if name == "calculator":
        return calculator(tool_input["expression"])
    if name == "web_search":
        return web_search(tool_input["query"])
    return f"error: unknown tool '{name}'"


def run_agentic_loop(client, user_message: str) -> str:
    messages = [{"role": "user", "content": user_message}]

    while True:
        response = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=1024,
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        print("---\nAssistant response:\n", response.stop_reason, "\n---")
        if response.stop_reason != "tool_use":
            return next(
                (b.text for b in response.content if b.type == "text"), ""
            )
        tool_results = []
        for block in response.content:
            print(f"Block: {block.type}")
            if block.type == "tool_use":
                print(f"Tool use block: {block.type} {block.name} {block.input}")
                result = execute_tool(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )
        messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    client = get_client()
    answer = run_agentic_loop(
        client,
        "Search for Lanus population and tell me what is that times 3",
    )
    print(answer)
