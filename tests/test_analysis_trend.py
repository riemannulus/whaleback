"""Unit tests for trend analysis module.

Tests for compute_relative_strength, compute_rs_percentile,
compute_sector_rotation, and compute_sector_ranking.
"""

from whaleback.analysis.trend import (
    compute_relative_strength,
    compute_rs_percentile,
    compute_sector_rotation,
    compute_sector_ranking,
)


class TestComputeRelativeStrength:
    """Test compute_relative_strength function."""

    def test_outperformance(self):
        """Stock goes up 20%, index goes up 10%."""
        stock = [100, 105, 110, 115, 120]
        index = [1000, 1025, 1050, 1075, 1100]
        result = compute_relative_strength(stock, index)
        assert result["current_rs"] > 1.0  # Outperforming
        assert result["rs_change_pct"] > 0
        assert len(result["series"]) == 5

    def test_underperformance(self):
        """Stock goes up 5%, index goes up 20%."""
        stock = [100, 101, 102, 103, 105]
        index = [1000, 1050, 1100, 1150, 1200]
        result = compute_relative_strength(stock, index)
        assert result["current_rs"] < 1.0

    def test_equal_performance(self):
        """Both go up 10%."""
        stock = [100, 105, 110]
        index = [1000, 1050, 1100]
        result = compute_relative_strength(stock, index)
        assert abs(result["current_rs"] - 1.0) < 0.01

    def test_empty_input(self):
        """Empty lists return None values."""
        result = compute_relative_strength([], [])
        assert result["current_rs"] is None
        assert result["series"] == []

    def test_single_point(self):
        """Single data point returns None (need at least 2)."""
        result = compute_relative_strength([100], [1000])
        assert result["current_rs"] is None

    def test_mismatched_lengths(self):
        """Mismatched lengths are trimmed to minimum."""
        stock = [100, 110, 120]
        index = [1000, 1100, 1200, 1300, 1400]
        result = compute_relative_strength(stock, index)
        assert len(result["series"]) == 3  # Trimmed to min length

    def test_with_dates(self):
        """Dates are included in series when provided."""
        stock = [100, 110]
        index = [1000, 1100]
        dates = ["2024-01-01", "2024-01-02"]
        result = compute_relative_strength(stock, index, dates)
        assert result["series"][0]["date"] == "2024-01-01"
        assert result["series"][1]["date"] == "2024-01-02"

    def test_zero_base(self):
        """Zero base values return None."""
        result = compute_relative_strength([0, 100], [1000, 1100])
        assert result["current_rs"] is None

    def test_first_entry_always_100(self):
        """First indexed values should always be 100."""
        stock = [500, 600]
        index = [2000, 2400]
        result = compute_relative_strength(stock, index)
        assert result["series"][0]["stock_indexed"] == 100.0
        assert result["series"][0]["index_indexed"] == 100.0

    def test_rs_ratio_calculation(self):
        """Verify RS ratio is stock_indexed / index_indexed."""
        stock = [100, 120]  # +20%
        index = [1000, 1100]  # +10%
        result = compute_relative_strength(stock, index)
        # stock_indexed[1] = 120, index_indexed[1] = 110
        # rs_ratio[1] = 120/110 ≈ 1.0909
        assert result["series"][1]["stock_indexed"] == 120.0
        assert result["series"][1]["index_indexed"] == 110.0
        assert abs(result["series"][1]["rs_ratio"] - 1.0909) < 0.001

    def test_negative_price_base(self):
        """Negative base price returns None."""
        result = compute_relative_strength([-100, -50], [1000, 1100])
        assert result["current_rs"] is None

    def test_rs_change_pct(self):
        """Verify RS change percentage calculation."""
        stock = [100, 110, 120]
        index = [1000, 1050, 1100]
        result = compute_relative_strength(stock, index)
        first_rs = result["series"][0]["rs_ratio"]
        last_rs = result["series"][-1]["rs_ratio"]
        expected_change = (last_rs - first_rs) / first_rs * 100
        assert abs(result["rs_change_pct"] - expected_change) < 0.01


class TestComputeRSPercentile:
    """Test compute_rs_percentile function."""

    def test_top_performer(self):
        """Highest RS value should return 100."""
        assert compute_rs_percentile(1.5, [0.8, 0.9, 1.0, 1.1, 1.2]) == 100

    def test_bottom_performer(self):
        """Lowest RS value should return 0."""
        assert compute_rs_percentile(0.5, [0.8, 0.9, 1.0, 1.1, 1.2]) == 0

    def test_median_performer(self):
        """Median RS value should be around 40-60 percentile."""
        result = compute_rs_percentile(1.0, [0.8, 0.9, 1.0, 1.1, 1.2])
        assert 30 <= result <= 50  # Around middle

    def test_none_ticker(self):
        """None ticker RS returns None."""
        assert compute_rs_percentile(None, [1.0, 1.1]) is None

    def test_empty_list(self):
        """Empty RS values list returns None."""
        assert compute_rs_percentile(1.0, []) is None

    def test_single_value(self):
        """Single comparison value."""
        assert compute_rs_percentile(1.5, [1.0]) == 100
        assert compute_rs_percentile(0.5, [1.0]) == 0

    def test_equal_values(self):
        """All equal values should return appropriate percentile."""
        result = compute_rs_percentile(1.0, [1.0, 1.0, 1.0])
        assert result == 0  # None below, so 0/3 * 100 = 0

    def test_none_in_list(self):
        """None values in list should be filtered out."""
        result = compute_rs_percentile(1.0, [0.8, None, 0.9, None, 1.2])
        # Valid values: [0.8, 0.9, 1.2]
        # Values below 1.0: 2 (0.8, 0.9)
        assert result == round(2 / 3 * 100)

    def test_exact_percentile_calculation(self):
        """Verify exact percentile calculation."""
        values = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4]
        # Testing 0.85: 4 values below (0.5, 0.6, 0.7, 0.8)
        result = compute_rs_percentile(0.85, values)
        assert result == 40  # 4/10 * 100 = 40


class TestComputeSectorRotation:
    """Test compute_sector_rotation function."""

    def test_four_quadrants(self):
        """Test all four quadrants are correctly assigned."""
        sectors = [
            {"sector": "IT", "avg_rs_20d": 1.2, "avg_rs_change": 0.1, "stock_count": 50},
            {"sector": "Finance", "avg_rs_20d": 1.1, "avg_rs_change": -0.05, "stock_count": 30},
            {"sector": "Energy", "avg_rs_20d": 0.8, "avg_rs_change": -0.1, "stock_count": 20},
            {"sector": "Healthcare", "avg_rs_20d": 0.9, "avg_rs_change": 0.05, "stock_count": 25},
        ]
        result = compute_sector_rotation(sectors)
        assert len(result) == 4
        quadrants = {r["sector"]: r["quadrant"] for r in result}
        assert quadrants["IT"] == "leading"
        assert quadrants["Finance"] == "weakening"
        assert quadrants["Energy"] == "lagging"
        assert quadrants["Healthcare"] == "improving"

    def test_empty_input(self):
        """Empty input returns empty list."""
        assert compute_sector_rotation([]) == []

    def test_none_values(self):
        """None values should get neutral quadrant."""
        sectors = [
            {"sector": "IT", "avg_rs_20d": None, "avg_rs_change": None, "stock_count": 10},
            {"sector": "Finance", "avg_rs_20d": 1.0, "avg_rs_change": 0.05, "stock_count": 20},
        ]
        result = compute_sector_rotation(sectors)
        # None values should get "neutral" quadrant
        it_result = next(r for r in result if r["sector"] == "IT")
        assert it_result["quadrant"] == "neutral"

    def test_single_sector(self):
        """Single sector gets quadrant based on median (itself)."""
        sectors = [
            {"sector": "IT", "avg_rs_20d": 1.0, "avg_rs_change": 0.05, "stock_count": 10},
        ]
        result = compute_sector_rotation(sectors)
        # Median is itself, so >= median for both -> leading
        assert result[0]["quadrant"] == "leading"

    def test_all_none_values(self):
        """All None values should return neutral for all."""
        sectors = [
            {"sector": "IT", "avg_rs_20d": None, "avg_rs_change": None, "stock_count": 10},
            {"sector": "Finance", "avg_rs_20d": None, "avg_rs_change": None, "stock_count": 20},
        ]
        result = compute_sector_rotation(sectors)
        assert all(r["quadrant"] == "neutral" for r in result)

    def test_median_calculation(self):
        """Verify median is used as boundary."""
        sectors = [
            {"sector": "A", "avg_rs_20d": 0.8, "avg_rs_change": 0.02},
            {"sector": "B", "avg_rs_20d": 1.0, "avg_rs_change": 0.05},
            {"sector": "C", "avg_rs_20d": 1.2, "avg_rs_change": 0.08},
        ]
        result = compute_sector_rotation(sectors)
        # Median RS: 1.0, Median change: 0.05
        quadrants = {r["sector"]: r["quadrant"] for r in result}
        assert quadrants["A"] == "lagging"  # < median RS, < median change
        assert quadrants["B"] == "leading"  # >= median RS, >= median change
        assert quadrants["C"] == "leading"  # >= median RS, >= median change

    def test_original_data_preserved(self):
        """Original sector data should be preserved in output."""
        sectors = [
            {
                "sector": "IT",
                "avg_rs_20d": 1.2,
                "avg_rs_change": 0.1,
                "stock_count": 50,
                "extra": "data",
            },
        ]
        result = compute_sector_rotation(sectors)
        assert result[0]["sector"] == "IT"
        assert result[0]["stock_count"] == 50
        assert result[0]["extra"] == "data"
        assert "quadrant" in result[0]


class TestComputeSectorRanking:
    """Test compute_sector_ranking function."""

    def test_basic_ranking(self):
        """Test basic sector ranking by performance."""
        sector_data = {
            "IT": [
                {"ticker": "005930", "name": "Samsung", "prices": [50000, 55000, 60000]},
                {"ticker": "000660", "name": "SK Hynix", "prices": [100000, 105000, 110000]},
            ],
            "Finance": [
                {"ticker": "105560", "name": "KB Financial", "prices": [50000, 49000, 48000]},
            ],
        }
        index_prices = [2500, 2600, 2700]
        result = compute_sector_ranking(sector_data, index_prices)
        assert len(result) == 2
        # IT should rank higher (positive change)
        assert result[0]["sector"] == "IT"
        assert result[0]["momentum_rank"] == 1
        assert result[1]["momentum_rank"] == 2

    def test_empty_data(self):
        """Empty data returns empty list."""
        assert compute_sector_ranking({}, [2500, 2600]) == []
        assert compute_sector_ranking({"IT": []}, [2500, 2600]) == []

    def test_stock_count(self):
        """Verify stock count is correct."""
        sector_data = {
            "IT": [
                {"ticker": "A", "prices": [100, 110]},
                {"ticker": "B", "prices": [200, 220]},
                {"ticker": "C", "prices": [300, 330]},
            ],
        }
        result = compute_sector_ranking(sector_data, [1000, 1100])
        assert result[0]["stock_count"] == 3

    def test_avg_change_rate_calculation(self):
        """Verify average change rate is calculated correctly."""
        sector_data = {
            "IT": [
                {"ticker": "A", "prices": [100, 110]},  # +10%
                {"ticker": "B", "prices": [100, 120]},  # +20%
            ],
        }
        result = compute_sector_ranking(sector_data, [1000, 1100])
        # Average: (10 + 20) / 2 = 15%
        assert result[0]["avg_change_rate"] == 15.0

    def test_no_index_prices(self):
        """No index prices returns empty list."""
        sector_data = {"IT": [{"ticker": "A", "prices": [100, 110]}]}
        assert compute_sector_ranking(sector_data, []) == []

    def test_insufficient_price_data(self):
        """Stocks with insufficient price data are skipped."""
        sector_data = {
            "IT": [
                {"ticker": "A", "prices": [100]},  # Only 1 price
                {"ticker": "B", "prices": []},  # No prices
            ],
        }
        result = compute_sector_ranking(sector_data, [1000, 1100])
        assert result == []  # No valid stocks

    def test_mixed_valid_invalid_stocks(self):
        """Mix of valid and invalid stocks - only valid counted."""
        sector_data = {
            "IT": [
                {"ticker": "A", "prices": [100, 110]},  # Valid: +10%
                {"ticker": "B", "prices": [100]},  # Invalid: only 1 price
                {"ticker": "C", "prices": [200, 240]},  # Valid: +20%
            ],
        }
        result = compute_sector_ranking(sector_data, [1000, 1100])
        assert result[0]["stock_count"] == 3  # Total count
        # But avg_change_rate should only use valid ones
        assert result[0]["avg_change_rate"] == 15.0  # (10 + 20) / 2

    def test_ranking_order(self):
        """Sectors should be ranked by avg_change_rate descending."""
        sector_data = {
            "IT": [{"ticker": "A", "prices": [100, 120]}],  # +20%
            "Finance": [{"ticker": "B", "prices": [100, 105]}],  # +5%
            "Energy": [{"ticker": "C", "prices": [100, 115]}],  # +15%
        }
        result = compute_sector_ranking(sector_data, [1000, 1100])
        assert result[0]["sector"] == "IT"
        assert result[1]["sector"] == "Energy"
        assert result[2]["sector"] == "Finance"
        assert result[0]["momentum_rank"] == 1
        assert result[1]["momentum_rank"] == 2
        assert result[2]["momentum_rank"] == 3

    def test_top_performer(self):
        """Top performer is identified correctly."""
        sector_data = {
            "IT": [
                {"ticker": "A", "name": "Stock A", "prices": [100, 110]},  # +10%
                {"ticker": "B", "name": "Stock B", "prices": [100, 130]},  # +30%
                {"ticker": "C", "name": "Stock C", "prices": [100, 115]},  # +15%
            ],
        }
        result = compute_sector_ranking(sector_data, [1000, 1100])
        top = result[0]["top_performer"]
        assert top["ticker"] == "B"
        assert top["name"] == "Stock B"
        assert top["change_rate"] == 30.0

    def test_rs_calculation(self):
        """Verify RS is calculated using compute_relative_strength."""
        sector_data = {
            "IT": [
                {"ticker": "A", "prices": [100, 120]},  # +20%
            ],
        }
        index_prices = [1000, 1100]  # +10%
        result = compute_sector_ranking(sector_data, index_prices)
        # RS should be > 1.0 since stock outperformed index
        assert result[0]["avg_rs"] is not None
        assert result[0]["avg_rs"] > 1.0

    def test_median_change_rate(self):
        """Verify median change rate is calculated."""
        sector_data = {
            "IT": [
                {"ticker": "A", "prices": [100, 110]},  # +10%
                {"ticker": "B", "prices": [100, 130]},  # +30%
                {"ticker": "C", "prices": [100, 115]},  # +15%
            ],
        }
        result = compute_sector_ranking(sector_data, [1000, 1100])
        # Median of [10, 30, 15] = 15
        assert result[0]["median_change_rate"] == 15.0

    def test_zero_base_price(self):
        """Zero base price should result in 0 change rate."""
        sector_data = {
            "IT": [
                {"ticker": "A", "prices": [0, 100]},  # 0 base
                {"ticker": "B", "prices": [100, 110]},  # +10%
            ],
        }
        result = compute_sector_ranking(sector_data, [1000, 1100])
        # Average: (0 + 10) / 2 = 5%
        assert result[0]["avg_change_rate"] == 5.0
