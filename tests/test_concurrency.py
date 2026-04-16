"""Concurrency tests for collector trace isolation."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

from drishti.collector import collector
from drishti.models.span import Span, TokenUsage
from drishti.models.trace import Trace


def _record_one(trace_name: str) -> tuple[str, int]:
    trace = Trace(name=trace_name)
    collector.start_trace(trace)

    span = Span(name=f"span-{trace_name}", provider="openai", model="gpt-4o")
    span.finish(output={"ok": True}, tokens=TokenUsage(total_tokens=1), cost=0.0)
    collector.record_span(span)

    ended = collector.end_trace()
    assert ended is not None
    return ended.name, len(ended.spans)


def test_threadpool_trace_isolation() -> None:
    names = [f"thread-{i}" for i in range(10)]
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(_record_one, names))

    assert sorted(name for name, _ in results) == sorted(names)
    assert all(span_count == 1 for _, span_count in results)


async def _async_record_one(trace_name: str) -> tuple[str, int, str]:
    trace = Trace(name=trace_name)
    collector.start_trace(trace)
    await asyncio.sleep(0)

    span = Span(name=f"span-{trace_name}", provider="openai", model="gpt-4o")
    span.finish(output={"ok": True}, tokens=TokenUsage(total_tokens=1), cost=0.0)
    collector.record_span(span)

    active_name = collector.active_trace.name if collector.active_trace else ""
    ended = collector.end_trace()
    assert ended is not None
    return active_name, len(ended.spans), ended.name


def test_async_trace_isolation() -> None:
    async def run() -> list[tuple[str, int, str]]:
        return await asyncio.gather(*[_async_record_one(f"async-{i}") for i in range(20)])

    results = asyncio.run(run())

    assert all(active == ended for active, _, ended in results)
    assert all(span_count == 1 for _, span_count, _ in results)
