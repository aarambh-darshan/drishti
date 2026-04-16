"""Integration test — async @trace decorator."""

import asyncio

import pytest

from drishti import trace
from drishti.collector import collector


class TestAsyncTrace:
    @pytest.mark.asyncio
    async def test_async_decorator(self):
        """@trace should work with async functions."""

        @trace(display=False, export=False)
        async def async_agent(query):
            await asyncio.sleep(0.01)
            return f"Answer to: {query}"

        result = await async_agent("What is AI?")
        assert result == "Answer to: What is AI?"

    @pytest.mark.asyncio
    async def test_async_exception_handling(self):
        """Async trace should handle exceptions correctly."""

        @trace(display=False, export=False)
        async def async_failing():
            await asyncio.sleep(0.01)
            raise ValueError("Async error")

        with pytest.raises(ValueError, match="Async error"):
            await async_failing()

        assert not collector.is_active

    @pytest.mark.asyncio
    async def test_async_return_value(self):
        """Async decorator must preserve return values."""

        @trace(display=False, export=False)
        async def async_compute():
            await asyncio.sleep(0.01)
            return {"result": 42}

        result = await async_compute()
        assert result == {"result": 42}

    @pytest.mark.asyncio
    async def test_async_collector_lifecycle(self):
        """Collector should be active during async execution and clean after."""
        was_active = False

        @trace(display=False, export=False)
        async def async_check():
            nonlocal was_active
            was_active = collector.is_active
            return True

        await async_check()
        assert was_active
        assert not collector.is_active
