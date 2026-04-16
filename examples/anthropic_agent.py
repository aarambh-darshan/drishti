"""
Example: Anthropic Agent with Drishti tracing.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python examples/anthropic_agent.py
"""

from drishti import trace

# Requires: pip install drishti[anthropic]
import anthropic

client = anthropic.Anthropic()


@trace(name="claude-agent")
def claude_agent(query: str) -> str:
    """A simple agent using Claude."""

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": query},
        ],
    )

    return response.content[0].text


if __name__ == "__main__":
    result = claude_agent("Explain the theory of relativity in simple terms.")
    print("\n--- Agent Result ---")
    print(result)
