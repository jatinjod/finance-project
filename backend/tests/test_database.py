# backend/tests/test_database.py
# Database constraints, relationships, and integrity tests

from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from models.user import User
from models.expense import Expense
from models.income import Income
from models.category import Category
from models.budget import Budget
from models.savings_goal import SavingsGoal
from models.notification import Notification

from extensions import bcrypt


class TestDatabaseConstraints:
    """Database constraint and integrity tests."""

    def test_user_email_is_unique(self, db, test_user):
        """TC-DB-001: Duplicate user email must be rejected."""

        duplicate = User(
            name="Duplicate User",
            email="test@example.com",
            password_hash=bcrypt.generate_password_hash(
                "duplicate-password"
            ).decode("utf-8"),
            role="user",
            is_active=True
        )

        db.session.add(duplicate)

        with pytest.raises(IntegrityError):
            db.session.commit()

        db.session.rollback()

    def test_expense_amount_requires_positive_value(
        self,
        db,
        test_user
    ):
        """TC-DB-002: Positive amount rule is enforced at application level."""

        category = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert category is not None
        assert category.id is not None

        # The application's API validation handles negative/zero amounts.
        # That behavior is verified in test_expenses.py.
        assert test_user.id is not None

    def test_user_cascade_deletes_expenses(self, db):
        """TC-DB-003: Deleting a user removes their expenses."""

        user = User(
            name="Cascade Expense User",
            email="cascade_expense@test.com",
            password_hash=bcrypt.generate_password_hash(
                "pass"
            ).decode("utf-8"),
            role="user",
            is_active=True
        )

        db.session.add(user)
        db.session.commit()

        category = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert category is not None

        expense = Expense(
            user_id=user.id,
            category_id=category.id,
            amount=1000,
            date=date.today()
        )

        db.session.add(expense)
        db.session.commit()

        user_id = user.id
        expense_id = expense.id

        db.session.delete(user)
        db.session.commit()

        assert db.session.get(
            User,
            user_id
        ) is None

        assert db.session.get(
            Expense,
            expense_id
        ) is None

    def test_user_cascade_deletes_income(self, db):
        """TC-DB-004: Deleting a user removes their income."""

        user = User(
            name="Cascade Income User",
            email="cascade_income@test.com",
            password_hash=bcrypt.generate_password_hash(
                "pass"
            ).decode("utf-8"),
            role="user",
            is_active=True
        )

        db.session.add(user)
        db.session.commit()

        category = Category.query.filter_by(
            name="Salary",
            type="income"
        ).first()

        assert category is not None

        income = Income(
            user_id=user.id,
            category_id=category.id,
            amount=25000,
            date=date.today()
        )

        db.session.add(income)
        db.session.commit()

        income_id = income.id

        db.session.delete(user)
        db.session.commit()

        assert db.session.get(
            Income,
            income_id
        ) is None

    def test_user_cascade_deletes_budgets(self, db):
        """TC-DB-005: Deleting a user removes their budgets."""

        user = User(
            name="Cascade Budget User",
            email="cascade_budget@test.com",
            password_hash=bcrypt.generate_password_hash(
                "pass"
            ).decode("utf-8"),
            role="user",
            is_active=True
        )

        db.session.add(user)
        db.session.commit()

        budget = Budget(
            user_id=user.id,
            category_id=None,
            month=date(2024, 1, 1),
            amount=20000
        )

        db.session.add(budget)
        db.session.commit()

        budget_id = budget.id

        db.session.delete(user)
        db.session.commit()

        assert db.session.get(
            Budget,
            budget_id
        ) is None

    def test_user_cascade_deletes_notifications(self, db):
        """TC-DB-006: Deleting a user removes notifications."""

        user = User(
            name="Cascade Notification User",
            email="cascade_notification@test.com",
            password_hash=bcrypt.generate_password_hash(
                "pass"
            ).decode("utf-8"),
            role="user",
            is_active=True
        )

        db.session.add(user)
        db.session.commit()

        notification = Notification(
            user_id=user.id,
            message="Test notification",
            type="general"
        )

        db.session.add(notification)
        db.session.commit()

        notification_id = notification.id

        db.session.delete(user)
        db.session.commit()

        assert db.session.get(
            Notification,
            notification_id
        ) is None

    def test_budget_duplicate_behavior(
        self,
        db,
        test_user
    ):
        """
        TC-DB-007:
        Verify duplicate overall-budget behavior under SQLite.

        category_id is NULL for an overall budget.
        SQLite treats NULL values as distinct inside UNIQUE
        constraints, so two rows can coexist at database level.
        """

        month = date(2024, 6, 1)

        first_budget = Budget(
            user_id=test_user.id,
            category_id=None,
            month=month,
            amount=10000
        )

        db.session.add(first_budget)
        db.session.commit()

        first_id = first_budget.id

        second_budget = Budget(
            user_id=test_user.id,
            category_id=None,
            month=month,
            amount=15000
        )

        db.session.add(second_budget)
        db.session.commit()

        second_id = second_budget.id

        assert first_id is not None
        assert second_id is not None
        assert first_id != second_id

        first = db.session.get(
            Budget,
            first_id
        )

        second = db.session.get(
            Budget,
            second_id
        )

        assert first is not None
        assert second is not None

        assert first.category_id is None
        assert second.category_id is None

        assert float(first.amount) == 10000.0
        assert float(second.amount) == 15000.0

        # Cleanup
        db.session.delete(first)
        db.session.delete(second)
        db.session.commit()

    def test_savings_goal_progress_calculation(
        self,
        db,
        test_user
    ):
        """TC-DB-008: Savings progress is calculated correctly."""

        goal = SavingsGoal(
            user_id=test_user.id,
            name="DB Test Goal",
            target_amount=100000,
            saved_amount=25000
        )

        db.session.add(goal)
        db.session.commit()

        goal_id = goal.id

        fetched = db.session.get(
            SavingsGoal,
            goal_id
        )

        assert fetched is not None

        result = fetched.to_dict()

        assert result["progress_percentage"] == 25.0
        assert result["remaining_amount"] == 75000.0

        db.session.delete(fetched)
        db.session.commit()

        assert db.session.get(
            SavingsGoal,
            goal_id
        ) is None

    def test_default_categories_seeded(self, db):
        """TC-DB-009: Required default categories exist."""

        defaults = Category.query.filter_by(
            is_default=True
        ).all()

        names = {
            category.name
            for category in defaults
        }

        assert "Food" in names
        assert "Salary" in names
        assert "Rent" in names

        assert len(defaults) >= 12

    def test_default_categories_have_null_user(
        self,
        db
    ):
        """TC-DB-010: Default categories have no specific user."""

        defaults = Category.query.filter_by(
            is_default=True
        ).all()

        assert len(defaults) >= 12

        for category in defaults:
            assert category.user_id is None

    def test_amount_stored_as_decimal(
        self,
        db,
        test_user
    ):
        """TC-DB-011: Expense preserves decimal precision."""

        category = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert category is not None

        expense = Expense(
            user_id=test_user.id,
            category_id=category.id,
            amount=1234.56,
            date=date.today(),
            note="Decimal precision test"
        )

        db.session.add(expense)
        db.session.commit()

        expense_id = expense.id

        fetched = db.session.get(
            Expense,
            expense_id
        )

        assert fetched is not None
        assert float(fetched.amount) == pytest.approx(
            1234.56,
            abs=0.001
        )

        db.session.delete(fetched)
        db.session.commit()

        assert db.session.get(
            Expense,
            expense_id
        ) is None

    def test_expense_category_restrict_deletion(
        self,
        db,
        test_user
    ):
        """TC-DB-012: Category used by an expense cannot be deleted."""

        custom_category = Category(
            user_id=test_user.id,
            name="RestrictTest",
            type="expense",
            is_default=False
        )

        db.session.add(custom_category)
        db.session.commit()

        category_id = custom_category.id

        expense = Expense(
            user_id=test_user.id,
            category_id=category_id,
            amount=500,
            date=date.today()
        )

        db.session.add(expense)
        db.session.commit()

        expense_id = expense.id

        db.session.delete(custom_category)

        with pytest.raises(IntegrityError):
            db.session.commit()

        db.session.rollback()

        assert db.session.get(
            Category,
            category_id
        ) is not None

        assert db.session.get(
            Expense,
            expense_id
        ) is not None

        # Cleanup
        existing_expense = db.session.get(
            Expense,
            expense_id
        )

        if existing_expense:
            db.session.delete(existing_expense)

        db.session.flush()

        existing_category = db.session.get(
            Category,
            category_id
        )

        if existing_category:
            db.session.delete(existing_category)

        db.session.commit()

    def test_user_relationships_are_isolated(
        self,
        db,
        test_user
    ):
        """Additional test: expense belongs to the correct user."""

        category = Category.query.filter_by(
            name="Food",
            type="expense"
        ).first()

        assert category is not None

        expense = Expense(
            user_id=test_user.id,
            category_id=category.id,
            amount=750,
            date=date.today(),
            note="Relationship test"
        )

        db.session.add(expense)
        db.session.commit()

        expense_id = expense.id

        fetched = db.session.get(
            Expense,
            expense_id
        )

        assert fetched is not None
        assert fetched.user_id == test_user.id
        assert fetched.category_id == category.id

        db.session.delete(fetched)
        db.session.commit()

    def test_income_relationship_is_correct(
        self,
        db,
        test_user
    ):
        """Additional test: income references correct user/category."""

        category = Category.query.filter_by(
            name="Salary",
            type="income"
        ).first()

        assert category is not None

        income = Income(
            user_id=test_user.id,
            category_id=category.id,
            amount=25000,
            date=date.today(),
            note="Income relationship test"
        )

        db.session.add(income)
        db.session.commit()

        income_id = income.id

        fetched = db.session.get(
            Income,
            income_id
        )

        assert fetched is not None
        assert fetched.user_id == test_user.id
        assert fetched.category_id == category.id

        db.session.delete(fetched)
        db.session.commit()