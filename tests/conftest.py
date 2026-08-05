"""Shared fixtures for custom component tests."""

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading integrations from this repository."""
    yield
