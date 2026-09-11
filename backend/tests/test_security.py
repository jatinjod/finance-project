# backend/tests/test_security.py
# Security tests: JWT, authorization, data isolation, input validation

from datetime import date

from models.user import User
from models.expense import Expense
from models.category import Category
from extensions import bcrypt


# ============================================================
# JWT / AUTHENTICATION SECURITY
# ============================================================

class TestJWTSecurity:
    """JWT and authentication security tests."""

    def test_invalid_jwt_rejected(self, client):
        """TC-SEC-001: Malformed JWT token → 401."""

        response = client.get(
            "/api/user/profile",
            headers={
                "Authorization": "Bearer this.is.not.valid"
            }
        )

        assert response.status_code == 401

    def test_expired_jwt_rejected(self, client):
        """TC-SEC-002: Invalid/expired JWT → 401."""

        expired_token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTY0MDAwMDAwMCwianRp"
            "IjoiZmFrZSIsInR5cGUiOiJhY2Nlc3MiLCJzdWIiOiIxIn0."
            "invalid_signature"
        )

        response = client.get(
            "/api/user/profile",
            headers={
                "Authorization": f"Bearer {expired_token}"
            }
        )

        assert response.status_code == 401

    def test_no_token_rejected(self, client):
        """TC-SEC-003: Protected endpoint without token → 401."""

        response = client.get(
            "/api/expenses"
        )

        assert response.status_code == 401

    def test_wrong_token_format_rejected(self, client):
        """TC-SEC-004: Non-Bearer authorization header → 401."""

        response = client.get(
            "/api/expenses",
            headers={
                "Authorization": "Basic sometoken"
            }
        )

        assert response.status_code == 401

    def test_admin_endpoint_blocked_for_normal_user(
        self,
        client,
        auth_headers
    ):
        """TC-SEC-005: Normal user cannot access admin users endpoint."""

        response = client.get(
            "/api/admin/users",
            headers=auth_headers
        )

        assert response.status_code == 403

    def test_admin_stats_blocked_for_normal_user(
        self,
        client,
        auth_headers
    ):
        """TC-SEC-006: Normal user cannot access admin stats."""

        response = client.get(
            "/api/admin/stats",
            headers=auth_headers
        )

        assert response.status_code == 403

    def test_admin_endpoint_requires_token(self, client):
        """TC-SEC-007: Admin endpoint without token → 401."""

        response = client.get(
            "/api/admin/users"
        )

        assert response.status_code == 401

    def test_random_token_rejected(self, client):
        """TC-SEC-008: Random authorization token → 401."""

        response = client.get(
            "/api/expenses",
            headers={
                "Authorization": "Bearer random-invalid-token"
            }
        )

        assert response.status_code == 401


# ============================================================
# INPUT VALIDATION / INJECTION SECURITY
# ============================================================

class TestInputValidation:
    """Input validation and injection prevention tests."""

    def test_sql_injection_in_search(
        self,
        client,
        auth_headers
    ):
        """TC-SEC-011: SQL injection string is handled safely."""

        malicious_query = "'; DROP TABLE expenses; --"

        response = client.get(
            "/api/transactions",
            query_string={
                "q": malicious_query
            },
            headers=auth_headers
        )

        # Injection must never produce a server error.
        assert response.status_code != 500
        assert response.status_code == 200

    def test_xss_in_note_field(
        self,
        client,
        auth_headers,
        db
    ):
        """TC-SEC-012: Script payload is stored as data."""

        category = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert category is not None

        xss_note = '<script>alert("xss")</script>'

        response = client.post(
            "/api/expenses",
            headers=auth_headers,
            json={
                "amount": 100,
                "category_id": category.id,
                "date": str(date.today()),
                "note": xss_note
            }
        )

        assert response.status_code == 201

        data = response.get_json()

        assert data is not None
        assert data.get("status") == "success"

        expense_id = data["data"]["id"]

        expense = db.session.get(
            Expense,
            expense_id
        )

        assert expense is not None

        # Backend should treat it as a string.
        assert expense.note == xss_note

        # Cleanup
        db.session.delete(expense)
        db.session.commit()

    def test_very_large_amount_handled_safely(
        self,
        client,
        auth_headers,
        db
    ):
        """TC-SEC-013: Extremely large amount must not cause 500."""

        category = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert category is not None

        response = client.post(
            "/api/expenses",
            headers=auth_headers,
            json={
                "amount": 999999999999999,
                "category_id": category.id,
                "date": str(date.today())
            }
        )

        assert response.status_code in [201, 400]

        # Cleanup if accepted.
        if response.status_code == 201:

            data = response.get_json()

            if data and data.get("data"):
                expense_id = data["data"].get("id")

                if expense_id:
                    expense = db.session.get(
                        Expense,
                        expense_id
                    )

                    if expense:
                        db.session.delete(expense)
                        db.session.commit()

    def test_string_in_amount_field(
        self,
        client,
        auth_headers
    ):
        """TC-SEC-014: Non-numeric amount → 400."""

        category = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert category is not None

        response = client.post(
            "/api/expenses",
            headers=auth_headers,
            json={
                "amount": "not-a-number",
                "category_id": category.id,
                "date": str(date.today())
            }
        )

        assert response.status_code == 400

    def test_empty_json_body(
        self,
        client,
        auth_headers
    ):
        """TC-SEC-015: Empty POST body → 400."""

        response = client.post(
            "/api/expenses",
            headers=auth_headers,
            data="",
            content_type="application/json"
        )

        assert response.status_code == 400

    def test_passwords_not_in_profile_response(
        self,
        client,
        auth_headers
    ):
        """TC-SEC-016: Password fields never appear in profile response."""

        response = client.get(
            "/api/user/profile",
            headers=auth_headers
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data is not None

        user = data.get("data", {})

        assert "password" not in user
        assert "password_hash" not in user

    def test_other_user_data_not_accessible(
        self,
        client,
        auth_headers,
        test_user,
        db
    ):
        """TC-SEC-017: User cannot modify another user's expense."""

        other = User(
            name="Security User",
            email="othersec@test.com",
            password_hash=bcrypt.generate_password_hash(
                "pass"
            ).decode("utf-8"),
            role="user",
            is_active=True
        )

        db.session.add(other)
        db.session.commit()

        other_id = other.id
        expense_id = None

        try:

            category = Category.query.filter_by(
                name="Food",
                type="expense"
            ).first()

            assert category is not None

            expense = Expense(
                user_id=other.id,
                category_id=category.id,
                amount=500,
                date=date.today(),
                note="Private security test"
            )

            db.session.add(expense)
            db.session.commit()

            expense_id = expense.id

            response = client.put(
                f"/api/expenses/{expense_id}",
                headers=auth_headers,
                json={
                    "amount": 9999
                }
            )

            assert response.status_code == 404

            # Verify original record remains unchanged.
            unchanged = db.session.get(
                Expense,
                expense_id
            )

            assert unchanged is not None
            assert float(unchanged.amount) == 500.0

        finally:

            if expense_id is not None:

                expense = db.session.get(
                    Expense,
                    expense_id
                )

                if expense:
                    db.session.delete(expense)

            user = db.session.get(
                User,
                other_id
            )

            if user:
                db.session.delete(user)

            db.session.commit()

    def test_admin_cannot_delete_own_account(
        self,
        client,
        admin_headers,
        test_admin
    ):
        """TC-SEC-018: Admin cannot delete own account."""

        response = client.delete(
            f"/api/admin/users/{test_admin.id}",
            headers=admin_headers
        )

        assert response.status_code == 400

    def test_cannot_set_income_category_budget(
        self,
        client,
        auth_headers
    ):
        """TC-SEC-019: Income category cannot be used for budget."""

        income_category = Category.query.filter_by(
            name="Salary",
            type="income"
        ).first()

        assert income_category is not None

        today = date.today()

        response = client.post(
            "/api/budget",
            headers=auth_headers,
            json={
                "amount": 5000,
                "category_id": income_category.id,
                "month": today.month,
                "year": today.year
            }
        )

        assert response.status_code == 400

    def test_category_type_enforced(
        self,
        client,
        auth_headers
    ):
        """TC-SEC-020: Income category cannot be used for expense."""

        income_category = Category.query.filter_by(
            name="Salary",
            type="income"
        ).first()

        assert income_category is not None

        response = client.post(
            "/api/expenses",
            headers=auth_headers,
            json={
                "amount": 1000,
                "category_id": income_category.id,
                "date": str(date.today())
            }
        )

        assert response.status_code == 400

    def test_negative_expense_rejected(
        self,
        client,
        auth_headers
    ):
        """Additional security validation: negative expense → 400."""

        category = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert category is not None

        response = client.post(
            "/api/expenses",
            headers=auth_headers,
            json={
                "amount": -1,
                "category_id": category.id,
                "date": str(date.today())
            }
        )

        assert response.status_code == 400

    def test_zero_expense_rejected(
        self,
        client,
        auth_headers
    ):
        """Additional security validation: zero expense → 400."""

        category = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert category is not None

        response = client.post(
            "/api/expenses",
            headers=auth_headers,
            json={
                "amount": 0,
                "category_id": category.id,
                "date": str(date.today())
            }
        )

        assert response.status_code == 400

    def test_cannot_read_another_users_expenses(
        self,
        client,
        auth_headers,
        db
    ):
        """Additional security test: user sees only own expenses."""

        other = User(
            name="Isolation User",
            email="isolation_security@test.com",
            password_hash=bcrypt.generate_password_hash(
                "pass"
            ).decode("utf-8"),
            role="user",
            is_active=True
        )

        db.session.add(other)
        db.session.commit()

        other_id = other.id
        expense_id = None

        try:

            category = Category.query.filter_by(
                name="Food",
                type="expense"
            ).first()

            expense = Expense(
                user_id=other.id,
                category_id=category.id,
                amount=888,
                date=date.today()
            )

            db.session.add(expense)
            db.session.commit()

            expense_id = expense.id

            response = client.get(
                "/api/expenses",
                headers=auth_headers
            )

            assert response.status_code == 200

            data = response.get_json()

            ids = [
                item["id"]
                for item in data.get("data", [])
                if isinstance(item, dict)
                and "id" in item
            ]

            assert expense_id not in ids

        finally:

            if expense_id is not None:

                expense = db.session.get(
                    Expense,
                    expense_id
                )

                if expense:
                    db.session.delete(expense)

            user = db.session.get(
                User,
                other_id
            )

            if user:
                db.session.delete(user)

            db.session.commit()