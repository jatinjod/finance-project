# backend/tests/test_dashboard.py
# Unit tests for dashboard summary endpoint

from datetime import date

from models.user import User
from models.income import Income
from models.expense import Expense
from models.category import Category
from extensions import bcrypt


class TestDashboard:
    """Dashboard summary endpoint tests."""

    def test_dashboard_returns_200(
        self,
        client,
        auth_headers
    ):
        """TC-DASH-001: Dashboard endpoint returns 200."""

        response = client.get(
            "/api/dashboard/summary",
            headers=auth_headers
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data is not None
        assert data.get("status") == "success"
        assert isinstance(data.get("data"), dict)

    def test_dashboard_has_required_keys(
        self,
        client,
        auth_headers
    ):
        """TC-DASH-002: Dashboard contains required sections."""

        response = client.get(
            "/api/dashboard/summary",
            headers=auth_headers
        )

        assert response.status_code == 200

        body = response.get_json()

        assert body is not None
        assert isinstance(body.get("data"), dict)

        data = body["data"]

        assert "summary" in data
        assert "budget_status" in data
        assert "recent_transactions" in data
        assert "category_chart" in data
        assert "monthly_chart" in data

        assert isinstance(data["summary"], dict)
        assert isinstance(data["budget_status"], dict)
        assert isinstance(data["recent_transactions"], list)
        assert isinstance(data["category_chart"], list)
        assert isinstance(data["monthly_chart"], list)

    def test_dashboard_summary_calculation(
        self,
        client,
        auth_headers,
        db,
        test_user
    ):
        """TC-DASH-003: Dashboard balance = income - expenses."""

        today = date.today()

        salary_category = Category.query.filter_by(
            name="Salary",
            type="income"
        ).first()

        food_category = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert salary_category is not None
        assert food_category is not None

        income = Income(
            user_id=test_user.id,
            category_id=salary_category.id,
            amount=25000,
            date=today,
            note="Dashboard income test"
        )

        expense = Expense(
            user_id=test_user.id,
            category_id=food_category.id,
            amount=5000,
            date=today,
            note="Dashboard expense test"
        )

        db.session.add_all([
            income,
            expense
        ])
        db.session.commit()

        income_id = income.id
        expense_id = expense.id

        try:
            response = client.get(
                "/api/dashboard/summary",
                headers=auth_headers
            )

            assert response.status_code == 200

            body = response.get_json()

            assert body is not None
            assert isinstance(body.get("data"), dict)

            summary = body["data"]["summary"]

            assert summary["total_income"] >= 25000
            assert summary["total_expenses"] >= 5000

            expected_balance = (
                summary["total_income"]
                - summary["total_expenses"]
            )

            assert summary["balance"] == expected_balance

        finally:
            existing_income = db.session.get(
                Income,
                income_id
            )

            if existing_income:
                db.session.delete(existing_income)

            existing_expense = db.session.get(
                Expense,
                expense_id
            )

            if existing_expense:
                db.session.delete(existing_expense)

            db.session.commit()

    def test_dashboard_empty_user(
        self,
        client,
        db
    ):
        """TC-DASH-004: New user with no data gets zero totals."""

        new_user = User(
            name="Empty User",
            email="empty@test.com",
            password_hash=bcrypt.generate_password_hash(
                "pass"
            ).decode("utf-8"),
            role="user",
            is_active=True
        )

        db.session.add(new_user)
        db.session.commit()

        user_id = new_user.id

        try:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "empty@test.com",
                    "password": "pass"
                }
            )

            assert login_response.status_code == 200

            login_data = login_response.get_json()

            assert login_data is not None
            assert isinstance(
                login_data.get("data"),
                dict
            )

            token = login_data["data"]["access_token"]

            headers = {
                "Authorization": f"Bearer {token}"
            }

            response = client.get(
                "/api/dashboard/summary",
                headers=headers
            )

            assert response.status_code == 200

            body = response.get_json()

            assert body is not None
            assert isinstance(body.get("data"), dict)

            summary = body["data"]["summary"]

            assert summary["total_income"] == 0
            assert summary["total_expenses"] == 0
            assert summary["balance"] == 0

        finally:
            existing_user = db.session.get(
                User,
                user_id
            )

            if existing_user:
                db.session.delete(existing_user)
                db.session.commit()

    def test_dashboard_requires_auth(
        self,
        client
    ):
        """TC-DASH-005: Dashboard requires authentication."""

        response = client.get(
            "/api/dashboard/summary"
        )

        assert response.status_code == 401

    def test_monthly_chart_has_6_months(
        self,
        client,
        auth_headers
    ):
        """TC-DASH-006: Monthly chart contains 6 months."""

        response = client.get(
            "/api/dashboard/summary",
            headers=auth_headers
        )

        assert response.status_code == 200

        body = response.get_json()

        assert body is not None
        assert isinstance(body.get("data"), dict)

        chart = body["data"]["monthly_chart"]

        assert isinstance(chart, list)
        assert len(chart) == 6

    def test_dashboard_category_chart_structure(
        self,
        client,
        auth_headers
    ):
        """Additional test: Category chart has valid list structure."""

        response = client.get(
            "/api/dashboard/summary",
            headers=auth_headers
        )

        assert response.status_code == 200

        body = response.get_json()
        data = body["data"]

        assert isinstance(
            data["category_chart"],
            list
        )

        for item in data["category_chart"]:

            assert isinstance(item, dict)

            assert "category" in item
            assert "amount" in item

    def test_dashboard_recent_transactions_structure(
        self,
        client,
        auth_headers
    ):
        """Additional test: Recent transactions have valid structure."""

        response = client.get(
            "/api/dashboard/summary",
            headers=auth_headers
        )

        assert response.status_code == 200

        body = response.get_json()
        transactions = body["data"]["recent_transactions"]

        assert isinstance(
            transactions,
            list
        )

        for transaction in transactions:

            assert isinstance(
                transaction,
                dict
            )

            assert "id" in transaction
            assert "amount" in transaction

    def test_dashboard_summary_keys(
        self,
        client,
        auth_headers
    ):
        """Additional test: Summary contains financial metrics."""

        response = client.get(
            "/api/dashboard/summary",
            headers=auth_headers
        )

        assert response.status_code == 200

        summary = response.get_json()["data"]["summary"]

        assert "total_income" in summary
        assert "total_expenses" in summary
        assert "balance" in summary

        assert isinstance(
            summary["total_income"],
            (int, float)
        )

        assert isinstance(
            summary["total_expenses"],
            (int, float)
        )

        assert isinstance(
            summary["balance"],
            (int, float)
        )