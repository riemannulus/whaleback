"""Unit tests for whaleback.analysis.quant module."""

from whaleback.analysis.quant import (
    compute_rim,
    compute_safety_margin,
    compute_fscore,
    compute_investment_grade,
)


class TestComputeRIM:
    """Test compute_rim function."""

    def test_basic_value_creation(self):
        """ROE > required return should create value (rim_value > BPS)."""
        # BPS=50000, ROE=15% > 10% required return
        result = compute_rim(bps=50000, roe=15.0)
        assert result["computable"] is True
        assert result["rim_value"] > 50000, "Value creation: rim_value should exceed BPS"
        assert result["inputs"]["bps"] == 50000
        assert result["inputs"]["roe_pct"] == 15.0
        assert result["inputs"]["required_return"] == 0.10

    def test_basic_value_destruction(self):
        """ROE < required return should destroy value (rim_value < BPS)."""
        # ROE=5% < 10% required return
        result = compute_rim(bps=50000, roe=5.0)
        assert result["computable"] is True
        assert result["rim_value"] < 50000, "Value destruction: rim_value should be below BPS"

    def test_none_bps(self):
        """None BPS should return non-computable."""
        result = compute_rim(bps=None, roe=15.0)
        assert result["computable"] is False
        assert result["rim_value"] is None
        assert result["reason"] == "missing_data"

    def test_none_roe(self):
        """None ROE should return non-computable."""
        result = compute_rim(bps=50000, roe=None)
        assert result["computable"] is False
        assert result["rim_value"] is None
        assert result["reason"] == "missing_data"

    def test_negative_bps(self):
        """Negative BPS should return non-computable."""
        result = compute_rim(bps=-1000, roe=15.0)
        assert result["computable"] is False
        assert result["rim_value"] is None
        assert result["reason"] == "negative_bps"

    def test_zero_bps(self):
        """Zero BPS should return non-computable."""
        result = compute_rim(bps=0, roe=15.0)
        assert result["computable"] is False
        assert result["reason"] == "negative_bps"

    def test_degenerate_denominator(self):
        """When required_return == growth_rate, should handle gracefully."""
        # required_return = 0.05 + 0.05 = 0.10
        # growth_rate = 0.10 → denominator = 0
        result = compute_rim(
            bps=50000,
            roe=15.0,
            risk_free_rate=0.05,
            equity_risk_premium=0.05,
            growth_rate=0.1,
        )
        assert result["computable"] is True
        assert result["rim_value"] is not None
        # High ROE case: should cap at BPS * 10
        assert result["rim_value"] == 50000 * 10

    def test_degenerate_denominator_low_roe(self):
        """When denominator is zero and ROE <= required_return."""
        result = compute_rim(
            bps=50000,
            roe=8.0,  # 8% < 10% required
            risk_free_rate=0.05,
            equity_risk_premium=0.05,
            growth_rate=0.1,
        )
        assert result["computable"] is True
        # Low ROE case: fallback to BPS
        assert result["rim_value"] == 50000

    def test_rim_value_non_negative(self):
        """Even with terrible ROE, rim_value should be non-negative."""
        result = compute_rim(bps=1000, roe=-50.0)
        assert result["computable"] is True
        assert result["rim_value"] >= 0

    def test_custom_rates(self):
        """Custom risk-free rate and equity risk premium should be reflected."""
        result = compute_rim(
            bps=50000,
            roe=20.0,
            risk_free_rate=0.04,
            equity_risk_premium=0.06,
        )
        assert result["computable"] is True
        assert result["inputs"]["required_return"] == 0.10
        assert result["rim_value"] > 50000

    def test_rim_value_rounding(self):
        """RIM value should be rounded to 2 decimal places."""
        result = compute_rim(bps=50000, roe=15.0)
        assert isinstance(result["rim_value"], float)
        # Check that it's rounded (no more than 2 decimal places)
        assert round(result["rim_value"], 2) == result["rim_value"]


class TestComputeSafetyMargin:
    """Test compute_safety_margin function."""

    def test_undervalued(self):
        """Positive margin indicates undervaluation."""
        result = compute_safety_margin(rim_value=100000, current_price=70000)
        assert result["safety_margin_pct"] == 30.0
        assert result["is_undervalued"] is True

    def test_overvalued(self):
        """Negative margin indicates overvaluation."""
        result = compute_safety_margin(rim_value=50000, current_price=70000)
        assert result["safety_margin_pct"] < 0
        assert result["is_undervalued"] is False

    def test_fair_value(self):
        """Zero margin at fair value."""
        result = compute_safety_margin(rim_value=50000, current_price=50000)
        assert result["safety_margin_pct"] == 0.0
        assert result["is_undervalued"] is False

    def test_none_rim_value(self):
        """None rim_value should return None margin."""
        result = compute_safety_margin(rim_value=None, current_price=50000)
        assert result["safety_margin_pct"] is None
        assert result["is_undervalued"] is None

    def test_none_current_price(self):
        """None current_price should return None margin."""
        result = compute_safety_margin(rim_value=50000, current_price=None)
        assert result["safety_margin_pct"] is None
        assert result["is_undervalued"] is None

    def test_zero_rim_value(self):
        """Zero rim_value should return None margin."""
        result = compute_safety_margin(rim_value=0, current_price=50000)
        assert result["safety_margin_pct"] is None

    def test_negative_rim_value(self):
        """Negative rim_value should return None margin."""
        result = compute_safety_margin(rim_value=-10000, current_price=50000)
        assert result["safety_margin_pct"] is None

    def test_zero_current_price(self):
        """Zero current_price should return None margin."""
        result = compute_safety_margin(rim_value=50000, current_price=0)
        assert result["safety_margin_pct"] is None

    def test_negative_current_price(self):
        """Negative current_price should return None margin."""
        result = compute_safety_margin(rim_value=50000, current_price=-1000)
        assert result["safety_margin_pct"] is None

    def test_margin_rounding(self):
        """Safety margin should be rounded to 2 decimal places."""
        result = compute_safety_margin(rim_value=100000, current_price=67890)
        assert isinstance(result["safety_margin_pct"], float)
        assert round(result["safety_margin_pct"], 2) == result["safety_margin_pct"]


class TestComputeFScore:
    """Test compute_fscore function."""

    def test_perfect_score(self):
        """All signals positive should yield score of 9."""
        current = {
            "eps": 5000,
            "roe": 15.0,
            "bps": 60000,
            "pbr": 0.5,
            "per": 8.0,
            "div": 2.5,
        }
        previous = {
            "eps": 3000,
            "roe": 10.0,
            "bps": 50000,
        }
        medians = {
            "median_pbr": 1.0,
            "median_per": 15.0,
        }
        result = compute_fscore(
            current, previous, medians, volume_current=1000000, volume_previous=800000
        )
        assert result["total_score"] == 9
        assert result["max_score"] == 9
        assert result["data_completeness"] == 1.0
        assert len(result["criteria"]) == 9

    def test_zero_score(self):
        """All signals negative should yield score of 0."""
        current = {
            "eps": -100,
            "roe": -5.0,
            "bps": 40000,
            "pbr": 3.0,
            "per": 30.0,
            "div": 0,
        }
        previous = {
            "eps": 100,
            "roe": 5.0,
            "bps": 50000,
        }
        medians = {
            "median_pbr": 1.0,
            "median_per": 15.0,
        }
        result = compute_fscore(
            current, previous, medians, volume_current=500000, volume_previous=1000000
        )
        assert result["total_score"] == 0
        assert len(result["criteria"]) == 9

    def test_none_current(self):
        """None current should return zero score."""
        result = compute_fscore(current=None, previous=None)
        assert result["total_score"] == 0
        assert result["data_completeness"] == 0.0
        assert result["criteria"] == []

    def test_partial_data_no_previous(self):
        """Partial current data with no previous should compute available signals."""
        current = {"eps": 5000, "roe": 15.0}
        result = compute_fscore(current, previous=None)
        assert 0 < result["data_completeness"] < 1.0
        assert len(result["criteria"]) == 9
        # Should have exactly 2 computable signals: eps > 0, roe > 0
        assert result["data_completeness"] == round(2 / 9, 2)

    def test_partial_data_no_sector(self):
        """No sector medians should mark those signals as non-computable."""
        current = {"eps": 5000, "roe": 15.0, "pbr": 0.5, "per": 8.0}
        result = compute_fscore(current, previous=None, sector_medians=None)
        assert len(result["criteria"]) == 9
        # PBR and PER sector comparisons should have note="섹터 데이터 없음"
        pbr_criterion = next(c for c in result["criteria"] if c["name"] == "pbr_below_sector")
        assert pbr_criterion["score"] == 0
        assert "섹터 데이터 없음" in pbr_criterion.get("note", "")

    def test_criteria_count_always_nine(self):
        """Criteria list should always have 9 entries."""
        current = {"eps": 1000}
        result = compute_fscore(current, previous=None)
        assert len(result["criteria"]) == 9

    def test_criteria_structure(self):
        """Each criterion should have required fields."""
        current = {"eps": 5000, "roe": 15.0}
        result = compute_fscore(current, previous=None)
        for criterion in result["criteria"]:
            assert "name" in criterion
            assert "score" in criterion
            assert "label" in criterion
            assert criterion["score"] in [0, 1]

    def test_negative_pbr_excluded(self):
        """Negative PBR should not score positively."""
        current = {"pbr": -0.5}
        medians = {"median_pbr": 1.0}
        result = compute_fscore(current, previous=None, sector_medians=medians)
        pbr_criterion = next(c for c in result["criteria"] if c["name"] == "pbr_below_sector")
        assert pbr_criterion["score"] == 0

    def test_negative_per_excluded(self):
        """Negative PER should not score positively."""
        current = {"per": -10.0}
        medians = {"median_per": 15.0}
        result = compute_fscore(current, previous=None, sector_medians=medians)
        per_criterion = next(c for c in result["criteria"] if c["name"] == "per_below_sector")
        assert per_criterion["score"] == 0

    def test_zero_previous_volume(self):
        """Zero previous volume should mark volume signal as non-computable."""
        current = {"eps": 5000}
        result = compute_fscore(current, previous=None, volume_current=1000000, volume_previous=0)
        vol_criterion = next(c for c in result["criteria"] if c["name"] == "volume_increasing")
        assert vol_criterion["score"] == 0


class TestComputeInvestmentGrade:
    """Test compute_investment_grade function."""

    def test_grade_a_plus(self):
        """F-Score >= 8, margin >= 30% should yield A+."""
        result = compute_investment_grade(fscore=8, safety_margin_pct=35.0, data_completeness=0.9)
        assert result["grade"] == "A+"
        assert "label" in result
        assert "description" in result

    def test_grade_a(self):
        """F-Score >= 7, margin >= 20% should yield A."""
        result = compute_investment_grade(fscore=7, safety_margin_pct=25.0, data_completeness=0.8)
        assert result["grade"] == "A"

    def test_grade_b_plus(self):
        """F-Score >= 6, margin >= 10% should yield B+."""
        result = compute_investment_grade(fscore=6, safety_margin_pct=15.0, data_completeness=0.7)
        assert result["grade"] == "B+"

    def test_grade_b(self):
        """F-Score >= 5, margin >= 0% should yield B."""
        result = compute_investment_grade(fscore=5, safety_margin_pct=5.0, data_completeness=0.7)
        assert result["grade"] == "B"

    def test_grade_c_plus(self):
        """F-Score >= 4 with negative margin should yield C+."""
        result = compute_investment_grade(fscore=4, safety_margin_pct=-10.0, data_completeness=0.6)
        assert result["grade"] == "C+"

    def test_grade_c(self):
        """F-Score >= 3 should yield C."""
        result = compute_investment_grade(fscore=3, safety_margin_pct=-20.0, data_completeness=0.6)
        assert result["grade"] == "C"

    def test_grade_d(self):
        """F-Score < 3 should yield D."""
        result = compute_investment_grade(fscore=2, safety_margin_pct=-50.0, data_completeness=0.6)
        assert result["grade"] == "D"

    def test_grade_f_low_completeness(self):
        """Data completeness < 0.5 should yield F regardless of score."""
        result = compute_investment_grade(fscore=9, safety_margin_pct=50.0, data_completeness=0.3)
        assert result["grade"] == "F"

    def test_none_safety_margin(self):
        """None safety margin should be treated as -999."""
        result = compute_investment_grade(fscore=8, safety_margin_pct=None, data_completeness=0.8)
        # High fscore but no positive margin → cannot be A+ or A
        assert result["grade"] in ["C+", "C", "D"]

    def test_threshold_data_completeness(self):
        """Exactly 0.5 completeness should pass."""
        result = compute_investment_grade(fscore=5, safety_margin_pct=5.0, data_completeness=0.5)
        assert result["grade"] != "F"

    def test_threshold_fscore_8_margin_30(self):
        """Exactly fscore=8, margin=30 should be A+."""
        result = compute_investment_grade(fscore=8, safety_margin_pct=30.0, data_completeness=0.9)
        assert result["grade"] == "A+"

    def test_threshold_fscore_8_margin_29(self):
        """fscore=8 but margin=29 should NOT be A+."""
        result = compute_investment_grade(fscore=8, safety_margin_pct=29.0, data_completeness=0.9)
        assert result["grade"] != "A+"

    def test_threshold_fscore_7_margin_20(self):
        """Exactly fscore=7, margin=20 should be A."""
        result = compute_investment_grade(fscore=7, safety_margin_pct=20.0, data_completeness=0.8)
        assert result["grade"] == "A"

    def test_threshold_fscore_6_margin_10(self):
        """Exactly fscore=6, margin=10 should be B+."""
        result = compute_investment_grade(fscore=6, safety_margin_pct=10.0, data_completeness=0.7)
        assert result["grade"] == "B+"

    def test_threshold_fscore_5_margin_0(self):
        """Exactly fscore=5, margin=0 should be B."""
        result = compute_investment_grade(fscore=5, safety_margin_pct=0.0, data_completeness=0.7)
        assert result["grade"] == "B"

    def test_max_fscore_zero_margin(self):
        """Perfect fscore but zero margin should be B."""
        result = compute_investment_grade(fscore=9, safety_margin_pct=0.0, data_completeness=1.0)
        assert result["grade"] == "B"

    def test_zero_fscore_high_margin(self):
        """Zero fscore even with high margin should be D."""
        result = compute_investment_grade(fscore=0, safety_margin_pct=50.0, data_completeness=0.9)
        assert result["grade"] == "D"
