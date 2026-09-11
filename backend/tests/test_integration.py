# backend/tests/test_integration.py
# End-to-end integration tests for complete FinanceAI data flows

from datetime import date

from models.user import User
from models.expense import Expense
from models.income import Income
from models.notification import Notification
from models.budget import Budget
from models.category import Category

from extensions import bcrypt


# ============================================================
# COMPLETE EXPENSE FLOW
# ============================================================

class TestCompleteExpenseFlow:
    """End-to-end expense lifecycle integration tests."""

    def test_full_expense_crud_flow(
        self,
        client,
        auth_headers,
        test_user,
        db
    ):
        """TC-INT-001: Create → Read → Update → Delete."""

        category = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert category is not None

        # ----------------------------------------------------
        # CREATE
        # ----------------------------------------------------

        create_response = client.post(
            "/api/expenses",
            headers=auth_headers,
            json={
                "amount": 1500,
                "category_id": category.id,
                "date": str(date.today()),
                "note": "Integration test"
            }
        )

        assert create_response.status_code == 201

        create_data = create_response.get_json()

        assert create_data is not None
        assert create_data.get("status") == "success"
        assert isinstance(create_data.get("data"), dict)

        expense_id = create_data["data"]["id"]

        assert create_data["data"]["amount"] == 1500.0

        # ----------------------------------------------------
        # READ
        # ----------------------------------------------------

        read_response = client.get(
            "/api/expenses",
            headers=auth_headers
        )

        assert read_response.status_code == 200

        read_data = read_response.get_json()

        assert read_data is not None
        assert isinstance(read_data.get("data"), list)

        expense_ids = [
            item["id"]
            for item in read_data["data"]
            if isinstance(item, dict) and "id" in item
        ]

        assert expense_id in expense_ids

        # ----------------------------------------------------
        # UPDATE
        # ----------------------------------------------------

        update_response = client.put(
            f"/api/expenses/{expense_id}",
            headers=auth_headers,
            json={
                "amount": 2000
            }
        )

        assert update_response.status_code == 200

        update_data = update_response.get_json()

        assert update_data is not None
        assert update_data.get("status") == "success"
        assert update_data["data"]["amount"] == 2000.0

        # ----------------------------------------------------
        # DELETE
        # ----------------------------------------------------

        delete_response = client.delete(
            f"/api/expenses/{expense_id}",
            headers=auth_headers
        )

        assert delete_response.status_code == 200

        deleted_expense = db.session.get(
            Expense,
            expense_id
        )

        assert deleted_expense is None

    def test_expense_appears_in_dashboard(
        self,
        client,
        auth_headers,
        test_user,
        db
    ):
        """TC-INT-002: Added expense updates dashboard totals."""

        category = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert category is not None

        # Get initial dashboard
        before_response = client.get(
            "/api/dashboard/summary",
            headers=auth_headers
        )

        assert before_response.status_code == 200

        before_data = before_response.get_json()

        before_total = float(
            before_data["data"]["summary"]["total_expenses"]
        )

        # Add expense
        create_response = client.post(
            "/api/expenses",
            headers=auth_headers,
            json={
                "amount": 3000,
                "category_id": category.id,
                "date": str(date.today()),
                "note": "Dashboard integration test"
            }
        )

        assert create_response.status_code == 201

        create_data = create_response.get_json()

        expense_id = create_data["data"]["id"]

        # Get updated dashboard
        after_response = client.get(
            "/api/dashboard/summary",
            headers=auth_headers
        )

        assert after_response.status_code == 200

        after_data = after_response.get_json()

        after_total = float(
            after_data["data"]["summary"]["total_expenses"]
        )

        assert after_total >= before_total + 3000

        # Cleanup
        expense = db.session.get(
            Expense,
            expense_id
        )

        if expense:
            db.session.delete(expense)
            db.session.commit()

    def test_expense_appears_in_transaction_history(
        self,
        client,
        auth_headers,
        test_user,
        db
    ):
        """TC-INT-003: Added expense appears in transactions."""

        category = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert category is not None

        create_response = client.post(
            "/api/expenses",
            headers=auth_headers,
            json={
                "amount": 999,
                "category_id": category.id,
                "date": str(date.today()),
                "note": "History integration test"
            }
        )

        assert create_response.status_code == 201

        expense_id = create_response.get_json()["data"]["id"]

        history_response = client.get(
            "/api/transactions",
            headers=auth_headers
        )

        assert history_response.status_code == 200

        history_data = history_response.get_json()

        assert history_data is not None
        assert isinstance(
            history_data.get("data"),
            list
        )

        matching_transactions = [
            tx
            for tx in history_data["data"]
            if tx.get("id") == expense_id
            and tx.get("transaction_type") == "expense"
        ]

        assert len(matching_transactions) >= 1

        # Cleanup
        expense = db.session.get(
            Expense,
            expense_id
        )

        if expense:
            db.session.delete(expense)
            db.session.commit()

    def test_expense_triggers_budget_check(
        self,
        client,
        auth_headers,
        test_user,
        db
    ):
        """TC-INT-004: Expense above 80% budget triggers notification."""

        today = date.today()

        category = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert category is not None

        budget = Budget(
            user_id=test_user.id,
            category_id=None,
            month=date(
                today.year,
                today.month,
                1
            ),
            amount=100
        )

        db.session.add(budget)
        db.session.commit()

        try:

            expense_response = client.post(
                "/api/expenses",
                headers=auth_headers,
                json={
                    "amount": 90,
                    "category_id": category.id,
                    "date": str(today),
                    "note": "Budget integration test"
                }
            )

            assert expense_response.status_code == 201

            notification_response = client.get(
                "/api/notifications",
                headers=auth_headers
            )

            assert notification_response.status_code == 200

            notification_data = notification_response.get_json()

            assert notification_data is not None
            assert isinstance(
                notification_data.get("data"),
                list
            )

            messages = [
                str(item.get("message", ""))
                for item in notification_data["data"]
                if isinstance(item, dict)
            ]

            has_budget_notification = any(
                (
                    "budget" in message.lower()
                    or "overall" in message.lower()
                )
                for message in messages
            )

            assert has_budget_notification, (
                "Expected budget notification was not found."
            )

        finally:

            # Remove test expenses
            test_expenses = Expense.query.filter_by(
                user_id=test_user.id
            ).all()

            for expense in test_expenses:
                db.session.delete(expense)

            # Remove test budget
            existing_budget = db.session.get(
                Budget,
                budget.id
            )

            if existing_budget:
                db.session.delete(existing_budget)

            # Remove test notifications
            test_notifications = Notification.query.filter_by(
                user_id=test_user.id
            ).all()

            for notification in test_notifications:
                db.session.delete(notification)

            db.session.commit()

    def test_report_reflects_expenses(
        self,
        client,
        auth_headers,
        test_user,
        db
    ):
        """TC-INT-005: Monthly report includes added expense."""

        today = date.today()

        category = Category.query.filter_by(
            name="Entertainment",
            type="expense"
        ).first()

        assert category is not None

        create_response = client.post(
            "/api/expenses",
            headers=auth_headers,
            json={
                "amount": 2500,
                "category_id": category.id,
                "date": str(today),
                "note": "Report integration test"
            }
        )

        assert create_response.status_code == 201

        expense_id = create_response.get_json()["data"]["id"]

        report_response = client.get(
            f"/api/reports/monthly"
            f"?month={today.month}"
            f"&year={today.year}",
            headers=auth_headers
        )

        assert report_response.status_code == 200

        report_data = report_response.get_json()

        assert report_data is not None
        assert isinstance(
            report_data.get("data"),
            dict
        )

        data = report_data["data"]

        assert data["total_expenses"] >= 2500

        assert (
            "Entertainment"
            in data.get("expense_by_category", {})
        )

        # Cleanup
        expense = db.session.get(
            Expense,
            expense_id
        )

        if expense:
            db.session.delete(expense)
            db.session.commit()


# ============================================================
# USER DATA ISOLATION
# ============================================================

class TestUserDataIsolation:
    """Integration tests for user-to-user data isolation."""

    def test_users_cannot_see_each_others_expenses(
        self,
        client,
        auth_headers,
        test_user,
        db
    ):
        """TC-INT-011: User A cannot see User B's expenses."""

        user_b = User(
            name="User B",
            email="userb@test.com",
            password_hash=bcrypt.generate_password_hash(
                "pass"
            ).decode("utf-8"),
            role="user",
            is_active=True
        )

        db.session.add(user_b)
        db.session.commit()

        user_b_id = user_b.id
        expense_b_id = None

        try:

            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "userb@test.com",
                    "password": "pass"
                }
            )

            assert login_response.status_code == 200

            login_data = login_response.get_json()

            token_b = login_data["data"]["access_token"]

            headers_b = {
                "Authorization": f"Bearer {token_b}"
            }

            category = Category.query.filter_by(
                name="Food",
                type="expense"
            ).first()

            assert category is not None

            expense_response = client.post(
                "/api/expenses",
                headers=headers_b,
                json={
                    "amount": 777,
                    "category_id": category.id,
                    "date": str(date.today()),
                    "note": "User B private expense"
                }
            )

            assert expense_response.status_code == 201

            expense_b_id = (
                expense_response
                .get_json()
                ["data"]
                ["id"]
            )

            # User A requests expenses
            user_a_response = client.get(
                "/api/expenses",
                headers=auth_headers
            )

            assert user_a_response.status_code == 200

            user_a_data = user_a_response.get_json()

            user_a_ids = [
                item["id"]
                for item in user_a_data["data"]
                if isinstance(item, dict)
                and "id" in item
            ]

            assert expense_b_id not in user_a_ids

        finally:

            if expense_b_id is not None:

                expense = db.session.get(
                    Expense,
                    expense_b_id
                )

                if expense:
                    db.session.delete(expense)

            user = db.session.get(
                User,
                user_b_id
            )

            if user:
                db.session.delete(user)

            db.session.commit()

    def test_user_cannot_access_another_users_data_by_id(
        self,
        client,
        auth_headers,
        test_user,
        db
    ):
        """TC-INT-012: User A cannot modify User B's expense."""

        user_b = User(
            name="User C",
            email="userc@test.com",
            password_hash=bcrypt.generate_password_hash(
                "pass"
            ).decode("utf-8"),
            role="user",
            is_active=True
        )

        db.session.add(user_b)
        db.session.commit()

        user_b_id = user_b.id
        expense_b_id = None

        try:

            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "userc@test.com",
                    "password": "pass"
                }
            )

            assert login_response.status_code == 200

            token_b = (
                login_response
                .get_json()
                ["data"]
                ["access_token"]
            )

            headers_b = {
                "Authorization": f"Bearer {token_b}"
            }

            category = Category.query.filter_by(
                name="Food",
                type="expense"
            ).first()

            assert category is not None

            expense_response = client.post(
                "/api/expenses",
                headers=headers_b,
                json={
                    "amount": 999,
                    "category_id": category.id,
                    "date": str(date.today()),
                    "note": "Private expense"
                }
            )

            assert expense_response.status_code == 201

            expense_b_id = (
                expense_response
                .get_json()
                ["data"]
                ["id"]
            )

            # User A attempts DELETE
            delete_response = client.delete(
                f"/api/expenses/{expense_b_id}",
                headers=auth_headers
            )

            assert delete_response.status_code == 404

            # User A attempts UPDATE
            update_response = client.put(
                f"/api/expenses/{expense_b_id}",
                headers=auth_headers,
                json={
                    "amount": 9999
                }
            )

            assert update_response.status_code == 404

            # Make sure User B's expense still exists
            remaining_expense = db.session.get(
                Expense,
                expense_b_id
            )

            assert remaining_expense is not None
            assert float(
                remaining_expense.amount
            ) == 999.0

        finally:

            if expense_b_id is not None:

                expense = db.session.get(
                    Expense,
                    expense_b_id
                )

                if expense:
                    db.session.delete(expense)

            user = db.session.get(
                User,
                user_b_id
            )

            if user:
                db.session.delete(user)

            db.session.commit()