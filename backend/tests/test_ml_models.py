# backend/tests/test_ml_models.py
# Unit tests for FinanceAI ML models

import pandas as pd
import numpy as np


# ============================================================
# EXPENSE PREDICTOR
# ============================================================

class TestExpensePredictor:

    def _make_monthly_df(self, num_months=6):
        values = [15000, 17000, 16000, 18000, 17500, 19000]

        return pd.DataFrame({
            "month_num": list(range(1, num_months + 1)),
            "total_expenses": values[:num_months]
        })

    def _make_expense_data(self, num_months=3):
        rows = []

        monthly_amounts = [5000, 6000, 7000]

        for month_index in range(num_months):
            month = month_index + 1

            for day in [5, 15]:
                rows.append({
                    "amount": monthly_amounts[month_index],
                    "date": f"2024-{month:02d}-{day:02d}",
                    "category_id": 1,
                    "category_name": "Food",
                    "note": "Food expense"
                })

        return rows

    def test_predictor_trains_successfully(self):
        """TC-ML-001: Predictor trains on valid monthly data."""

        from ml_models.expense_predictor import ExpensePredictor

        predictor = ExpensePredictor()

        monthly_df = self._make_monthly_df()

        result = predictor.train(monthly_df)

        assert result is True
        assert predictor.is_trained is True
        assert predictor.monthly_data is not None

    def test_predictor_returns_positive_value(self):
        """TC-ML-002: Prediction is non-negative."""

        from ml_models.expense_predictor import ExpensePredictor

        predictor = ExpensePredictor()

        monthly_df = self._make_monthly_df()

        assert predictor.train(monthly_df) is True

        result = predictor.predict()

        assert result["status"] == "success"
        assert result["predicted_amount"] >= 0

    def test_predictor_insufficient_training_data(self):
        """TC-ML-003: Predictor refuses fewer than 3 monthly rows."""

        from ml_models.expense_predictor import ExpensePredictor

        predictor = ExpensePredictor()

        df = pd.DataFrame({
            "month_num": [1, 2],
            "total_expenses": [1000, 1200]
        })

        assert predictor.train(df) is False

    def test_predictor_insufficient_raw_data(self):
        """TC-ML-004: Standalone predictor rejects insufficient monthly history."""

        from ml_models.expense_predictor import predict_next_month_expense

        result = predict_next_month_expense([
            {
                "amount": 1000,
                "date": "2024-01-01",
                "category_id": 1,
                "category_name": "Food",
                "note": ""
            }
        ])

        assert result["status"] == "insufficient_data"

    def test_predictor_includes_confidence(self):
        """TC-ML-005: Prediction contains confidence."""

        from ml_models.expense_predictor import ExpensePredictor

        predictor = ExpensePredictor()

        assert predictor.train(
            self._make_monthly_df()
        ) is True

        result = predictor.predict()

        assert "confidence" in result
        assert result["confidence"] in {
            "high",
            "medium",
            "low"
        }

    def test_predictor_includes_prediction_bounds(self):
        """TC-ML-006: Prediction contains valid lower/upper bounds."""

        from ml_models.expense_predictor import ExpensePredictor

        predictor = ExpensePredictor()

        assert predictor.train(
            self._make_monthly_df()
        ) is True

        result = predictor.predict()

        assert "lower_bound" in result
        assert "upper_bound" in result

        assert result["lower_bound"] <= result["predicted_amount"]
        assert result["upper_bound"] >= result["predicted_amount"]

    def test_predictor_metrics_present(self):
        """TC-ML-007: Linear and polynomial metrics are produced."""

        from ml_models.expense_predictor import ExpensePredictor

        predictor = ExpensePredictor()

        assert predictor.train(
            self._make_monthly_df()
        ) is True

        assert "linear" in predictor.metrics
        assert "r2" in predictor.metrics["linear"]
        assert "mae" in predictor.metrics["linear"]

        assert "polynomial" in predictor.metrics
        assert "r2" in predictor.metrics["polynomial"]
        assert "mae" in predictor.metrics["polynomial"]

    def test_predictor_prediction_contains_required_fields(self):
        """TC-ML-008: Prediction response contains expected fields."""

        from ml_models.expense_predictor import ExpensePredictor

        predictor = ExpensePredictor()

        assert predictor.train(
            self._make_monthly_df()
        ) is True

        result = predictor.predict()

        required = {
            "status",
            "predicted_amount",
            "lower_bound",
            "upper_bound",
            "trend",
            "confidence",
            "model_used",
            "r2_score",
            "months_of_data",
            "linear_prediction",
            "metrics",
            "interpretation"
        }

        assert required.issubset(result.keys())

    def test_predictor_standalone_success(self):
        """TC-ML-009: Standalone predictor succeeds with 3 months."""

        from ml_models.expense_predictor import predict_next_month_expense

        result = predict_next_month_expense(
            self._make_expense_data(3)
        )

        assert result["status"] == "success"
        assert result["predicted_amount"] >= 0


# ============================================================
# ANOMALY DETECTOR
# ============================================================

class TestAnomalyDetector:

    def _make_expense_df(self):
        amounts = [
            1500, 1200, 1800, 900,
            1600, 1100, 1400, 1300,
            1700, 1000, 1250, 1450,
            15000
        ]

        return pd.DataFrame({
            "id": list(range(len(amounts))),
            "amount": amounts,
            "date": pd.date_range(
                "2024-01-01",
                periods=len(amounts)
            ),
            "category_name": ["Food"] * len(amounts),
            "note": [""] * len(amounts)
        })

    def test_detector_handles_valid_data(self):
        """TC-ML-010: Detector processes 10+ transactions."""

        from ml_models.anomaly_detector import AnomalyDetector

        detector = AnomalyDetector()

        df = self._make_expense_df()

        result_df, anomalies = detector.fit_predict(df)

        assert len(result_df) == len(df)
        assert isinstance(anomalies, list)
        assert detector.is_fitted is True

    def test_detector_finds_large_outlier(self):
        """TC-ML-011: Obvious large transaction should be flagged."""

        from ml_models.anomaly_detector import AnomalyDetector

        detector = AnomalyDetector()

        _, anomalies = detector.fit_predict(
            self._make_expense_df()
        )

        anomaly_amounts = [
            float(item["amount"])
            for item in anomalies
        ]

        assert 15000.0 in anomaly_amounts

    def test_detector_adds_detection_columns(self):
        """TC-ML-012: Detector adds all anomaly columns."""

        from ml_models.anomaly_detector import AnomalyDetector

        detector = AnomalyDetector()

        result_df, _ = detector.fit_predict(
            self._make_expense_df()
        )

        required_columns = {
            "iso_flag",
            "zscore_flag",
            "iqr_flag",
            "anomaly_score",
            "is_anomaly"
        }

        assert required_columns.issubset(
            result_df.columns
        )

    def test_detector_consensus_rule(self):
        """TC-ML-013: Anomaly requires 2 or more methods."""

        from ml_models.anomaly_detector import AnomalyDetector

        detector = AnomalyDetector()

        result_df, _ = detector.fit_predict(
            self._make_expense_df()
        )

        for _, row in result_df.iterrows():
            expected = int(row["anomaly_score"] >= 2)

            assert int(row["is_anomaly"]) == expected

    def test_detector_uniform_data_has_no_anomalies(self):
        """TC-ML-014: Uniform values should not be anomalous."""

        from ml_models.anomaly_detector import AnomalyDetector

        df = pd.DataFrame({
            "id": list(range(20)),
            "amount": [1000.0] * 20,
            "date": pd.date_range(
                "2024-01-01",
                periods=20
            ),
            "category_name": ["Food"] * 20,
            "note": [""] * 20
        })

        detector = AnomalyDetector()

        _, anomalies = detector.fit_predict(df)

        assert len(anomalies) == 0

    def test_detector_insufficient_data(self):
        """TC-ML-015: Fewer than 10 records → no detection."""

        from ml_models.anomaly_detector import detect_anomalies

        data = [
            {
                "amount": 1000,
                "date": "2024-01-01",
                "category_id": 1,
                "category_name": "Food",
                "note": ""
            }
        ] * 5

        result = detect_anomalies(data)

        assert result["status"] == "insufficient_data"
        assert result["anomalies"] == []
        assert result["anomalies_found"] == 0

    def test_detector_standalone_success(self):
        """TC-ML-016: Standalone detector returns success."""

        from ml_models.anomaly_detector import detect_anomalies

        data = []

        amounts = [
            1500, 1200, 1800, 900,
            1600, 1100, 1400, 1300,
            1700, 1000, 1250, 1450,
            15000
        ]

        for index, amount in enumerate(amounts):

            data.append({
                "amount": amount,
                "date": f"2024-01-{index + 1:02d}",
                "category_id": 1,
                "category_name": "Food",
                "note": ""
            })

        result = detect_anomalies(data)

        assert result["status"] == "success"
        assert result["total_checked"] == 13
        assert result["methods_used"] == [
            "Isolation Forest",
            "Z-Score",
            "IQR"
        ]
        assert "thresholds" in result
        assert "consensus_rule" in result


# ============================================================
# BUDGET RECOMMENDER
# ============================================================

class TestBudgetRecommender:

    def _make_expense_df(self):

        rows = []

        monthly_amounts = {
            1: 1000,
            2: 1500,
            3: 2000
        }

        for month, base_amount in monthly_amounts.items():

            rows.append({
                "amount": base_amount,
                "date": f"2024-{month:02d}-05",
                "category_name": "Food"
            })

            rows.append({
                "amount": base_amount / 2,
                "date": f"2024-{month:02d}-15",
                "category_name": "Transport"
            })

            rows.append({
                "amount": base_amount / 4,
                "date": f"2024-{month:02d}-20",
                "category_name": "Entertainment"
            })

        df = pd.DataFrame(rows)

        df["date"] = pd.to_datetime(df["date"])
        df["month_period"] = df["date"].dt.to_period("M")

        return df

    def test_recommender_compute_success(self):
        """TC-ML-017: Budget recommender computes successfully."""

        from ml_models.budget_recommender import BudgetRecommender

        recommender = BudgetRecommender()

        result = recommender.compute(
            self._make_expense_df()
        )

        assert result is True
        assert recommender.is_computed is True

    def test_recommender_returns_success(self):
        """TC-ML-018: Recommender result has success status."""

        from ml_models.budget_recommender import BudgetRecommender

        recommender = BudgetRecommender()

        recommender.compute(
            self._make_expense_df()
        )

        result = recommender.get_results()

        assert result["status"] == "success"
        assert "overall" in result
        assert "category_recommendations" in result

    def test_recommender_overall_positive(self):
        """TC-ML-019: Overall recommendation is positive."""

        from ml_models.budget_recommender import BudgetRecommender

        recommender = BudgetRecommender()

        recommender.compute(
            self._make_expense_df()
        )

        result = recommender.get_results()

        assert (
            result["overall"]["recommended_overall"]
            > 0
        )

    def test_recommender_category_recommendations_exist(self):
        """TC-ML-020: Category recommendations are generated."""

        from ml_models.budget_recommender import BudgetRecommender

        recommender = BudgetRecommender()

        recommender.compute(
            self._make_expense_df()
        )

        result = recommender.get_results()

        recommendations = result[
            "category_recommendations"
        ]

        assert isinstance(
            recommendations,
            list
        )

        assert len(recommendations) >= 3

    def test_recommender_category_fields(self):
        """TC-ML-021: Category recommendations contain required fields."""

        from ml_models.budget_recommender import BudgetRecommender

        recommender = BudgetRecommender()

        recommender.compute(
            self._make_expense_df()
        )

        result = recommender.get_results()

        for item in result[
            "category_recommendations"
        ]:

            assert "category_name" in item
            assert "average_spending" in item
            assert "median_spending" in item
            assert "p75_spending" in item
            assert "max_spending" in item
            assert "recommended_budget" in item
            assert "months_active" in item
            assert "basis" in item

            assert (
                item["recommended_budget"] > 0
            )

    def test_recommender_insufficient_data(self):
        """TC-ML-022: Standalone recommender rejects too little data."""

        from ml_models.budget_recommender import recommend_budget

        result = recommend_budget([
            {
                "amount": 1000,
                "date": "2024-01-01",
                "category_name": "Food"
            }
        ])

        assert result["status"] == "insufficient_data"


# ============================================================
# CATEGORY SUGGESTER
# ============================================================

class TestCategorySuggester:

    def test_suggest_food_category(self):
        """TC-ML-023: Restaurant lunch → Food."""

        from ml_models.category_suggester import CategorySuggester

        suggester = CategorySuggester()

        result = suggester.suggest(
            "lunch at restaurant"
        )

        assert result["suggested"] == "Food"
        assert result["confidence"] > 0

    def test_suggest_transport_category(self):
        """TC-ML-024: Uber → Transport."""

        from ml_models.category_suggester import CategorySuggester

        suggester = CategorySuggester()

        result = suggester.suggest(
            "uber to office"
        )

        assert result["suggested"] == "Transport"

    def test_suggest_utilities_category(self):
        """TC-ML-025: Electricity bill → Utilities."""

        from ml_models.category_suggester import CategorySuggester

        suggester = CategorySuggester()

        result = suggester.suggest(
            "electricity bill payment"
        )

        assert result["suggested"] == "Utilities"

    def test_suggest_shopping_category(self):
        """TC-ML-026: Amazon clothes purchase → Shopping."""

        from ml_models.category_suggester import CategorySuggester

        suggester = CategorySuggester()

        result = suggester.suggest(
            "bought clothes from amazon"
        )

        assert result["suggested"] == "Shopping"

    def test_suggest_healthcare_category(self):
        """TC-ML-027: Pharmacy medicine → Healthcare."""

        from ml_models.category_suggester import CategorySuggester

        suggester = CategorySuggester()

        result = suggester.suggest(
            "medicine from pharmacy"
        )

        assert result["suggested"] == "Healthcare"

    def test_suggest_empty_note(self):
        """TC-ML-028: Empty note → no suggestion."""

        from ml_models.category_suggester import CategorySuggester

        suggester = CategorySuggester()

        result = suggester.suggest("")

        assert result["suggested"] is None
        assert result["confidence"] == 0
        assert result["method"] == "no_input"
        assert result["alternatives"] == []

    def test_suggest_unknown_note(self):
        """TC-ML-029: Unknown description → Other Expense fallback."""

        from ml_models.category_suggester import CategorySuggester

        suggester = CategorySuggester()

        result = suggester.suggest(
            "random unrelated xyz"
        )

        assert result["suggested"] == "Other Expense"
        assert result["confidence"] == 10
        assert result["method"] == "default"

    def test_suggest_with_alternatives(self):
        """TC-ML-030: Suggestion response contains alternatives."""

        from ml_models.category_suggester import CategorySuggester

        suggester = CategorySuggester()

        result = suggester.suggest(
            "grocery shopping at supermarket"
        )

        assert "alternatives" in result
        assert isinstance(
            result["alternatives"],
            list
        )

    def test_suggest_confidence_range(self):
        """TC-ML-031: Confidence is between 0 and 100."""

        from ml_models.category_suggester import CategorySuggester

        suggester = CategorySuggester()

        result = suggester.suggest(
            "monthly rent payment"
        )

        assert (
            0 <= result["confidence"] <= 100
        )

    def test_suggest_available_categories_filter(self):
        """TC-ML-032: Available category list is respected."""

        from ml_models.category_suggester import CategorySuggester

        suggester = CategorySuggester()

        result = suggester.suggest(
            "lunch at restaurant",
            available_categories=[
                "Transport",
                "Other Expense"
            ]
        )

        assert result["suggested"] in {
            "Transport",
            "Other Expense"
        }

    def test_suggest_standalone_function(self):
        """TC-ML-033: Standalone category suggestion works."""

        from ml_models.category_suggester import suggest_category

        result = suggest_category(
            "electricity bill"
        )

        assert result["suggested"] == "Utilities"
        assert result["confidence"] > 0


# ============================================================
# FINANCIAL HEALTH SCORER
# ============================================================

class TestFinancialHealthScorer:

    def _make_dataframes(self):

        expense_dates = pd.to_datetime([
            "2024-01-05",
            "2024-01-10",
            "2024-01-20",
            "2024-02-05",
            "2024-02-10",
            "2024-02-20",
            "2024-03-05",
            "2024-03-10",
            "2024-03-20"
        ])

        expense_df = pd.DataFrame({
            "amount": [
                3000,
                2000,
                2500,
                3000,
                2000,
                2500,
                3000,
                2000,
                2500
            ],
            "date": expense_dates,
            "category_name": [
                "Food",
                "Transport",
                "Rent",
                "Food",
                "Transport",
                "Rent",
                "Food",
                "Transport",
                "Rent"
            ],
            "category_id": [
                1, 2, 3,
                1, 2, 3,
                1, 2, 3
            ]
        })

        expense_df["month_period"] = (
            expense_df["date"].dt.to_period("M")
        )

        income_df = pd.DataFrame({
            "amount": [
                25000,
                25000,
                25000
            ],
            "date": pd.to_datetime([
                "2024-01-01",
                "2024-02-01",
                "2024-03-01"
            ]),
            "category_name": [
                "Salary",
                "Salary",
                "Salary"
            ]
        })

        income_df["month_period"] = (
            income_df["date"].dt.to_period("M")
        )

        return expense_df, income_df

    def test_scorer_returns_valid_score(self):
        """TC-ML-034: Health score is between 0 and 100."""

        from ml_models.financial_health_scorer import FinancialHealthScorer

        expense_df, income_df = self._make_dataframes()

        scorer = FinancialHealthScorer()

        scorer.compute(
            expense_df,
            income_df
        )

        result = scorer.get_results()

        assert 0 <= result["total_score"] <= 100

    def test_scorer_returns_valid_grade(self):
        """TC-ML-035: Health grade is valid."""

        from ml_models.financial_health_scorer import FinancialHealthScorer

        expense_df, income_df = self._make_dataframes()

        scorer = FinancialHealthScorer()

        scorer.compute(
            expense_df,
            income_df
        )

        result = scorer.get_results()

        assert result["grade"] in {
            "A+",
            "A",
            "B",
            "C",
            "D",
            "F"
        }

    def test_scorer_has_breakdown(self):
        """TC-ML-036: Score breakdown contains all components."""

        from ml_models.financial_health_scorer import FinancialHealthScorer

        expense_df, income_df = self._make_dataframes()

        scorer = FinancialHealthScorer()

        scorer.compute(
            expense_df,
            income_df
        )

        result = scorer.get_results()

        assert isinstance(
            result["breakdown"],
            list
        )

        assert len(result["breakdown"]) >= 5

    def test_scorer_has_six_component_scores(self):
        """TC-ML-037: Six score components are available."""

        from ml_models.financial_health_scorer import FinancialHealthScorer

        expense_df, income_df = self._make_dataframes()

        scorer = FinancialHealthScorer()

        scorer.compute(
            expense_df,
            income_df
        )

        result = scorer.get_results()

        component_scores = result[
            "component_scores"
        ]

        expected_components = {
            "savings_rate",
            "consistency",
            "diversity",
            "goals",
            "income_stability",
            "budget_adherence"
        }

        assert expected_components.issubset(
            component_scores.keys()
        )

    def test_scorer_has_insights(self):
        """TC-ML-038: Scorer generates insights."""

        from ml_models.financial_health_scorer import FinancialHealthScorer

        expense_df, income_df = self._make_dataframes()

        scorer = FinancialHealthScorer()

        scorer.compute(
            expense_df,
            income_df
        )

        result = scorer.get_results()

        assert isinstance(
            result["insights"],
            list
        )

        assert len(result["insights"]) > 0

    def test_scorer_no_income_data(self):
        """TC-ML-039: Scorer handles missing income safely."""

        from ml_models.financial_health_scorer import FinancialHealthScorer

        expense_df, _ = self._make_dataframes()

        scorer = FinancialHealthScorer()

        scorer.compute(
            expense_df,
            None
        )

        result = scorer.get_results()

        assert 0 <= result["total_score"] <= 100
        assert result["grade"] in {
            "A+",
            "A",
            "B",
            "C",
            "D",
            "F"
        }

    def test_scorer_handles_empty_expenses(self):
        """TC-ML-040: Empty expense DataFrame is handled."""

        from ml_models.financial_health_scorer import FinancialHealthScorer

        expense_df = pd.DataFrame()

        income_df = pd.DataFrame({
            "amount": [25000],
            "date": pd.to_datetime([
                "2024-01-01"
            ]),
            "category_name": ["Salary"],
            "month_period": pd.PeriodIndex(
                ["2024-01"],
                freq="M"
            )
        })

        scorer = FinancialHealthScorer()

        scorer.compute(
            expense_df,
            income_df
        )

        result = scorer.get_results()

        assert 0 <= result["total_score"] <= 100

    def test_scorer_score_breakdown_values_are_valid(self):
        """TC-ML-041: Every breakdown score stays within its max."""

        from ml_models.financial_health_scorer import FinancialHealthScorer

        expense_df, income_df = self._make_dataframes()

        scorer = FinancialHealthScorer()

        scorer.compute(
            expense_df,
            income_df
        )

        result = scorer.get_results()

        for item in result["breakdown"]:

            if "score" in item:
                assert item["score"] >= 0

            if "max_score" in item:
                assert item["max_score"] > 0

            if (
                "score" in item
                and "max_score" in item
            ):
                assert (
                    item["score"]
                    <= item["max_score"]
                )


# ============================================================
# PATTERN DETECTOR
# ============================================================

class TestPatternDetector:

    def _make_pattern_df(self):

        rows = []

        monthly_values = {
            1: [1000, 1200, 1100, 1300],
            2: [1500, 1600, 1550, 1650],
            3: [2000, 2100, 2050, 2150]
        }

        for month, values in monthly_values.items():

            for index, amount in enumerate(
                values,
                start=1
            ):

                rows.append({
                    "amount": amount,
                    "date": f"2024-{month:02d}-{index * 5:02d}",
                    "category_name": "Food",
                    "category_id": 1
                })

        df = pd.DataFrame(rows)

        df["date"] = pd.to_datetime(df["date"])
        df["month_period"] = (
            df["date"].dt.to_period("M")
        )
        df["day_of_week"] = (
            df["date"].dt.dayofweek
        )
        df["is_weekend"] = (
            df["day_of_week"] >= 5
        ).astype(int)

        return df

    def test_pattern_detector_insufficient_data(self):
        """TC-ML-042: Fewer than 10 transactions → insufficient data."""

        from ml_models.pattern_detector import PatternDetector

        detector = PatternDetector()

        df = self._make_pattern_df().head(5)

        result = detector.analyze(df)

        assert result["status"] == "insufficient_data"

    def test_pattern_detector_success(self):
        """TC-ML-043: Pattern detector succeeds with enough data."""

        from ml_models.pattern_detector import PatternDetector

        detector = PatternDetector()

        df = self._make_pattern_df()

        result = detector.analyze(df)

        assert result["status"] == "success"
        assert result["total_analyzed"] == len(df)

    def test_pattern_detector_result_structure(self):
        """TC-ML-044: Pattern detector returns all expected sections."""

        from ml_models.pattern_detector import PatternDetector

        detector = PatternDetector()

        result = detector.analyze(
            self._make_pattern_df()
        )

        assert "patterns" in result
        assert "tips" in result
        assert "warnings" in result
        assert "positives" in result

        assert isinstance(
            result["patterns"],
            list
        )

        assert isinstance(
            result["tips"],
            list
        )

        assert isinstance(
            result["warnings"],
            list
        )

        assert isinstance(
            result["positives"],
            list
        )