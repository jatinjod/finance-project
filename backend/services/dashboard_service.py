# backend/services/dashboard_service.py
# Aggregates all data needed for the main dashboard

from datetime import date

from sqlalchemy import func

from extensions import db
from models.income import Income
from models.expense import Expense
from models.notification import Notification
from models.savings_goal import SavingsGoal
from models.category import Category


def get_dashboard_summary(user_id):
    """Return complete dashboard data for one user."""

    today = date.today()
    month = today.month
    year = today.year

    # ─────────────────────────────────────────
    # MONTHLY TOTALS
    # ─────────────────────────────────────────
    monthly_income = (
        db.session.query(func.sum(Income.amount))
        .filter(
            Income.user_id == user_id,
            db.extract("month", Income.date) == month,
            db.extract("year", Income.date) == year
        )
        .scalar()
        or 0
    )

    monthly_expenses = (
        db.session.query(func.sum(Expense.amount))
        .filter(
            Expense.user_id == user_id,
            db.extract("month", Expense.date) == month,
            db.extract("year", Expense.date) == year
        )
        .scalar()
        or 0
    )

    monthly_income = round(float(monthly_income), 2)
    monthly_expenses = round(float(monthly_expenses), 2)
    balance = round(monthly_income - monthly_expenses, 2)

    # ─────────────────────────────────────────
    # BUDGET STATUS
    # ─────────────────────────────────────────
    from services.budget_service import get_budget_status

    budget_status = get_budget_status(
        user_id,
        year,
        month
    )

    # ─────────────────────────────────────────
    # RECENT 5 TRANSACTIONS
    # ─────────────────────────────────────────
    recent_income = (
        Income.query
        .filter_by(user_id=user_id)
        .order_by(
            Income.date.desc(),
            Income.created_at.desc(),
            Income.id.desc()
        )
        .limit(5)
        .all()
    )

    recent_expenses = (
        Expense.query
        .filter_by(user_id=user_id)
        .order_by(
            Expense.date.desc(),
            Expense.created_at.desc(),
            Expense.id.desc()
        )
        .limit(5)
        .all()
    )

    recent_transactions = []

    for income in recent_income:
        transaction = income.to_dict()
        transaction["transaction_type"] = "income"
        recent_transactions.append(transaction)

    for expense in recent_expenses:
        transaction = expense.to_dict()
        transaction["transaction_type"] = "expense"
        recent_transactions.append(transaction)

    recent_transactions.sort(
        key=lambda item: (
            item.get("date") or "",
            item.get("created_at") or "",
            item.get("id") or 0
        ),
        reverse=True
    )

    recent_transactions = recent_transactions[:5]

    # ─────────────────────────────────────────
    # CATEGORY PIE CHART
    # ─────────────────────────────────────────
    category_expenses = (
        db.session.query(
            Expense.category_id,
            func.sum(Expense.amount).label("total")
        )
        .filter(
            Expense.user_id == user_id,
            db.extract("month", Expense.date) == month,
            db.extract("year", Expense.date) == year
        )
        .group_by(Expense.category_id)
        .all()
    )

    category_chart = []

    for category_id, total in category_expenses:
        category = db.session.get(Category, category_id)

        category_chart.append({
            "category": category.name if category else "Unknown",
            "amount": round(float(total or 0), 2)
        })

    category_chart.sort(
        key=lambda item: item["amount"],
        reverse=True
    )

    # ─────────────────────────────────────────
    # MONTHLY CHART — LAST 6 MONTHS
    # ─────────────────────────────────────────
    monthly_chart = []

    month_names = [
        "Jan", "Feb", "Mar", "Apr",
        "May", "Jun", "Jul", "Aug",
        "Sep", "Oct", "Nov", "Dec"
    ]

    for offset in range(5, -1, -1):
        target_month = today.month - offset
        target_year = today.year

        while target_month <= 0:
            target_month += 12
            target_year -= 1

        month_income = (
            db.session.query(func.sum(Income.amount))
            .filter(
                Income.user_id == user_id,
                db.extract("month", Income.date) == target_month,
                db.extract("year", Income.date) == target_year
            )
            .scalar()
            or 0
        )

        month_expense = (
            db.session.query(func.sum(Expense.amount))
            .filter(
                Expense.user_id == user_id,
                db.extract("month", Expense.date) == target_month,
                db.extract("year", Expense.date) == target_year
            )
            .scalar()
            or 0
        )

        monthly_chart.append({
            "month": f"{month_names[target_month - 1]} {target_year}",
            "income": round(float(month_income), 2),
            "expenses": round(float(month_expense), 2)
        })

    # ─────────────────────────────────────────
    # ACTIVE SAVINGS GOALS
    # ─────────────────────────────────────────
    active_goals = (
        SavingsGoal.query
        .filter_by(
            user_id=user_id,
            is_complete=False
        )
        .order_by(SavingsGoal.created_at.desc())
        .limit(3)
        .all()
    )

    # ─────────────────────────────────────────
    # UNREAD NOTIFICATIONS
    # ─────────────────────────────────────────
    unread_count = (
        Notification.query
        .filter_by(
            user_id=user_id,
            is_read=False
        )
        .count()
    )

    # ─────────────────────────────────────────
    # FINAL RESPONSE
    # ─────────────────────────────────────────
    return {
        "summary": {
            "total_income": monthly_income,
            "total_expenses": monthly_expenses,
            "balance": balance,
            "month": month,
            "year": year
        },
        "budget_status": budget_status,
        "recent_transactions": recent_transactions,
        "category_chart": category_chart,
        "monthly_chart": monthly_chart,
        "active_goals": [
            goal.to_dict()
            for goal in active_goals
        ],
        "unread_notifications": unread_count
    }