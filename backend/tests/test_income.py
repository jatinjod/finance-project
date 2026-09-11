# backend/tests/test_income.py
# Unit tests for income management module

from datetime import date

from models.income import Income
from models.category import Category


class TestIncome:
    """Income management tests."""

    def test_add_valid_income(
        self,
        client,
        auth_headers,
        test_user,
        db
    ):
        """TC-INC-001: Add valid income → 201."""

        cat = Category.query.filter_by(
            name="Salary",
            type="income"
        ).first()

        assert cat is not None

        response = client.post(
            "/api/income",
            headers=auth_headers,
            json={
                "amount": 25000.00,
                "category_id": cat.id,
                "date": str(date.today()),
                "note": "Monthly salary"
            }
        )

        assert response.status_code == 201

        data = response.get_json()

        assert data is not None
        assert data.get("status") == "success"
        assert isinstance(data.get("data"), dict)
        assert "id" in data["data"]
        assert data["data"]["amount"] == 25000.0

        # Cleanup
        income = db.session.get(
            Income,
            data["data"]["id"]
        )

        if income:
            db.session.delete(income)
            db.session.commit()

    def test_add_income_wrong_category_type(
        self,
        client,
        auth_headers
    ):
        """TC-INC-002: Expense category used for income → 400."""

        expense_cat = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert expense_cat is not None

        response = client.post(
            "/api/income",
            headers=auth_headers,
            json={
                "amount": 25000,
                "category_id": expense_cat.id,
                "date": str(date.today())
            }
        )

        assert response.status_code == 400

    def test_get_income_list(
        self,
        client,
        auth_headers,
        sample_income
    ):
        """TC-INC-003: Get income list → 200 with pagination."""

        response = client.get(
            "/api/income",
            headers=auth_headers
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data is not None
        assert "data" in data
        assert isinstance(data["data"], list)
        assert "pagination" in data
        assert isinstance(data["pagination"], dict)

    def test_update_income(
        self,
        client,
        auth_headers,
        sample_income
    ):
        """TC-INC-004: Update income amount → 200."""

        response = client.put(
            f"/api/income/{sample_income.id}",
            headers=auth_headers,
            json={
                "amount": 30000.00
            }
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data is not None
        assert data.get("status") == "success"
        assert data["data"]["amount"] == 30000.0

    def test_delete_income(
        self,
        client,
        auth_headers,
        db,
        test_user
    ):
        """TC-INC-005: Delete income → 200 and record removed."""

        cat = Category.query.filter_by(
            name="Freelance",
            type="income"
        ).first()

        assert cat is not None

        income = Income(
            user_id=test_user.id,
            category_id=cat.id,
            amount=5000.00,
            date=date.today(),
            note="Delete income test"
        )

        db.session.add(income)
        db.session.commit()

        income_id = income.id

        response = client.delete(
            f"/api/income/{income_id}",
            headers=auth_headers
        )

        assert response.status_code == 200

        deleted_income = db.session.get(
            Income,
            income_id
        )

        assert deleted_income is None

    def test_filter_income_by_category(
        self,
        client,
        auth_headers,
        sample_income
    ):
        """TC-INC-006: Filter income by category."""

        cat = Category.query.filter_by(
            name="Salary",
            type="income"
        ).first()

        assert cat is not None

        response = client.get(
            f"/api/income?category_id={cat.id}",
            headers=auth_headers
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data is not None
        assert isinstance(data.get("data"), list)

        for income in data["data"]:
            assert income["category_id"] == cat.id

    def test_income_decimal_precision(
        self,
        client,
        auth_headers,
        db,
        test_user
    ):
        """TC-INC-007: Income amount preserves decimal precision."""

        cat = Category.query.filter_by(
            name="Salary",
            type="income"
        ).first()

        assert cat is not None

        response = client.post(
            "/api/income",
            headers=auth_headers,
            json={
                "amount": 12345.67,
                "category_id": cat.id,
                "date": str(date.today()),
                "note": "Precision test"
            }
        )

        assert response.status_code == 201

        data = response.get_json()

        assert data is not None
        assert data["data"]["amount"] == 12345.67

        income_id = data["data"]["id"]

        income = db.session.get(
            Income,
            income_id
        )

        assert income is not None
        assert float(income.amount) == 12345.67

        # Cleanup
        db.session.delete(income)
        db.session.commit()