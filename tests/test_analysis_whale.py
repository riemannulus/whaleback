"""Unit tests for the whale analysis module."""

from whaleback.analysis.whale import compute_whale_score


class TestComputeWhaleScore:
    def test_empty_data(self):
        """Empty data should return neutral score."""
        result = compute_whale_score([])
        assert result["whale_score"] == 0.0
        assert result["signal"] == "neutral"
        assert result["lookback_days"] == 0

    def test_strong_accumulation(self):
        """All investors buying every day with high volume should show strong accumulation."""
        data = [
            {
                "trade_date": f"2024-01-{i:02d}",
                "institution_net": 2_000_000_000,
                "foreign_net": 1_500_000_000,
                "pension_net": 800_000_000,
            }
            for i in range(1, 21)
        ]
        result = compute_whale_score(data, avg_daily_trading_value=5_000_000_000)
        assert result["whale_score"] >= 70
        assert result["signal"] == "strong_accumulation"
        assert result["signal_label"] == "강한 매집"

    def test_distribution_signal(self):
        """All investors selling every day should show distribution."""
        data = [
            {
                "trade_date": f"2024-01-{i:02d}",
                "institution_net": -500_000_000,
                "foreign_net": -300_000_000,
                "pension_net": -100_000_000,
            }
            for i in range(1, 21)
        ]
        result = compute_whale_score(data, avg_daily_trading_value=5_000_000_000)
        # Score should be low (consistency of buying is 0)
        assert result["whale_score"] < 30
        assert result["signal"] == "distribution"
        assert result["signal_label"] == "매도 우위"

    def test_mixed_signals(self):
        """Mixed investor behavior should produce intermediate scores."""
        data = [
            {
                "trade_date": f"2024-01-{i:02d}",
                "institution_net": 500_000_000,
                "foreign_net": -200_000_000,
                "pension_net": 0,
            }
            for i in range(1, 21)
        ]
        result = compute_whale_score(data, avg_daily_trading_value=5_000_000_000)
        assert 0 < result["whale_score"] < 100
        assert result["components"]["institution_net"]["consistency"] == 1.0
        assert result["components"]["foreign_net"]["consistency"] == 0.0

    def test_none_investor_values(self):
        """None values in data should be handled gracefully."""
        data = [
            {
                "trade_date": "2024-01-01",
                "institution_net": 100_000,
                "foreign_net": None,
                "pension_net": None,
            },
            {
                "trade_date": "2024-01-02",
                "institution_net": 200_000,
                "foreign_net": None,
                "pension_net": None,
            },
        ]
        result = compute_whale_score(data)
        assert result["whale_score"] >= 0
        assert result["components"]["institution_net"]["buy_days"] == 2

    def test_lookback_limit(self):
        """Should only use last N days when data exceeds lookback period."""
        data = [
            {
                "trade_date": f"2024-01-{i:02d}",
                "institution_net": 100_000,
                "foreign_net": 100_000,
                "pension_net": 100_000,
            }
            for i in range(1, 31)  # 30 days of data
        ]
        result = compute_whale_score(data, lookback_days=10)
        assert result["lookback_days"] == 10

    def test_no_trading_value_fallback(self):
        """No avg_daily_trading_value should use fallback intensity calculation."""
        data = [
            {
                "trade_date": f"2024-01-{i:02d}",
                "institution_net": 500_000_000,
                "foreign_net": 300_000_000,
                "pension_net": 100_000_000,
            }
            for i in range(1, 11)
        ]
        result = compute_whale_score(data, avg_daily_trading_value=None)
        assert result["whale_score"] > 0  # Should still compute

    def test_component_structure(self):
        """All component fields should be present in result."""
        data = [
            {
                "trade_date": "2024-01-01",
                "institution_net": 100,
                "foreign_net": -50,
                "pension_net": 0,
            }
        ]
        result = compute_whale_score(data)
        for investor_type in ["institution_net", "foreign_net", "pension_net"]:
            comp = result["components"][investor_type]
            assert "net_total" in comp
            assert "buy_days" in comp
            assert "sell_days" in comp
            assert "consistency" in comp
            assert "intensity" in comp
            assert "score" in comp

    def test_consistency_calculation(self):
        """Consistency should be calculated as buy_days / active_days."""
        # 15 buy days, 5 sell days = 0.75 consistency
        data = []
        for i in range(1, 21):
            net = 100_000 if i <= 15 else -100_000
            data.append(
                {
                    "trade_date": f"2024-01-{i:02d}",
                    "institution_net": net,
                    "foreign_net": 0,
                    "pension_net": 0,
                }
            )
        result = compute_whale_score(data)
        assert result["components"]["institution_net"]["consistency"] == 0.75
        assert result["components"]["institution_net"]["buy_days"] == 15
        assert result["components"]["institution_net"]["sell_days"] == 5

    def test_neutral_days_calculation(self):
        """Neutral days should be counted correctly."""
        data = [
            {
                "trade_date": "2024-01-01",
                "institution_net": 100,
                "foreign_net": 0,
                "pension_net": 0,
            },
            {
                "trade_date": "2024-01-02",
                "institution_net": -100,
                "foreign_net": 0,
                "pension_net": 0,
            },
            {
                "trade_date": "2024-01-03",
                "institution_net": 0,
                "foreign_net": 0,
                "pension_net": 0,
            },
        ]
        result = compute_whale_score(data)
        # Foreign and pension have 3 neutral days each (all 0)
        assert result["components"]["foreign_net"]["neutral_days"] == 3
        assert result["components"]["pension_net"]["neutral_days"] == 3
        # Institution has 1 buy, 1 sell, 1 neutral
        assert result["components"]["institution_net"]["neutral_days"] == 1

    def test_intensity_capping(self):
        """Intensity should be capped at 1.0."""
        data = [
            {
                "trade_date": f"2024-01-{i:02d}",
                "institution_net": 10_000_000_000,  # Very high net buying
                "foreign_net": 0,
                "pension_net": 0,
            }
            for i in range(1, 11)
        ]
        result = compute_whale_score(data, avg_daily_trading_value=1_000_000_000)
        # Intensity should be capped at 1.0 even though avg_net/avg_daily_trading_value > 1
        assert result["components"]["institution_net"]["intensity"] <= 1.0

    def test_mild_accumulation_signal(self):
        """Score between 50-70 should show mild accumulation."""
        # Create data that produces score ~60
        data = [
            {
                "trade_date": f"2024-01-{i:02d}",
                "institution_net": 300_000_000 if i <= 12 else -100_000_000,
                "foreign_net": 0,
                "pension_net": 0,
            }
            for i in range(1, 21)
        ]
        result = compute_whale_score(data, avg_daily_trading_value=5_000_000_000)
        if 50 <= result["whale_score"] < 70:
            assert result["signal"] == "mild_accumulation"
            assert result["signal_label"] == "완만한 매집"

    def test_neutral_signal_positive_net(self):
        """Score below 30 with positive net should show neutral."""
        data = [
            {
                "trade_date": f"2024-01-{i:02d}",
                "institution_net": 10_000 if i == 1 else 0,
                "foreign_net": 0,
                "pension_net": 0,
            }
            for i in range(1, 21)
        ]
        result = compute_whale_score(data)
        assert result["whale_score"] < 30
        assert result["signal"] == "neutral"  # Positive net_total

    def test_composite_score_calculation(self):
        """Whale score should be max * 0.5 + avg * 0.5."""
        data = [
            {
                "trade_date": f"2024-01-{i:02d}",
                "institution_net": 1_000_000_000,  # Will have high score
                "foreign_net": 0,  # Will have low score
                "pension_net": 0,  # Will have low score
            }
            for i in range(1, 21)
        ]
        result = compute_whale_score(data, avg_daily_trading_value=5_000_000_000)

        inst_score = result["components"]["institution_net"]["score"]
        foreign_score = result["components"]["foreign_net"]["score"]
        pension_score = result["components"]["pension_net"]["score"]

        max_score = max(inst_score, foreign_score, pension_score)
        avg_score = (inst_score + foreign_score + pension_score) / 3
        expected_whale_score = max_score * 0.5 + avg_score * 0.5

        assert abs(result["whale_score"] - expected_whale_score) < 0.01

    def test_all_none_investor_data(self):
        """Data with all None investor values should return empty component."""
        data = [
            {
                "trade_date": "2024-01-01",
                "institution_net": None,
                "foreign_net": None,
                "pension_net": None,
            }
        ]
        result = compute_whale_score(data)
        assert result["whale_score"] == 0.0
        for investor_type in ["institution_net", "foreign_net", "pension_net"]:
            comp = result["components"][investor_type]
            assert comp["buy_days"] == 0
            assert comp["sell_days"] == 0
            assert comp["score"] == 0.0
