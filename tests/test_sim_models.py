"""Unit tests for individual simulation models."""

import numpy as np
import pytest

from whaleback.analysis.sim_models import SimModel, ModelResult
from whaleback.analysis.sim_models.gbm import simulate_gbm
from whaleback.analysis.sim_models.garch import simulate_garch
from whaleback.analysis.sim_models.heston import simulate_heston
from whaleback.analysis.sim_models.merton import simulate_merton


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_log_returns():
    """Generate realistic daily log returns (~20% annual vol)."""
    rng = np.random.default_rng(42)
    daily_vol = 0.20 / np.sqrt(252)
    daily_mu = 0.08 / 252
    returns = rng.normal(daily_mu, daily_vol, 200)
    return returns


@pytest.fixture
def rng():
    return np.random.default_rng(12345)


BASE_PRICE = 50000
HORIZONS = (21, 63, 126, 252)
NUM_SIMS = 1000  # smaller for test speed


# ---------------------------------------------------------------------------
# GBM Tests
# ---------------------------------------------------------------------------

class TestGBM:
    def test_returns_model_result(self, sample_log_returns, rng):
        result = simulate_gbm(sample_log_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng)
        assert result is not None
        assert result["model"] == "gbm"

    def test_terminal_prices_shape(self, sample_log_returns, rng):
        result = simulate_gbm(sample_log_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng)
        for h in HORIZONS:
            assert h in result["terminal_prices"]
            assert len(result["terminal_prices"][h]) == NUM_SIMS

    def test_horizons_have_required_keys(self, sample_log_returns, rng):
        result = simulate_gbm(sample_log_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng)
        required_keys = {"label", "p5", "p25", "p50", "p75", "p95",
                         "expected_return_pct", "var_5pct_pct", "upside_prob"}
        for h in HORIZONS:
            assert required_keys.issubset(result["horizons"][h].keys())

    def test_percentile_ordering(self, sample_log_returns, rng):
        result = simulate_gbm(sample_log_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng)
        for h in HORIZONS:
            stats = result["horizons"][h]
            assert stats["p5"] <= stats["p25"] <= stats["p50"] <= stats["p75"] <= stats["p95"]

    def test_upside_prob_range(self, sample_log_returns, rng):
        result = simulate_gbm(sample_log_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng)
        for h in HORIZONS:
            prob = result["horizons"][h]["upside_prob"]
            assert 0.0 <= prob <= 1.0

    def test_zero_volatility_returns_none(self, rng):
        flat_returns = np.zeros(100)
        result = simulate_gbm(flat_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng)
        assert result is None

    def test_sigma_capping(self, rng):
        """Extreme volatility should be capped."""
        wild_returns = np.random.default_rng(1).normal(0, 0.5, 200)  # ~800% annual vol
        result = simulate_gbm(wild_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng, max_sigma=1.50)
        assert result is not None

    def test_reproducibility(self, sample_log_returns):
        rng1 = np.random.default_rng(999)
        rng2 = np.random.default_rng(999)
        r1 = simulate_gbm(sample_log_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng1)
        r2 = simulate_gbm(sample_log_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng2)
        np.testing.assert_array_equal(r1["terminal_prices"][63], r2["terminal_prices"][63])


# ---------------------------------------------------------------------------
# GARCH Tests
# ---------------------------------------------------------------------------

class TestGARCH:
    def test_returns_model_result(self, sample_log_returns, rng):
        result = simulate_garch(sample_log_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng)
        assert result is not None
        assert result["model"] == "garch"

    def test_terminal_prices_shape(self, sample_log_returns, rng):
        result = simulate_garch(sample_log_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng)
        for h in HORIZONS:
            assert h in result["terminal_prices"]
            assert len(result["terminal_prices"][h]) == NUM_SIMS

    def test_insufficient_data_returns_none(self, rng):
        short_returns = np.random.default_rng(1).normal(0, 0.01, 10)
        result = simulate_garch(short_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng)
        assert result is None

    def test_percentile_ordering(self, sample_log_returns, rng):
        result = simulate_garch(sample_log_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng)
        for h in HORIZONS:
            stats = result["horizons"][h]
            assert stats["p5"] <= stats["p25"] <= stats["p50"] <= stats["p75"] <= stats["p95"]

    def test_terminal_prices_capped(self, sample_log_returns, rng):
        """Terminal prices should be within [base*0.001, base*100]."""
        result = simulate_garch(sample_log_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng)
        for h in HORIZONS:
            tp = result["terminal_prices"][h]
            assert np.all(tp >= BASE_PRICE * 0.001)
            assert np.all(tp <= BASE_PRICE * 100)


# ---------------------------------------------------------------------------
# Heston Tests
# ---------------------------------------------------------------------------

class TestHeston:
    def test_returns_model_result(self, sample_log_returns, rng):
        result = simulate_heston(sample_log_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng)
        assert result is not None
        assert result["model"] == "heston"

    def test_terminal_prices_shape(self, sample_log_returns, rng):
        result = simulate_heston(sample_log_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng)
        for h in HORIZONS:
            assert h in result["terminal_prices"]
            assert len(result["terminal_prices"][h]) == NUM_SIMS

    def test_insufficient_data_returns_none(self, rng):
        short_returns = np.random.default_rng(1).normal(0, 0.01, 10)
        result = simulate_heston(short_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng)
        assert result is None

    def test_percentile_ordering(self, sample_log_returns, rng):
        result = simulate_heston(sample_log_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng)
        for h in HORIZONS:
            stats = result["horizons"][h]
            assert stats["p5"] <= stats["p25"] <= stats["p50"] <= stats["p75"] <= stats["p95"]

    def test_terminal_prices_capped(self, sample_log_returns, rng):
        result = simulate_heston(sample_log_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng)
        for h in HORIZONS:
            tp = result["terminal_prices"][h]
            assert np.all(tp >= BASE_PRICE * 0.001)
            assert np.all(tp <= BASE_PRICE * 100)

    def test_custom_params(self, sample_log_returns, rng):
        """Should work with non-default Heston params."""
        result = simulate_heston(
            sample_log_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng,
            kappa=3.0, theta=0.02, xi=0.2, rho=-0.5
        )
        assert result is not None


# ---------------------------------------------------------------------------
# Merton Tests
# ---------------------------------------------------------------------------

class TestMerton:
    def test_returns_model_result(self, sample_log_returns, rng):
        result = simulate_merton(sample_log_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng)
        assert result is not None
        assert result["model"] == "merton"

    def test_terminal_prices_shape(self, sample_log_returns, rng):
        result = simulate_merton(sample_log_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng)
        for h in HORIZONS:
            assert h in result["terminal_prices"]
            assert len(result["terminal_prices"][h]) == NUM_SIMS

    def test_insufficient_data_returns_none(self, rng):
        short_returns = np.random.default_rng(1).normal(0, 0.01, 10)
        result = simulate_merton(short_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng)
        assert result is None

    def test_percentile_ordering(self, sample_log_returns, rng):
        result = simulate_merton(sample_log_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng)
        for h in HORIZONS:
            stats = result["horizons"][h]
            assert stats["p5"] <= stats["p25"] <= stats["p50"] <= stats["p75"] <= stats["p95"]

    def test_terminal_prices_capped(self, sample_log_returns, rng):
        result = simulate_merton(sample_log_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng)
        for h in HORIZONS:
            tp = result["terminal_prices"][h]
            assert np.all(tp >= BASE_PRICE * 0.001)
            assert np.all(tp <= BASE_PRICE * 100)

    def test_zero_jump_intensity(self, sample_log_returns, rng):
        """With lambda=0, should behave like GBM."""
        result = simulate_merton(
            sample_log_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng,
            lam=0.0
        )
        assert result is not None

    def test_high_jump_intensity(self, sample_log_returns, rng):
        """High jump intensity should produce wider distributions."""
        result = simulate_merton(
            sample_log_returns, BASE_PRICE, NUM_SIMS, HORIZONS, rng,
            lam=2.0, mu_j=-0.05, sigma_j=0.10
        )
        assert result is not None
