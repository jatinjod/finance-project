# backend/tests/test_auth.py
# Unit tests for authentication module

import pytest
from models.user import User


class TestUserRegistration:
    """Registration test cases."""

    def test_register_valid_user(self, client, db):
        """TC-AUTH-001: Valid registration → 201."""

        response = client.post(
            "/api/auth/register",
            json={
                "name": "John Doe",
                "email": "john@test.com",
                "password": "password123",
            },
        )

        assert response.status_code == 201

        data = response.get_json()

        assert data is not None
        assert data.get("status") == "success"
        assert isinstance(data.get("data"), dict)
        assert "user_id" in data["data"]

        # Cleanup
        user = User.query.filter_by(
            email="john@test.com"
        ).first()

        if user:
            db.session.delete(user)
            db.session.commit()


    def test_register_missing_name(self, client):
        """TC-AUTH-002: Missing name → 400."""

        response = client.post(
            "/api/auth/register",
            json={
                "email": "noname@test.com",
                "password": "password123",
            },
        )

        assert response.status_code == 400

        data = response.get_json()

        assert data is not None
        assert "error" in data


    def test_register_missing_email(self, client):
        """TC-AUTH-003: Missing email → 400."""

        response = client.post(
            "/api/auth/register",
            json={
                "name": "Test",
                "password": "password123",
            },
        )

        assert response.status_code == 400


    def test_register_invalid_email_format(self, client):
        """TC-AUTH-004: Invalid email format → 400."""

        response = client.post(
            "/api/auth/register",
            json={
                "name": "Test User",
                "email": "not-an-email",
                "password": "password123",
            },
        )

        assert response.status_code == 400


    def test_register_short_password(self, client):
        """TC-AUTH-005: Password shorter than minimum → 400."""

        response = client.post(
            "/api/auth/register",
            json={
                "name": "Test User",
                "email": "short@test.com",
                "password": "123",
            },
        )

        assert response.status_code == 400


    def test_register_duplicate_email(self, client, test_user):
        """TC-AUTH-006: Duplicate email → 409."""

        response = client.post(
            "/api/auth/register",
            json={
                "name": "Duplicate User",
                "email": "test@example.com",
                "password": "password123",
            },
        )

        assert response.status_code == 409


    def test_register_password_is_hashed(self, client, db):
        """TC-AUTH-007: Password is stored hashed."""

        response = client.post(
            "/api/auth/register",
            json={
                "name": "Hash Test",
                "email": "hash@test.com",
                "password": "myplainpassword",
            },
        )

        assert response.status_code == 201

        user = User.query.filter_by(
            email="hash@test.com"
        ).first()

        assert user is not None
        assert user.password_hash != "myplainpassword"
        assert len(user.password_hash) > 20

        # Cleanup
        db.session.delete(user)
        db.session.commit()


    def test_register_empty_body(self, client):
        """TC-AUTH-008: Empty request body → 400."""

        response = client.post(
            "/api/auth/register",
            data="",
            content_type="application/json",
        )

        assert response.status_code == 400


    def test_register_short_name(self, client):
        """TC-AUTH-009: One-character name → 400."""

        response = client.post(
            "/api/auth/register",
            json={
                "name": "A",
                "email": "singlechar@test.com",
                "password": "password123",
            },
        )

        assert response.status_code == 400


class TestUserLogin:
    """Login and JWT authentication test cases."""

    def test_login_valid_credentials(self, client, test_user):
        """TC-AUTH-010: Valid credentials → 200 + JWT token."""

        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "password123",
            },
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data is not None
        assert data.get("status") == "success"
        assert isinstance(data.get("data"), dict)
        assert "access_token" in data["data"]
        assert "user" in data["data"]

        assert data["data"]["access_token"]
        assert isinstance(data["data"]["access_token"], str)


    def test_login_wrong_password(self, client, test_user):
        """TC-AUTH-011: Wrong password → 401."""

        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401


    def test_login_wrong_email(self, client):
        """TC-AUTH-012: Unknown email → 401."""

        response = client.post(
            "/api/auth/login",
            json={
                "email": "nobody@nowhere.com",
                "password": "password123",
            },
        )

        assert response.status_code == 401


    def test_login_missing_email(self, client):
        """TC-AUTH-013: Missing email → 400."""

        response = client.post(
            "/api/auth/login",
            json={
                "password": "password123",
            },
        )

        assert response.status_code == 400


    def test_login_missing_password(self, client):
        """Additional auth validation: missing password → 400."""

        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
            },
        )

        assert response.status_code == 400


    def test_login_empty_body(self, client):
        """Additional auth validation: empty body → 400."""

        response = client.post(
            "/api/auth/login",
            data="",
            content_type="application/json",
        )

        assert response.status_code == 400


    def test_login_returns_correct_user_data(self, client, test_user):
        """TC-AUTH-014: Login response contains correct user data."""

        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "password123",
            },
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data is not None
        assert data.get("status") == "success"

        user = data["data"]["user"]

        assert user["email"] == "test@example.com"
        assert user["name"] == "Test User"
        assert user["role"] == "user"


    def test_login_deactivated_account(self, client, db, test_user):
        """TC-AUTH-015: Deactivated account → 403."""

        test_user.is_active = False
        db.session.commit()

        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "password123",
            },
        )

        assert response.status_code == 403

        # Restore fixture state
        test_user.is_active = True
        db.session.commit()


    def test_logout_requires_token(self, client):
        """TC-AUTH-016: Logout without token → 401."""

        response = client.post(
            "/api/auth/logout"
        )

        assert response.status_code == 401


    def test_logout_with_valid_token(self, client, auth_headers):
        """TC-AUTH-017: Logout with valid token → 200."""

        response = client.post(
            "/api/auth/logout",
            headers=auth_headers,
        )

        assert response.status_code == 200


    def test_protected_route_without_token(self, client):
        """TC-AUTH-018: Protected route without JWT → 401."""

        response = client.get(
            "/api/user/profile"
        )

        assert response.status_code == 401


    def test_protected_route_with_token(self, client, auth_headers):
        """TC-AUTH-019: Protected route with valid JWT → 200."""

        response = client.get(
            "/api/user/profile",
            headers=auth_headers,
        )

        assert response.status_code == 200


    def test_invalid_token_rejected(self, client):
        """Additional JWT test: invalid token → 401."""

        response = client.get(
            "/api/user/profile",
            headers={
                "Authorization": "Bearer invalid.token.value"
            },
        )

        assert response.status_code == 401