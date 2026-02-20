"""Pytest configuration and shared fixtures."""

import pytest


@pytest.fixture
def sample_current_fundamentals():
    """Sample current period fundamentals."""
    return {
        "eps": 5000,
        "roe": 15.0,
        "bps": 60000,
        "pbr": 0.8,
        "per": 10.0,
        "div": 2.5,
    }


@pytest.fixture
def sample_previous_fundamentals():
    """Sample previous period fundamentals."""
    return {
        "eps": 3000,
        "roe": 12.0,
        "bps": 50000,
    }


@pytest.fixture
def sample_sector_medians():
    """Sample sector median metrics."""
    return {
        "median_pbr": 1.0,
        "median_per": 15.0,
    }
