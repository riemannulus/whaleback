"""Integration tests for ensemble combination and backward compatibility."""

import numpy as np
import pytest

from whaleback.analysis.simulation import run_monte_carlo, compute_simulation_score
from whaleback.analysis.sim_models import SimModel
from whaleback.analysis.sim_models.gbm import simulate_gbm
from whaleback.analysis.sim_models.ensemble import combine_ensemble


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def realistic_prices():
    """Generate 200 days of realistic stock prices."""
    rng = np.random.default_rng(42)
    daily_returns = rng.normal(0.0003, 0.015, 200)
    prices = [50000.0]
    for r in daily_returns:
        prices.append(prices[-1] * np.exp(r))
    return prices


@pytest.fixture
def short_prices():
    """Too few prices for simulation."""
    return [50000.0 + i * 100 for i in range(30)]


# ---------------------------------------------------------------------------
# Backward Compatibility Tests
# ---------------------------------------------------------------------------

class TestBackwardCompatibility:
    """Ensure run_monte_carlo returns all original keys."""

    REQUIRED_KEYS = {
        "simulation_score", "simulation_grade", "base_price",
        "mu", "sigma", "num_simulations", "input_days_used",
        "horizons", "target_probs",
    }

    def test_all_original_keys_present(self, realistic_prices):
        result = run_monte_carlo(realistic_prices, num_simulations=500, ticker="005930")
        assert result is not None
        assert self.REQUIRED_KEYS.issubset(result.keys())

    def test_model_breakdown_present(self, realistic_prices):
        result = run_monte_carlo(realistic_prices, num_simulations=500, ticker="005930")
        assert result is not None
        assert "model_breakdown" in result

    def test_horizons_structure(self, realistic_prices):
        result = run_monte_carlo(realistic_prices, num_simulations=500, ticker="005930")
        horizons = result["horizons"]
        for h_key, h_data in horizons.items():
            assert "label" in h_data
            assert "p5" in h_data
            assert "p50" in h_data
            assert "expected_return_pct" in h_data
            assert "upside_prob" in h_data

    def test_simulation_score_range(self, realistic_prices):
        result = run_monte_carlo(realistic_prices, num_simulations=500, ticker="005930")
        score = result["simulation_score"]
        if score is not None:
            assert 0.0 <= score <= 100.0

    def test_simulation_grade_valid(self, realistic_prices):
        result = run_monte_carlo(realistic_prices, num_simulations=500, ticker="005930")
        grade = result["simulation_grade"]
        if grade is not None:
            assert grade in ("positive", "neutral_positive", "neutral", "negative")

    def test_insufficient_data_returns_none(self, short_prices):
        result = run_monte_carlo(short_prices)
        assert result is None

    def test_empty_prices_returns_none(self):
        assert run_monte_carlo([]) is None
        assert run_monte_carlo(None) is None


# ---------------------------------------------------------------------------
# Ensemble Tests
# ---------------------------------------------------------------------------

class TestEnsemble:
    def test_multi_model_returns_breakdown(self, realistic_prices):
        result = run_monte_carlo(
            realistic_prices,
            num_simulations=500,
            ticker="005930",
            models=(SimModel.GBM, SimModel.GARCH, SimModel.HESTON, SimModel.MERTON),
        )
        assert result is not None
        bd = result.get("model_breakdown")
        assert bd is not None
        assert "model_scores" in bd
        assert len(bd["model_scores"]) >= 2  # at least 2 models succeeded

    def test_single_model_no_breakdown(self, realistic_prices):
        result = run_monte_carlo(
            realistic_prices,
            num_simulations=500,
            ticker="005930",
            models=(SimModel.GBM,),
        )
        assert result is not None
        assert result["model_breakdown"] is None

    def test_custom_weights(self, realistic_prices):
        result = run_monte_carlo(
            realistic_prices,
            num_simulations=500,
            ticker="005930",
            weights={
                "gbm": 0.5, "garch": 0.2, "heston": 0.2, "merton": 0.1,
            },
        )
        assert result is not None
        assert result["simulation_score"] is not None

    def test_ensemble_weight_renormalization(self):
        """If a model fails, weights should renormalize."""
        rng = np.random.default_rng(42)
        log_returns = rng.normal(0.0003, 0.015, 200)
        base_price = 50000

        gbm_result = simulate_gbm(log_returns, base_price, 500, (63, 126), rng)
        assert gbm_result is not None

        # Only GBM succeeds
        result = combine_ensemble(
            model_results={"gbm": gbm_result},
            weights={"gbm": 0.25, "garch": 0.30, "heston": 0.20, "merton": 0.25},
            horizons=(63, 126),
            base_price=base_price,
            target_multipliers=(1.1, 1.2),
        )
        assert result is not None
        assert "horizons" in result


# ---------------------------------------------------------------------------
# Scoring Tests
# ---------------------------------------------------------------------------

class TestScoring:
    def test_compute_simulation_score_valid(self):
        horizons = {
            63: {"expected_return_pct": 5.0, "upside_prob": 0.6, "var_5pct_pct": -10.0},
            126: {"expected_return_pct": 10.0, "upside_prob": 0.65, "var_5pct_pct": -15.0},
        }
        result = compute_simulation_score(horizons)
        assert result["score"] is not None
        assert 0 <= result["score"] <= 100

    def test_compute_simulation_score_missing_horizon(self):
        horizons = {63: {"expected_return_pct": 5.0, "upside_prob": 0.6, "var_5pct_pct": -10.0}}
        result = compute_simulation_score(horizons)
        assert result["score"] is None


# ---------------------------------------------------------------------------
# Seed Stability Tests
# ---------------------------------------------------------------------------

class TestSeedStability:
    def test_hashlib_seed_reproducibility(self, realistic_prices):
        """Same ticker should produce same results across calls."""
        r1 = run_monte_carlo(realistic_prices, num_simulations=500, ticker="005930",
                             models=(SimModel.GBM,))
        r2 = run_monte_carlo(realistic_prices, num_simulations=500, ticker="005930",
                             models=(SimModel.GBM,))
        assert r1["simulation_score"] == r2["simulation_score"]
        assert r1["horizons"][126]["p50"] == r2["horizons"][126]["p50"]

    def test_different_tickers_different_results(self, realistic_prices):
        r1 = run_monte_carlo(realistic_prices, num_simulations=500, ticker="005930",
                             models=(SimModel.GBM,))
        r2 = run_monte_carlo(realistic_prices, num_simulations=500, ticker="035420",
                             models=(SimModel.GBM,))
        # Different seeds should produce different median prices (very unlikely to match)
        assert r1["horizons"][126]["p50"] != r2["horizons"][126]["p50"]
