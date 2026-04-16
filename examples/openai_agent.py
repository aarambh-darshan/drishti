"""
Example: OpenAI Agent with Drishti tracing.

Usage:
    export OPENAI_API_KEY=sk-...
    python examples/openai_agent.py
"""

from drishti import trace

# Requires: pip install drishti[openai]
import openai

client = openai.OpenAI()


@trace(name="research-agent")
def research_agent(query: str) -> str:
    """A simple research agent that makes two LLM calls."""

    # Step 1: Generate search queries
    plan = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Generate 3 search queries for the topic."},
            {"role": "user", "content": query},
        ],
    )
    queries = plan.choices[0].message.content

    # Step 2: Synthesize answer
    answer = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a research assistant. Synthesize an answer."},
            {"role": "user", "content": f"Topic: {query}\nQueries: {queries}"},
        ],
    )

    return answer.choices[0].message.content


if __name__ == "__main__":
    result = research_agent("What is quantum computing?")
    print("\n--- Agent Result ---")
    print(result)
