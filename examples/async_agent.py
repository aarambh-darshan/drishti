"""
Example: Async Agent with Drishti tracing.

Demonstrates that @trace works seamlessly with async functions.

Usage:
    export OPENAI_API_KEY=sk-...
    python examples/async_agent.py
"""

import asyncio

from drishti import trace

# Requires: pip install drishti[openai]
import openai

client = openai.AsyncOpenAI()


@trace(name="async-research-agent")
async def async_research_agent(query: str) -> str:
    """An async research agent that makes concurrent LLM calls."""

    # Step 1: Plan (single call)
    plan = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Generate a research plan for the topic."},
            {"role": "user", "content": query},
        ],
    )
    plan_text = plan.choices[0].message.content

    # Step 2: Synthesize
    answer = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Synthesize a comprehensive answer."},
            {"role": "user", "content": f"Topic: {query}\nPlan: {plan_text}"},
        ],
    )

    return answer.choices[0].message.content


if __name__ == "__main__":
    result = asyncio.run(async_research_agent("What is quantum computing?"))
    print("\n--- Agent Result ---")
    print(result)
