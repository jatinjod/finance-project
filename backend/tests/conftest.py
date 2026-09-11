# backend/tests/conftest.py
# Shared pytest fixtures and isolated test database

import pytest
from datetime import date

from app import create_app
from extensions import db as _db, bcrypt

from models.user import User
from models.category import Category
from models.income import Income
from models.expense import Expense
from models.budget import Budget
from models.savings_goal import SavingsGoal


@pytest.fixture(scope="session")
def app():
    """
    Create a completely isolated Flask test application.

    IMPORTANT:
    Uses an in-memory SQLite database instead of the real MySQL
    financeai database.
    """

    test_app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "test-jwt-secret-key-for-pytest-123456",
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })

    with test_app.app_context():

        # Create test database tables
        _db.create_all()

        # Seed test-only categories
        _seed_test_categories()

        yield test_app

        # Cleanup test database
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def db(app):
    """
    Provide database access to each test.

    Every test gets the same isolated test database session,
    and pending changes are rolled back after the test.
    """

    with app.app_context():
        yield _db
        _db.session.rollback()


@pytest.fixture(scope="function")
def client(app):
    """Flask test client for HTTP requests."""
    return app.test_client()


@pytest.fixture(scope="function")
def test_user(db):
    """Create a normal test user."""

    user = User(
        name="Test User",
        email="test@example.com",
        password_hash=bcrypt.generate_password_hash(
            "password123"
        ).decode("utf-8"),
        role="user",
        is_active=True
    )

    db.session.add(user)
    db.session.commit()

    yield user

    # Cleanup
    existing_user = db.session.get(
        User,
        user.id
    )

    if existing_user:
        db.session.delete(existing_user)
        db.session.commit()


@pytest.fixture(scope="function")
def test_admin(db):
    """Create a test admin user."""

    admin = User(
        name="Admin User",
        email="admin@example.com",
        password_hash=bcrypt.generate_password_hash(
            "admin123"
        ).decode("utf-8"),
        role="admin",
        is_active=True
    )

    db.session.add(admin)
    db.session.commit()

    yield admin

    # Cleanup
    existing_admin = db.session.get(
        User,
        admin.id
    )

    if existing_admin:
        db.session.delete(existing_admin)
        db.session.commit()


@pytest.fixture(scope="function")
def user_token(client, test_user):
    """Generate JWT token for the normal test user."""

    response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "password123"
        }
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data is not None
    assert data.get("data") is not None
    assert data["data"].get("access_token")

    return data["data"]["access_token"]


@pytest.fixture(scope="function")
def admin_token(client, test_admin):
    """Generate JWT token for the test admin."""

    response = client.post(
        "/api/auth/login",
        json={
            "email": "admin@example.com",
            "password": "admin123"
        }
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data is not None
    assert data.get("data") is not None
    assert data["data"].get("access_token")

    return data["data"]["access_token"]


@pytest.fixture(scope="function")
def auth_headers(user_token):
    """Authorization headers for normal test user."""

    return {
        "Authorization": f"Bearer {user_token}"
    }


@pytest.fixture(scope="function")
def admin_headers(admin_token):
    """Authorization headers for admin test user."""

    return {
        "Authorization": f"Bearer {admin_token}"
    }


@pytest.fixture(scope="function")
def sample_expense(db, test_user):
    """Create a sample expense for the normal test user."""

    food_category = Category.query.filter_by(
        name="Food",
        type="expense",
        user_id=None
    ).first()

    assert food_category is not None

    expense = Expense(
        user_id=test_user.id,
        category_id=food_category.id,
        amount=1500.00,
        date=date.today(),
        note="Test grocery expense"
    )

    db.session.add(expense)
    db.session.commit()

    yield expense

    # Cleanup
    existing_expense = db.session.get(
        Expense,
        expense.id
    )

    if existing_expense:
        db.session.delete(existing_expense)
        db.session.commit()


@pytest.fixture(scope="function")
def sample_income(db, test_user):
    """Create a sample income for the normal test user."""

    salary_category = Category.query.filter_by(
        name="Salary",
        type="income",
        user_id=None
    ).first()

    assert salary_category is not None

    income = Income(
        user_id=test_user.id,
        category_id=salary_category.id,
        amount=25000.00,
        date=date.today(),
        note="Monthly salary"
    )

    db.session.add(income)
    db.session.commit()

    yield income

    # Cleanup
    existing_income = db.session.get(
        Income,
        income.id
    )

    if existing_income:
        db.session.delete(existing_income)
        db.session.commit()


def _seed_test_categories():
    """
    Seed only the categories needed by the tests.

    These are stored only in the SQLite test database.
    They do NOT affect your real MySQL database.
    """

    categories = [
        ("Salary", "income"),
        ("Freelance", "income"),
        ("Business", "income"),
        ("Investment", "income"),
        ("Gift", "income"),

        ("Food", "expense"),
        ("Transport", "expense"),
        ("Rent", "expense"),
        ("Utilities", "expense"),
        ("Entertainment", "expense"),
        ("Shopping", "expense"),
        ("Healthcare", "expense"),
        ("Education", "expense"),
        ("Travel", "expense"),
        ("Other", "expense"),
    ]

    for name, category_type in categories:

        existing = Category.query.filter_by(
            name=name,
            type=category_type,
            user_id=None
        ).first()

        if existing:
            continue

        category = Category(
            user_id=None,
            name=name,
            type=category_type,
            is_default=True
        )

        _db.session.add(category)

    _db.session.commit()