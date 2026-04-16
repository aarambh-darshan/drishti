"""Example: multi-step research agent with mixed-model routing."""

from __future__ import annotations

from drishti import trace

# Requires: pip install drishti-ai[openai]
import openai

client = openai.OpenAI()


@trace(name="multi-step-research-agent", budget_usd=0.10, on_exceed="warn")
def multi_step_agent(topic: str) -> str:
    """A realistic agent pipeline with planning, retrieval drafting, and synthesis."""

    planning = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Create a concise research plan with 3 sub-questions."},
            {"role": "user", "content": topic},
        ],
    )
    plan_text = planning.choices[0].message.content

    draft = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Draft bullet-point notes for each sub-question."},
            {"role": "user", "content": f"Topic: {topic}\nPlan:\n{plan_text}"},
        ],
    )
    draft_text = draft.choices[0].message.content

    synthesis = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Write a final polished answer using the notes."},
            {"role": "user", "content": f"Topic: {topic}\nPlan:\n{plan_text}\nNotes:\n{draft_text}"},
        ],
    )

    return synthesis.choices[0].message.content


if __name__ == "__main__":
    result = multi_step_agent("How do retrieval-augmented generation systems work?")
    print("\n--- Agent Result ---")
    print(result)
