# backend/seed_sample_data.py
# Populates the database with realistic sample data for testing
# Run: python seed_sample_data.py

from datetime import date, timedelta
import random

from app import create_app, init_db
from extensions import db, bcrypt
from models.user import User
from models.category import Category
from models.income import Income
from models.expense import Expense
from models.budget import Budget
from models.savings_goal import SavingsGoal
from models.notification import Notification


def seed_sample_data():
    app = create_app()

    with app.app_context():
        # Initialize DB and default categories first
        init_db(app)

        print("\n🌱 Seeding sample data...")

        # ── Create/Get Sample Users ─────────────
        # Existing users are preserved.
        # These dedicated users are only for integration testing.

        user1 = User.query.filter_by(
            email="integration_test_user@example.com"
        ).first()

        if not user1:
            user1 = User(
                name="Integration Test User",
                email="integration_test_user@example.com",
                password_hash=bcrypt.generate_password_hash(
                    "password123"
                ).decode("utf-8"),
                role="user"
            )
            db.session.add(user1)

        user2 = User.query.filter_by(
            email="isolation_test_user@example.com"
        ).first()

        if not user2:
            user2 = User(
                name="Isolation Test User",
                email="isolation_test_user@example.com",
                password_hash=bcrypt.generate_password_hash(
                    "password123"
                ).decode("utf-8"),
                role="user"
            )
            db.session.add(user2)

        db.session.commit()

        print("   ✅ Integration test users ready")

        user_id = user1.id

        # ── Get Category IDs ───────────────────
        salary_cat = Category.query.filter_by(
            name="Salary"
        ).first()

        freelance_cat = Category.query.filter_by(
            name="Freelance"
        ).first()

        food_cat = Category.query.filter_by(
            name="Food"
        ).first()

        transport_cat = Category.query.filter_by(
            name="Transport"
        ).first()

        rent_cat = Category.query.filter_by(
            name="Rent"
        ).first()

        shopping_cat = Category.query.filter_by(
            name="Shopping"
        ).first()

        entertain_cat = Category.query.filter_by(
            name="Entertainment"
        ).first()

        health_cat = Category.query.filter_by(
            name="Healthcare"
        ).first()

        utilities_cat = Category.query.filter_by(
            name="Utilities"
        ).first()

        # ── Create 6 Months of Income ──────────
        income_records = []
        today = date.today()

        for i in range(6, 0, -1):

            m = today.month - i
            y = today.year

            while m <= 0:
                m += 12
                y -= 1

            month_start = date(y, m, 1)

            income_records.append(
                Income(
                    user_id=user_id,
                    category_id=salary_cat.id,
                    amount=25000.00,
                    date=month_start,
                    note="Monthly salary"
                )
            )

            # Freelance income some months
            if i % 2 == 0:
                income_records.append(
                    Income(
                        user_id=user_id,
                        category_id=freelance_cat.id,
                        amount=round(
                            random.uniform(4000, 9000),
                            2
                        ),
                        date=date(y, m, 15),
                        note="Freelance project payment"
                    )
                )

        db.session.add_all(income_records)
        db.session.commit()

        print("   ✅ Income records created")

        # ── Create 6 Months of Expenses ────────
        expense_records = []

        expense_templates = [
            (
                rent_cat.id,
                12000.00,
                12000.00,
                "Monthly rent",
                1
            ),
            (
                food_cat.id,
                3500.00,
                6000.00,
                "Grocery and food",
                5
            ),
            (
                transport_cat.id,
                1200.00,
                1800.00,
                "Transport",
                6
            ),
            (
                utilities_cat.id,
                1000.00,
                1500.00,
                "Utilities bill",
                10
            ),
            (
                food_cat.id,
                500.00,
                1500.00,
                "Eating out",
                14
            ),
            (
                entertain_cat.id,
                500.00,
                1200.00,
                "Entertainment",
                20
            ),
            (
                shopping_cat.id,
                1000.00,
                4000.00,
                "Shopping",
                25
            ),
            (
                health_cat.id,
                0,
                2000.00,
                "Healthcare",
                12
            ),
        ]

        for i in range(6, 0, -1):

            m = today.month - i
            y = today.year

            while m <= 0:
                m += 12
                y -= 1

            for (
                cat_id,
                min_amt,
                max_amt,
                note,
                day
            ) in expense_templates:

                # Skip healthcare some months
                if (
                    cat_id == health_cat.id
                    and random.random() > 0.4
                ):
                    continue

                amount = round(
                    random.uniform(
                        min_amt,
                        max_amt
                    ),
                    2
                )

                expense_records.append(
                    Expense(
                        user_id=user_id,
                        category_id=cat_id,
                        amount=amount,
                        date=date(
                            y,
                            m,
                            min(day, 28)
                        ),
                        note=note
                    )
                )

        db.session.add_all(expense_records)
        db.session.commit()

        print("   ✅ Expense records created")

        # ── Create Budgets for Current Month ───
        first_of_month = date(
            today.year,
            today.month,
            1
        )

        budgets = [
            Budget(
                user_id=user_id,
                category_id=None,
                month=first_of_month,
                amount=22000.00
            ),
            Budget(
                user_id=user_id,
                category_id=food_cat.id,
                month=first_of_month,
                amount=6000.00
            ),
            Budget(
                user_id=user_id,
                category_id=transport_cat.id,
                month=first_of_month,
                amount=2000.00
            ),
            Budget(
                user_id=user_id,
                category_id=rent_cat.id,
                month=first_of_month,
                amount=12000.00
            ),
            Budget(
                user_id=user_id,
                category_id=shopping_cat.id,
                month=first_of_month,
                amount=3000.00
            ),
            Budget(
                user_id=user_id,
                category_id=entertain_cat.id,
                month=first_of_month,
                amount=1500.00
            ),
        ]

        db.session.add_all(budgets)
        db.session.commit()

        print("   ✅ Budgets created")

        # ── Create Savings Goals ───────────────
        goals = [
            SavingsGoal(
                user_id=user_id,
                name="Buy a Laptop",
                target_amount=60000.00,
                saved_amount=18000.00,
                deadline=date(
                    today.year,
                    12,
                    31
                ),
                is_complete=False
            ),
            SavingsGoal(
                user_id=user_id,
                name="Emergency Fund",
                target_amount=100000.00,
                saved_amount=35000.00,
                deadline=None,
                is_complete=False
            ),
            SavingsGoal(
                user_id=user_id,
                name="Vacation Trip",
                target_amount=30000.00,
                saved_amount=30000.00,
                deadline=date(
                    today.year,
                    6,
                    30
                ),
                is_complete=True
            ),
        ]

        db.session.add_all(goals)
        db.session.commit()

        print("   ✅ Savings goals created")

        # ── Create Sample Notifications ────────
        notifications = [
            Notification(
                user_id=user_id,
                message=(
                    "Your Food budget has reached 80%. "
                    "Spent ₹4,800 of ₹6,000."
                ),
                type="budget_warning",
                is_read=False
            ),
            Notification(
                user_id=user_id,
                message=(
                    "Unusual transaction: ₹4,000 "
                    "in Shopping detected."
                ),
                type="anomaly",
                is_read=False
            ),
            Notification(
                user_id=user_id,
                message=(
                    "🎉 Congratulations! You completed "
                    "your Vacation Trip goal!"
                ),
                type="goal_achieved",
                is_read=True
            ),
        ]

        db.session.add_all(notifications)
        db.session.commit()

        print("   ✅ Notifications created")

        print("\n✅ Sample data seeded successfully!")

        print("\n📋 Test Credentials:")
        print(
            "   Integration User : "
            "integration_test_user@example.com / password123"
        )
        print(
            "   Isolation User   : "
            "isolation_test_user@example.com / password123"
        )
        print(
            "   Admin            : "
            "admin@finance.com / admin123"
        )


if __name__ == "__main__":
    seed_sample_data()