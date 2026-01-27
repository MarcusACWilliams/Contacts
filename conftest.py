"""Pytest configuration and shared fixtures"""
import pytest
import asyncio
from typing import Generator


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def reset_app_state():
    """Reset application state before each test"""
    # This fixture runs before each test to ensure clean state
    yield
    # Cleanup after test if needed
