# backend/tests/test_savings.py
# Unit tests for savings goals module

from datetime import date, timedelta

import pytest

from models.savings_goal import SavingsGoal


class TestSavingsGoals:
    """Savings goal management tests."""

    def test_create_savings_goal(
        self,
        client,
        auth_headers,
        db
    ):
        """TC-SAV-001: Create valid savings goal → 201."""

        deadline = str(
            date.today() + timedelta(days=180)
        )

        response = client.post(
            "/api/savings",
            headers=auth_headers,
            json={
                "name": "Buy Laptop",
                "target_amount": 60000,
                "saved_amount": 10000,
                "deadline": deadline
            }
        )

        assert response.status_code == 201

        data = response.get_json()

        assert data is not None
        assert data.get("status") == "success"
        assert isinstance(data.get("data"), dict)

        assert data["data"]["name"] == "Buy Laptop"
        assert float(
            data["data"]["target_amount"]
        ) == 60000.0

        assert float(
            data["data"]["saved_amount"]
        ) == 10000.0

        assert data["data"]["progress_percentage"] == pytest.approx(
            16.67,
            abs=0.1
        )

        assert "id" in data["data"]

        # Cleanup
        goal = db.session.get(
            SavingsGoal,
            data["data"]["id"]
        )

        if goal:
            db.session.delete(goal)
            db.session.commit()

    def test_create_goal_zero_target(
        self,
        client,
        auth_headers
    ):
        """TC-SAV-002: Zero target amount → 400."""

        response = client.post(
            "/api/savings",
            headers=auth_headers,
            json={
                "name": "Invalid Goal",
                "target_amount": 0
            }
        )

        assert response.status_code == 400

        data = response.get_json()

        assert data is not None
        assert "error" in data

    def test_create_goal_negative_saved(
        self,
        client,
        auth_headers
    ):
        """TC-SAV-003: Negative saved amount → 400."""

        response = client.post(
            "/api/savings",
            headers=auth_headers,
            json={
                "name": "Negative Saved",
                "target_amount": 10000,
                "saved_amount": -500
            }
        )

        assert response.status_code == 400

        data = response.get_json()

        assert data is not None
        assert "error" in data

    def test_get_savings_goals(
        self,
        client,
        auth_headers,
        db,
        test_user
    ):
        """TC-SAV-004: Get savings goals list → 200."""

        goal = SavingsGoal(
            user_id=test_user.id,
            name="Test Goal",
            target_amount=50000,
            saved_amount=10000
        )

        db.session.add(goal)
        db.session.commit()

        goal_id = goal.id

        try:
            response = client.get(
                "/api/savings",
                headers=auth_headers
            )

            assert response.status_code == 200

            data = response.get_json()

            assert data is not None
            assert isinstance(data.get("data"), list)
            assert len(data["data"]) >= 1

            found = any(
                item.get("id") == goal_id
                for item in data["data"]
                if isinstance(item, dict)
            )

            assert found is True

        finally:
            existing_goal = db.session.get(
                SavingsGoal,
                goal_id
            )

            if existing_goal:
                db.session.delete(existing_goal)
                db.session.commit()

    def test_update_savings_progress(
        self,
        client,
        auth_headers,
        db,
        test_user
    ):
        """TC-SAV-005: Update saved amount → progress recalculated."""

        goal = SavingsGoal(
            user_id=test_user.id,
            name="Progress Test",
            target_amount=100000,
            saved_amount=20000
        )

        db.session.add(goal)
        db.session.commit()

        goal_id = goal.id

        try:
            response = client.put(
                f"/api/savings/{goal_id}",
                headers=auth_headers,
                json={
                    "saved_amount": 50000
                }
            )

            assert response.status_code == 200

            data = response.get_json()

            assert data is not None
            assert data.get("status") == "success"
            assert isinstance(data.get("data"), dict)

            assert float(
                data["data"]["saved_amount"]
            ) == 50000.0

            assert data["data"]["progress_percentage"] == pytest.approx(
                50.0,
                abs=0.01
            )

        finally:
            existing_goal = db.session.get(
                SavingsGoal,
                goal_id
            )

            if existing_goal:
                db.session.delete(existing_goal)
                db.session.commit()

    def test_goal_auto_complete(
        self,
        client,
        auth_headers,
        db,
        test_user
    ):
        """TC-SAV-006: Goal auto-completes when saved >= target."""

        goal = SavingsGoal(
            user_id=test_user.id,
            name="Auto Complete",
            target_amount=50000,
            saved_amount=49000
        )

        db.session.add(goal)
        db.session.commit()

        goal_id = goal.id

        try:
            response = client.put(
                f"/api/savings/{goal_id}",
                headers=auth_headers,
                json={
                    "saved_amount": 50000
                }
            )

            assert response.status_code == 200

            data = response.get_json()

            assert data is not None
            assert data.get("status") == "success"
            assert isinstance(data.get("data"), dict)

            assert data["data"]["is_complete"] is True
            assert data["data"]["progress_percentage"] >= 100

        finally:
            existing_goal = db.session.get(
                SavingsGoal,
                goal_id
            )

            if existing_goal:
                db.session.delete(existing_goal)
                db.session.commit()

    def test_delete_savings_goal(
        self,
        client,
        auth_headers,
        db,
        test_user
    ):
        """TC-SAV-007: Delete savings goal → 200 and removed."""

        goal = SavingsGoal(
            user_id=test_user.id,
            name="To Delete",
            target_amount=30000,
            saved_amount=0
        )

        db.session.add(goal)
        db.session.commit()

        goal_id = goal.id

        response = client.delete(
            f"/api/savings/{goal_id}",
            headers=auth_headers
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data is not None
        assert data.get("status") == "success"

        deleted_goal = db.session.get(
            SavingsGoal,
            goal_id
        )

        assert deleted_goal is None

    def test_get_savings_requires_auth(
        self,
        client
    ):
        """Additional security test: Savings endpoint without JWT → 401."""

        response = client.get(
            "/api/savings"
        )

        assert response.status_code == 401

    def test_create_savings_requires_auth(
        self,
        client
    ):
        """Additional security test: Create goal without JWT → 401."""

        response = client.post(
            "/api/savings",
            json={
                "name": "Unauthorized Goal",
                "target_amount": 10000
            }
        )

        assert response.status_code == 401

    def test_delete_nonexistent_savings_goal(
        self,
        client,
        auth_headers
    ):
        """Additional test: Delete nonexistent goal → 404."""

        response = client.delete(
            "/api/savings/99999",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_update_nonexistent_savings_goal(
        self,
        client,
        auth_headers
    ):
        """Additional test: Update nonexistent goal → 404."""

        response = client.put(
            "/api/savings/99999",
            headers=auth_headers,
            json={
                "saved_amount": 5000
            }
        )

        assert response.status_code == 404