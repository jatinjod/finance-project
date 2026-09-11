# backend/tests/test_performance.py
# Performance and response-time tests for FinanceAI

import time
from datetime import date, timedelta

from models.expense import Expense
from models.income import Income
from models.category import Category


# ============================================================
# RESPONSE TIME TESTS
# ============================================================

class TestResponseTimes:

    def test_login_response_under_2_seconds(
        self,
        client,
        test_user
    ):
        """TC-PERF-001: Login should complete within 2 seconds."""

        start = time.perf_counter()

        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "password123"
            }
        )

        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < 2.0, (
            f"Login took {elapsed:.2f}s; expected under 2s"
        )

    def test_dashboard_response_under_3_seconds(
        self,
        client,
        auth_headers
    ):
        """TC-PERF-002: Dashboard should load within 3 seconds."""

        start = time.perf_counter()

        response = client.get(
            "/api/dashboard/summary",
            headers=auth_headers
        )

        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < 3.0, (
            f"Dashboard took {elapsed:.2f}s; expected under 3s"
        )

    def test_expense_add_under_2_seconds(
        self,
        client,
        auth_headers,
        test_user,
        db
    ):
        """TC-PERF-003: Adding expense should complete within 2 seconds."""

        category = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert category is not None

        start = time.perf_counter()

        response = client.post(
            "/api/expenses",
            headers=auth_headers,
            json={
                "amount": 1000,
                "category_id": category.id,
                "date": str(date.today()),
                "note": "Performance test"
            }
        )

        elapsed = time.perf_counter() - start

        assert response.status_code == 201
        assert elapsed < 2.0, (
            f"Add expense took {elapsed:.2f}s; expected under 2s"
        )

        data = response.get_json()

        expense_id = data["data"]["id"]

        expense = db.session.get(
            Expense,
            expense_id
        )

        if expense:
            db.session.delete(expense)
            db.session.commit()

    def test_report_generation_under_5_seconds(
        self,
        client,
        auth_headers
    ):
        """TC-PERF-004: Monthly report should generate within 5 seconds."""

        start = time.perf_counter()

        response = client.get(
            "/api/reports/monthly?month=1&year=2024",
            headers=auth_headers
        )

        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < 5.0, (
            f"Report took {elapsed:.2f}s; expected under 5s"
        )

    def test_category_list_under_1_second(
        self,
        client,
        auth_headers
    ):
        """TC-PERF-005: Categories should load within 1 second."""

        start = time.perf_counter()

        response = client.get(
            "/api/categories",
            headers=auth_headers
        )

        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < 1.0, (
            f"Categories took {elapsed:.2f}s; expected under 1s"
        )

    def test_transactions_under_3_seconds(
        self,
        client,
        auth_headers
    ):
        """TC-PERF-006: Transactions should load within 3 seconds."""

        start = time.perf_counter()

        response = client.get(
            "/api/transactions",
            headers=auth_headers
        )

        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < 3.0, (
            f"Transactions took {elapsed:.2f}s; expected under 3s"
        )

    def test_multiple_sequential_requests(
        self,
        client,
        auth_headers
    ):
        """TC-PERF-007: 10 category requests should finish within 10 seconds."""

        start = time.perf_counter()

        for _ in range(10):

            response = client.get(
                "/api/categories",
                headers=auth_headers
            )

            assert response.status_code == 200

        elapsed = time.perf_counter() - start

        assert elapsed < 10.0, (
            f"10 requests took {elapsed:.2f}s; expected under 10s"
        )

    def test_ai_insights_under_10_seconds(
        self,
        client,
        auth_headers,
        test_user,
        db
    ):
        """TC-PERF-008: AI insights should respond within 10 seconds."""

        category = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert category is not None

        expenses = []

        try:

            for i in range(12):

                expense = Expense(
                    user_id=test_user.id,
                    category_id=category.id,
                    amount=1000 + (i * 100),
                    date=date.today() - timedelta(days=i * 10),
                    note="AI performance test"
                )

                expenses.append(expense)
                db.session.add(expense)

            db.session.commit()

            start = time.perf_counter()

            response = client.get(
                "/api/ai/insights",
                headers=auth_headers
            )

            elapsed = time.perf_counter() - start

            assert response.status_code == 200
            assert elapsed < 10.0, (
                f"AI insights took {elapsed:.2f}s; expected under 10s"
            )

        finally:

            for expense in expenses:

                existing = db.session.get(
                    Expense,
                    expense.id
                )

                if existing:
                    db.session.delete(existing)

            db.session.commit()


# ============================================================
# DATA VOLUME / LOAD TESTS
# ============================================================

class TestDataVolume:

    def test_pagination_works_correctly(
        self,
        client,
        auth_headers,
        test_user,
        db
    ):
        """TC-PERF-009: Expense pagination should return requested page size."""

        category = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert category is not None

        expenses = []

        try:

            for i in range(25):

                expense = Expense(
                    user_id=test_user.id,
                    category_id=category.id,
                    amount=100 + i,
                    date=date.today() - timedelta(days=i),
                    note="Pagination performance test"
                )

                expenses.append(expense)
                db.session.add(expense)

            db.session.commit()

            # Page 1
            response_1 = client.get(
                "/api/expenses?page=1&per_page=10",
                headers=auth_headers
            )

            assert response_1.status_code == 200

            data_1 = response_1.get_json()

            assert isinstance(
                data_1.get("data"),
                list
            )

            assert len(data_1["data"]) == 10

            assert "pagination" in data_1

            assert data_1["pagination"]["pages"] >= 3
            assert data_1["pagination"]["total"] >= 25

            # Page 2
            response_2 = client.get(
                "/api/expenses?page=2&per_page=10",
                headers=auth_headers
            )

            assert response_2.status_code == 200

            data_2 = response_2.get_json()

            assert len(data_2["data"]) == 10

        finally:

            for expense in expenses:

                existing = db.session.get(
                    Expense,
                    expense.id
                )

                if existing:
                    db.session.delete(existing)

            db.session.commit()

    def test_large_dataset_dashboard(
        self,
        client,
        auth_headers,
        test_user,
        db
    ):
        """TC-PERF-010: Dashboard handles 100 transactions."""

        category = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert category is not None

        expenses = []

        try:

            for i in range(100):

                expense = Expense(
                    user_id=test_user.id,
                    category_id=category.id,
                    amount=500 + i,
                    date=date.today() - timedelta(days=i),
                    note="Large dataset test"
                )

                expenses.append(expense)
                db.session.add(expense)

            db.session.commit()

            start = time.perf_counter()

            response = client.get(
                "/api/dashboard/summary",
                headers=auth_headers
            )

            elapsed = time.perf_counter() - start

            assert response.status_code == 200

            assert elapsed < 5.0, (
                f"Dashboard with 100 transactions took "
                f"{elapsed:.2f}s; expected under 5s"
            )

            data = response.get_json()

            assert data is not None
            assert "data" in data
            assert "summary" in data["data"]

        finally:

            for expense in expenses:

                existing = db.session.get(
                    Expense,
                    expense.id
                )

                if existing:
                    db.session.delete(existing)

            db.session.commit()


# ============================================================
# ADDITIONAL PERFORMANCE CHECKS
# ============================================================

class TestAnalyticsPerformance:

    def test_analytics_monthly_under_5_seconds(
        self,
        client,
        auth_headers
    ):
        """Additional: Monthly analytics should respond within 5 seconds."""

        today = date.today()

        start = time.perf_counter()

        response = client.get(
            f"/api/analytics/monthly"
            f"?month={today.month}"
            f"&year={today.year}",
            headers=auth_headers
        )

        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < 5.0, (
            f"Monthly analytics took {elapsed:.2f}s; expected under 5s"
        )

    def test_full_analytics_under_10_seconds(
        self,
        client,
        auth_headers
    ):
        """Additional: Full analytics bundle should respond within 10 seconds."""

        today = date.today()

        start = time.perf_counter()

        response = client.get(
            f"/api/analytics/full"
            f"?month={today.month}"
            f"&year={today.year}"
            f"&months=6",
            headers=auth_headers
        )

        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < 10.0, (
            f"Full analytics took {elapsed:.2f}s; expected under 10s"
        )

    def test_ai_category_suggestion_under_3_seconds(
        self,
        client,
        auth_headers
    ):
        """Additional: AI category suggestion should respond quickly."""

        start = time.perf_counter()

        response = client.post(
            "/api/ai/suggest-category",
            headers=auth_headers,
            json={
                "note": "electricity bill payment"
            }
        )

        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < 3.0, (
            f"Category suggestion took {elapsed:.2f}s; expected under 3s"
        )