# backend/tests/test_budget.py
# Unit tests for budget management module

from datetime import date

from models.budget import Budget
from models.category import Category


class TestBudget:
    """Budget management test cases."""

    def test_set_overall_budget(
        self,
        client,
        auth_headers,
        db
    ):
        """TC-BUD-001: Set overall monthly budget → 200/201."""

        today = date.today()

        response = client.post(
            "/api/budget",
            headers=auth_headers,
            json={
                "amount": 20000,
                "month": today.month,
                "year": today.year
            }
        )

        assert response.status_code in [200, 201]

        data = response.get_json()

        assert data is not None
        assert data.get("status") == "success"
        assert isinstance(data.get("data"), dict)
        assert "id" in data["data"]

        budget = db.session.get(
            Budget,
            data["data"]["id"]
        )

        assert budget is not None
        assert float(budget.amount) == 20000.0

        # Cleanup
        db.session.delete(budget)
        db.session.commit()

    def test_set_category_budget(
        self,
        client,
        auth_headers,
        db
    ):
        """TC-BUD-002: Set category-specific budget → 200/201."""

        today = date.today()

        cat = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert cat is not None

        response = client.post(
            "/api/budget",
            headers=auth_headers,
            json={
                "amount": 5000,
                "category_id": cat.id,
                "month": today.month,
                "year": today.year
            }
        )

        assert response.status_code in [200, 201]

        data = response.get_json()

        assert data is not None
        assert data.get("status") == "success"
        assert isinstance(data.get("data"), dict)
        assert "id" in data["data"]

        budget = db.session.get(
            Budget,
            data["data"]["id"]
        )

        assert budget is not None
        assert budget.category_id == cat.id
        assert float(budget.amount) == 5000.0

        # Cleanup
        db.session.delete(budget)
        db.session.commit()

    def test_budget_negative_amount(
        self,
        client,
        auth_headers
    ):
        """TC-BUD-003: Negative budget amount → 400."""

        today = date.today()

        response = client.post(
            "/api/budget",
            headers=auth_headers,
            json={
                "amount": -1000,
                "month": today.month,
                "year": today.year
            }
        )

        assert response.status_code == 400

    def test_get_budget_status(
        self,
        client,
        auth_headers,
        db,
        test_user
    ):
        """TC-BUD-004: Get budget status → 200."""

        today = date.today()

        budget = Budget(
            user_id=test_user.id,
            category_id=None,
            month=date(
                today.year,
                today.month,
                1
            ),
            amount=20000
        )

        db.session.add(budget)
        db.session.commit()

        budget_id = budget.id

        response = client.get(
            "/api/budget",
            headers=auth_headers
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data is not None
        assert data.get("status") == "success"
        assert isinstance(data.get("data"), dict)

        assert "overall" in data["data"]
        assert "categories" in data["data"]

        assert data["data"]["overall"] is not None
        assert (
            data["data"]["overall"]["budget_id"]
            == budget_id
        )

        # Cleanup
        existing = db.session.get(
            Budget,
            budget_id
        )

        if existing:
            db.session.delete(existing)
            db.session.commit()

    def test_get_budget_status_endpoint(
        self,
        client,
        auth_headers,
        db,
        test_user
    ):
        """Additional test: /api/budget/status → 200."""

        today = date.today()

        budget = Budget(
            user_id=test_user.id,
            category_id=None,
            month=date(
                today.year,
                today.month,
                1
            ),
            amount=30000
        )

        db.session.add(budget)
        db.session.commit()

        budget_id = budget.id

        response = client.get(
            "/api/budget/status",
            headers=auth_headers
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data is not None
        assert data.get("status") == "success"
        assert isinstance(data.get("data"), dict)
        assert "overall" in data["data"]
        assert "categories" in data["data"]

        # Cleanup
        existing = db.session.get(
            Budget,
            budget_id
        )

        if existing:
            db.session.delete(existing)
            db.session.commit()

    def test_budget_update_on_duplicate(
        self,
        client,
        auth_headers,
        db
    ):
        """TC-BUD-005: Setting same budget again updates existing budget."""

        today = date.today()

        first_response = client.post(
            "/api/budget",
            headers=auth_headers,
            json={
                "amount": 20000,
                "month": today.month,
                "year": today.year
            }
        )

        assert first_response.status_code in [200, 201]

        first_data = first_response.get_json()

        assert first_data is not None
        assert first_data.get("status") == "success"

        first_budget_id = first_data["data"]["id"]

        second_response = client.post(
            "/api/budget",
            headers=auth_headers,
            json={
                "amount": 25000,
                "month": today.month,
                "year": today.year
            }
        )

        assert second_response.status_code == 200

        second_data = second_response.get_json()

        assert second_data is not None
        assert second_data.get("status") == "success"
        assert second_data["data"]["id"] == first_budget_id
        assert second_data["data"]["amount"] == 25000.0

        # Cleanup
        budget = db.session.get(
            Budget,
            first_budget_id
        )

        if budget:
            db.session.delete(budget)
            db.session.commit()

    def test_delete_budget(
        self,
        client,
        auth_headers,
        db,
        test_user
    ):
        """TC-BUD-006: Delete budget → 200."""

        today = date.today()

        budget = Budget(
            user_id=test_user.id,
            category_id=None,
            month=date(
                today.year,
                today.month,
                1
            ),
            amount=20000
        )

        db.session.add(budget)
        db.session.commit()

        budget_id = budget.id

        response = client.delete(
            f"/api/budget/{budget_id}",
            headers=auth_headers
        )

        assert response.status_code == 200

        deleted_budget = db.session.get(
            Budget,
            budget_id
        )

        assert deleted_budget is None

    def test_delete_nonexistent_budget(
        self,
        client,
        auth_headers
    ):
        """Additional test: Delete missing budget → 404."""

        response = client.delete(
            "/api/budget/99999",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_budget_invalid_month(
        self,
        client,
        auth_headers
    ):
        """TC-BUD-007: Invalid month 13 → 400."""

        response = client.post(
            "/api/budget",
            headers=auth_headers,
            json={
                "amount": 20000,
                "month": 13,
                "year": 2024
            }
        )

        assert response.status_code == 400

    def test_budget_invalid_year(
        self,
        client,
        auth_headers
    ):
        """Additional test: Invalid year → 400."""

        response = client.post(
            "/api/budget",
            headers=auth_headers,
            json={
                "amount": 20000,
                "month": 1,
                "year": 0
            }
        )

        assert response.status_code == 400

    def test_budget_without_auth(
        self,
        client
    ):
        """Additional security test: Budget request without JWT → 401."""

        response = client.post(
            "/api/budget",
            json={
                "amount": 20000,
                "month": date.today().month,
                "year": date.today().year
            }
        )

        assert response.status_code == 401

    def test_income_category_budget_rejected(
        self,
        client,
        auth_headers
    ):
        """Additional test: Income category cannot receive expense budget."""

        today = date.today()

        income_cat = Category.query.filter_by(
            name="Salary",
            type="income"
        ).first()

        assert income_cat is not None

        response = client.post(
            "/api/budget",
            headers=auth_headers,
            json={
                "amount": 5000,
                "category_id": income_cat.id,
                "month": today.month,
                "year": today.year
            }
        )

        assert response.status_code == 400