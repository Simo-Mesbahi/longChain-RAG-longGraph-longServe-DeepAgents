"""Print a minimal official Deep Agents SDK template."""

SDK_TEMPLATE = '''"""Template for adapting this course project to the official SDK."""

from deepagents import create_deep_agent


def search_evidence(query: str) -> str:
    """Search the approved documentary corpus and return cited evidence."""
    raise NotImplementedError


researcher = {
    "name": "researcher",
    "description": "Search approved evidence and write raw findings to files.",
    "prompt": "Never invent sources. Use files for large outputs.",
}

verifier = {
    "name": "verifier",
    "description": "Check evidence sufficiency and human-review constraints.",
    "prompt": "Route sensitive or unsupported claims to review.",
}

writer = {
    "name": "writer",
    "description": "Draft only cited answers or controlled review requests.",
    "prompt": "Publish only verified claims with approved citations.",
}

agent = create_deep_agent(
    tools=[search_evidence],
    instructions="You are a documentary investigation analyst.",
    subagents=[researcher, verifier, writer],
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "Quelle est la franchise ?"}]}
)
print(result)
'''


def main() -> int:
    print(SDK_TEMPLATE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
