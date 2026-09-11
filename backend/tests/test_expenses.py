# backend/tests/test_expenses.py
# Unit tests for expense management module

from datetime import date

from models.expense import Expense
from models.category import Category
from models.user import User
from extensions import bcrypt


class TestAddExpense:
    """Expense creation tests."""

    def test_add_valid_expense(self, client, auth_headers, test_user, db):
        """TC-EXP-001: Add expense with valid data → 201."""

        cat = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert cat is not None

        response = client.post(
            "/api/expenses",
            headers=auth_headers,
            json={
                "amount": 1500.00,
                "category_id": cat.id,
                "date": str(date.today()),
                "note": "Test expense"
            }
        )

        assert response.status_code == 201

        data = response.get_json()

        assert data is not None
        assert data.get("status") == "success"
        assert isinstance(data.get("data"), dict)
        assert data["data"]["amount"] == 1500.0
        assert "id" in data["data"]

        # Cleanup
        expense = db.session.get(
            Expense,
            data["data"]["id"]
        )

        if expense:
            db.session.delete(expense)
            db.session.commit()

    def test_add_expense_without_note(
        self,
        client,
        auth_headers,
        test_user,
        db
    ):
        """TC-EXP-002: Add expense without optional note → 201."""

        cat = Category.query.filter_by(
            name="Transport",
            type="expense"
        ).first()

        assert cat is not None

        response = client.post(
            "/api/expenses",
            headers=auth_headers,
            json={
                "amount": 500,
                "category_id": cat.id,
                "date": str(date.today())
            }
        )

        assert response.status_code == 201

        data = response.get_json()

        assert data is not None
        assert data.get("status") == "success"

        exp_id = data["data"]["id"]

        exp = db.session.get(
            Expense,
            exp_id
        )

        if exp:
            db.session.delete(exp)
            db.session.commit()

    def test_add_expense_negative_amount(
        self,
        client,
        auth_headers
    ):
        """TC-EXP-003: Negative amount → 400."""

        cat = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert cat is not None

        response = client.post(
            "/api/expenses",
            headers=auth_headers,
            json={
                "amount": -500,
                "category_id": cat.id,
                "date": str(date.today())
            }
        )

        assert response.status_code == 400

    def test_add_expense_zero_amount(
        self,
        client,
        auth_headers
    ):
        """TC-EXP-004: Zero amount → 400."""

        cat = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert cat is not None

        response = client.post(
            "/api/expenses",
            headers=auth_headers,
            json={
                "amount": 0,
                "category_id": cat.id,
                "date": str(date.today())
            }
        )

        assert response.status_code == 400

    def test_add_expense_missing_amount(
        self,
        client,
        auth_headers
    ):
        """TC-EXP-005: Missing amount → 400."""

        cat = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert cat is not None

        response = client.post(
            "/api/expenses",
            headers=auth_headers,
            json={
                "category_id": cat.id,
                "date": str(date.today())
            }
        )

        assert response.status_code == 400

    def test_add_expense_missing_category(
        self,
        client,
        auth_headers
    ):
        """TC-EXP-006: Missing category → 400."""

        response = client.post(
            "/api/expenses",
            headers=auth_headers,
            json={
                "amount": 1000,
                "date": str(date.today())
            }
        )

        assert response.status_code == 400

    def test_add_expense_invalid_date(
        self,
        client,
        auth_headers
    ):
        """TC-EXP-007: Invalid date format → 400."""

        cat = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert cat is not None

        response = client.post(
            "/api/expenses",
            headers=auth_headers,
            json={
                "amount": 1000,
                "category_id": cat.id,
                "date": "not-a-date"
            }
        )

        assert response.status_code == 400

    def test_add_expense_without_auth(self, client):
        """TC-EXP-008: Add expense without authentication → 401."""

        response = client.post(
            "/api/expenses",
            json={
                "amount": 1000,
                "category_id": 1,
                "date": str(date.today())
            }
        )

        assert response.status_code == 401

    def test_add_expense_wrong_category_type(
        self,
        client,
        auth_headers
    ):
        """TC-EXP-009: Income category used for expense → 400."""

        income_cat = Category.query.filter_by(
            name="Salary",
            type="income"
        ).first()

        assert income_cat is not None

        response = client.post(
            "/api/expenses",
            headers=auth_headers,
            json={
                "amount": 1000,
                "category_id": income_cat.id,
                "date": str(date.today())
            }
        )

        assert response.status_code == 400


class TestGetExpenses:
    """Expense retrieval tests."""

    def test_get_expenses_returns_list(
        self,
        client,
        auth_headers,
        sample_expense
    ):
        """TC-EXP-010: Get expenses returns list."""

        response = client.get(
            "/api/expenses",
            headers=auth_headers
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data is not None
        assert "data" in data
        assert isinstance(data["data"], list)

        assert "pagination" in data
        assert isinstance(data["pagination"], dict)

    def test_get_expenses_only_own_data(
        self,
        client,
        auth_headers,
        sample_expense,
        db
    ):
        """TC-EXP-011: User can only see their own expenses."""

        other = User(
            name="Other User",
            email="other@test.com",
            password_hash=bcrypt.generate_password_hash(
                "pass"
            ).decode("utf-8"),
            role="user",
            is_active=True
        )

        db.session.add(other)
        db.session.commit()

        try:

            login_res = client.post(
                "/api/auth/login",
                json={
                    "email": "other@test.com",
                    "password": "pass"
                }
            )

            assert login_res.status_code == 200

            login_data = login_res.get_json()

            other_token = login_data["data"]["access_token"]

            other_headers = {
                "Authorization": f"Bearer {other_token}"
            }

            response = client.get(
                "/api/expenses",
                headers=other_headers
            )

            assert response.status_code == 200

            data = response.get_json()

            assert len(data["data"]) == 0

        finally:

            existing_other = db.session.get(
                User,
                other.id
            )

            if existing_other:
                db.session.delete(existing_other)
                db.session.commit()

    def test_get_expenses_filter_by_month(
        self,
        client,
        auth_headers,
        sample_expense
    ):
        """TC-EXP-012: Filter expenses by month and year."""

        today = date.today()

        response = client.get(
            f"/api/expenses?month={today.month}&year={today.year}",
            headers=auth_headers
        )

        assert response.status_code == 200

    def test_get_expenses_filter_by_category(
        self,
        client,
        auth_headers,
        sample_expense
    ):
        """TC-EXP-013: Filter expenses by category."""

        cat = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert cat is not None

        response = client.get(
            f"/api/expenses?category_id={cat.id}",
            headers=auth_headers
        )

        assert response.status_code == 200

        data = response.get_json()

        assert isinstance(data["data"], list)

        for exp in data["data"]:
            assert exp["category_id"] == cat.id


class TestUpdateDeleteExpense:
    """Expense update and delete tests."""

    def test_update_expense_amount(
        self,
        client,
        auth_headers,
        sample_expense
    ):
        """TC-EXP-014: Update expense amount → 200."""

        response = client.put(
            f"/api/expenses/{sample_expense.id}",
            headers=auth_headers,
            json={
                "amount": 2000.00
            }
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data is not None
        assert data["data"]["amount"] == 2000.0

    def test_update_expense_note(
        self,
        client,
        auth_headers,
        sample_expense
    ):
        """TC-EXP-015: Update expense note → 200."""

        response = client.put(
            f"/api/expenses/{sample_expense.id}",
            headers=auth_headers,
            json={
                "note": "Updated note"
            }
        )

        assert response.status_code == 200

    def test_update_nonexistent_expense(
        self,
        client,
        auth_headers
    ):
        """TC-EXP-016: Update non-existent expense → 404."""

        response = client.put(
            "/api/expenses/99999",
            headers=auth_headers,
            json={
                "amount": 1000
            }
        )

        assert response.status_code == 404

    def test_delete_expense(
        self,
        client,
        auth_headers,
        db,
        test_user
    ):
        """TC-EXP-017: Delete an expense → 200."""

        cat = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert cat is not None

        expense = Expense(
            user_id=test_user.id,
            category_id=cat.id,
            amount=100.00,
            date=date.today()
        )

        db.session.add(expense)
        db.session.commit()

        expense_id = expense.id

        response = client.delete(
            f"/api/expenses/{expense_id}",
            headers=auth_headers
        )

        assert response.status_code == 200

        deleted_expense = db.session.get(
            Expense,
            expense_id
        )

        assert deleted_expense is None

    def test_delete_nonexistent_expense(
        self,
        client,
        auth_headers
    ):
        """TC-EXP-018: Delete non-existent expense → 404."""

        response = client.delete(
            "/api/expenses/99999",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_cannot_delete_another_users_expense(
        self,
        client,
        auth_headers,
        sample_expense,
        db
    ):
        """TC-EXP-019: Cannot delete another user's expense → 404."""

        other = User(
            name="Other User 2",
            email="other2@test.com",
            password_hash=bcrypt.generate_password_hash(
                "pass"
            ).decode("utf-8"),
            role="user",
            is_active=True
        )

        db.session.add(other)
        db.session.commit()

        try:

            login_res = client.post(
                "/api/auth/login",
                json={
                    "email": "other2@test.com",
                    "password": "pass"
                }
            )

            assert login_res.status_code == 200

            other_token = (
                login_res.get_json()
                ["data"]
                ["access_token"]
            )

            other_headers = {
                "Authorization": f"Bearer {other_token}"
            }

            response = client.delete(
                f"/api/expenses/{sample_expense.id}",
                headers=other_headers
            )

            assert response.status_code == 404

        finally:

            existing_other = db.session.get(
                User,
                other.id
            )

            if existing_other:
                db.session.delete(existing_other)
                db.session.commit()

    def test_update_expense_negative_amount(
        self,
        client,
        auth_headers,
        sample_expense
    ):
        """TC-EXP-020: Update with negative amount → 400."""

        response = client.put(
            f"/api/expenses/{sample_expense.id}",
            headers=auth_headers,
            json={
                "amount": -500
            }
        )

        assert response.status_code == 400