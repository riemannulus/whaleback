"""Monte Carlo simulation models package.

Provides multiple stochastic models for price path simulation:
- GBM: Geometric Brownian Motion (constant volatility)
- GARCH: GARCH(1,1) time-varying volatility
- HESTON: Heston stochastic volatility (two-factor)
- MERTON: Merton jump-diffusion
"""

from enum import Enum
from typing import Any, TypedDict

import numpy as np


class SimModel(str, Enum):
    GBM = "gbm"
    GARCH = "garch"
    HESTON = "heston"
    MERTON = "merton"


class HorizonStats(TypedDict):
    label: str
    p5: int
    p25: int
    p50: int
    p75: int
    p95: int
    expected_return_pct: float
    var_5pct_pct: float
    upside_prob: float


class ModelResult(TypedDict):
    """Standard return type for all simulation models."""
    model: str
    terminal_prices: dict[int, np.ndarray]  # horizon -> terminal price array
    horizons: dict[int, HorizonStats]


__all__ = ["SimModel", "HorizonStats", "ModelResult"]
