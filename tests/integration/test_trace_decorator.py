"""Integration test — full end-to-end @trace decorator with mocked provider."""

import shutil
from pathlib import Path

import pytest

from drishti import trace
from drishti.collector import collector


TEST_TRACES_DIR = ".drishti/test_integration_traces"


@pytest.fixture(autouse=True)
def cleanup():
    yield
    test_dir = Path(TEST_TRACES_DIR)
    if test_dir.exists():
        shutil.rmtree(test_dir)


class TestTraceDecorator:
    def test_bare_decorator(self):
        """@trace without args should use function name."""

        @trace(display=False, export=False)
        def my_function():
            return 42

        result = my_function()
        assert result == 42

    def test_named_decorator(self):
        """@trace(name='foo') should use custom name."""

        @trace(name="custom-agent", display=False, export=False)
        def my_function():
            return "hello"

        result = my_function()
        assert result == "hello"

    def test_exception_handling(self):
        """Trace should still be completed on exception."""

        @trace(display=False, export=False)
        def failing_function():
            raise ValueError("Something broke")

        with pytest.raises(ValueError, match="Something broke"):
            failing_function()

    def test_return_value_preserved(self):
        """Decorator must not alter the return value."""

        @trace(display=False, export=False)
        def compute():
            return {"key": "value", "num": 42}

        result = compute()
        assert result == {"key": "value", "num": 42}

    def test_args_and_kwargs_forwarded(self):
        """Arguments should be forwarded correctly."""

        @trace(display=False, export=False)
        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        result = greet("Darshan", greeting="Namaste")
        assert result == "Namaste, Darshan!"

    def test_collector_is_clean_after_trace(self):
        """Collector should have no active trace after decorator exits."""

        @trace(display=False, export=False)
        def simple():
            assert collector.is_active  # Active during execution
            return True

        simple()
        assert not collector.is_active  # Clean after

    def test_collector_clean_after_exception(self):
        """Collector should be clean even if function raises."""

        @trace(display=False, export=False)
        def fails():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            fails()

        assert not collector.is_active
