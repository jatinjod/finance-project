# backend/services/budget_service.py
# Budget calculation logic and notification trigger

from datetime import date, timedelta

from extensions import db
from models.budget import Budget
from models.expense import Expense
from models.notification import Notification
from models.category import Category


def get_month_date_range(year, month):
    """
    Return the first date of the month and the first date
    of the next month.

    Using a date range avoids database-specific EXTRACT
    behavior and works reliably with MySQL.
    """
    year = int(year)
    month = int(month)

    first_day = date(year, month, 1)

    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)

    return first_day, next_month


def get_total_expenses_for_month(user_id, year, month):
    """Return total expenses for a user in a given month."""

    first_day, next_month = get_month_date_range(
        year,
        month
    )

    result = (
        db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0))
        .filter(
            Expense.user_id == user_id,
            Expense.date >= first_day,
            Expense.date < next_month
        )
        .scalar()
    )

    return round(float(result or 0), 2)


def get_category_expenses_for_month(
    user_id,
    category_id,
    year,
    month
):
    """Return category-specific expenses for a user/month."""

    first_day, next_month = get_month_date_range(
        year,
        month
    )

    result = (
        db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0))
        .filter(
            Expense.user_id == user_id,
            Expense.category_id == category_id,
            Expense.date >= first_day,
            Expense.date < next_month
        )
        .scalar()
    )

    return round(float(result or 0), 2)


def _send_notification_if_not_exists(
    user_id,
    message,
    notif_type,
    category_name
):
    """Create notification if a similar unread notification does not exist."""

    existing = (
        Notification.query
        .filter(
            Notification.user_id == user_id,
            Notification.type == notif_type,
            Notification.is_read.is_(False),
            Notification.message.like(
                f"%{category_name}%"
            )
        )
        .first()
    )

    if existing:
        return

    notification = Notification(
        user_id=user_id,
        message=message,
        type=notif_type
    )

    try:
        db.session.add(notification)
        db.session.commit()

    except Exception:
        db.session.rollback()


def check_budget_threshold(
    user_id,
    expense_date,
    category_id
):
    """
    Check overall/category budget after an expense is
    added or updated.

    Creates warning/exceeded notifications when required.
    """

    if not expense_date:
        return

    month = expense_date.month
    year = expense_date.year

    first_of_month = date(
        year,
        month,
        1
    )

    # -------------------------------------------------
    # Overall monthly budget
    # -------------------------------------------------

    overall_budget = (
        Budget.query
        .filter(
            Budget.user_id == user_id,
            Budget.category_id.is_(None),
            Budget.month == first_of_month
        )
        .first()
    )

    if overall_budget:

        total_spent = get_total_expenses_for_month(
            user_id,
            year,
            month
        )

        budget_amount = float(
            overall_budget.amount or 0
        )

        if budget_amount > 0:

            percentage = (
                total_spent / budget_amount
            ) * 100

            if percentage >= 100:

                _send_notification_if_not_exists(
                    user_id,
                    (
                        f"Overall budget exceeded! "
                        f"Spent ₹{total_spent:,.2f} "
                        f"of ₹{budget_amount:,.2f}."
                    ),
                    "budget_exceeded",
                    "Overall"
                )

            elif percentage >= 80:

                _send_notification_if_not_exists(
                    user_id,
                    (
                        f"Overall budget at "
                        f"{percentage:.0f}%! "
                        f"Spent ₹{total_spent:,.2f} "
                        f"of ₹{budget_amount:,.2f}."
                    ),
                    "budget_warning",
                    "Overall"
                )

    # -------------------------------------------------
    # Category-specific budget
    # -------------------------------------------------

    if category_id is None:
        return

    category_budget = (
        Budget.query
        .filter(
            Budget.user_id == user_id,
            Budget.category_id == category_id,
            Budget.month == first_of_month
        )
        .first()
    )

    if not category_budget:
        return

    category = db.session.get(
        Category,
        category_id
    )

    category_name = (
        category.name
        if category
        else "Unknown"
    )

    category_spent = get_category_expenses_for_month(
        user_id,
        category_id,
        year,
        month
    )

    category_budget_amount = float(
        category_budget.amount or 0
    )

    if category_budget_amount <= 0:
        return

    category_percentage = (
        category_spent /
        category_budget_amount
    ) * 100

    if category_percentage >= 100:

        _send_notification_if_not_exists(
            user_id,
            (
                f"{category_name} budget exceeded! "
                f"Spent ₹{category_spent:,.2f} "
                f"of ₹{category_budget_amount:,.2f}."
            ),
            "budget_exceeded",
            category_name
        )

    elif category_percentage >= 80:

        _send_notification_if_not_exists(
            user_id,
            (
                f"{category_name} budget at "
                f"{category_percentage:.0f}%! "
                f"Spent ₹{category_spent:,.2f} "
                f"of ₹{category_budget_amount:,.2f}."
            ),
            "budget_warning",
            category_name
        )


def get_budget_status(
    user_id,
    year,
    month
):
    """
    Return complete budget status for the current user.

    Includes:
    - Overall budget
    - Overall spending
    - Remaining amount
    - Percentage used
    - Overall status
    - Category budgets
    """

    year = int(year)
    month = int(month)

    if month < 1 or month > 12:
        raise ValueError("Invalid month")

    if year < 1:
        raise ValueError("Invalid year")

    first_of_month, _ = get_month_date_range(
        year,
        month
    )

    total_spent = get_total_expenses_for_month(
        user_id,
        year,
        month
    )

    result = {
        "overall": None,
        "categories": []
    }

    # -------------------------------------------------
    # Overall budget
    # -------------------------------------------------

    overall = (
        Budget.query
        .filter(
            Budget.user_id == user_id,
            Budget.category_id.is_(None),
            Budget.month == first_of_month
        )
        .first()
    )

    if overall:

        budget_amount = float(
            overall.amount or 0
        )

        percentage = (
            (total_spent / budget_amount) * 100
            if budget_amount > 0
            else 0
        )

        result["overall"] = {
            "budget_id": overall.id,
            "budget_amount": round(
                budget_amount,
                2
            ),
            "spent_amount": round(
                total_spent,
                2
            ),
            "remaining": round(
                max(
                    budget_amount - total_spent,
                    0
                ),
                2
            ),
            "percentage": round(
                min(percentage, 999),
                2
            ),
            "status": (
                "exceeded"
                if percentage >= 100
                else "warning"
                if percentage >= 80
                else "safe"
            )
        }

    # -------------------------------------------------
    # Category budgets
    # -------------------------------------------------

    category_budgets = (
        Budget.query
        .filter(
            Budget.user_id == user_id,
            Budget.category_id.is_not(None),
            Budget.month == first_of_month
        )
        .all()
    )

    for budget in category_budgets:

        category = db.session.get(
            Category,
            budget.category_id
        )

        category_name = (
            category.name
            if category
            else "Unknown"
        )

        category_spent = get_category_expenses_for_month(
            user_id,
            budget.category_id,
            year,
            month
        )

        category_amount = float(
            budget.amount or 0
        )

        category_percentage = (
            (category_spent / category_amount) * 100
            if category_amount > 0
            else 0
        )

        result["categories"].append({
            "budget_id": budget.id,
            "category_id": budget.category_id,
            "category_name": category_name,
            "budget_amount": round(
                category_amount,
                2
            ),
            "spent_amount": round(
                category_spent,
                2
            ),
            "remaining": round(
                max(
                    category_amount - category_spent,
                    0
                ),
                2
            ),
            "percentage": round(
                min(category_percentage, 999),
                2
            ),
            "status": (
                "exceeded"
                if category_percentage >= 100
                else "warning"
                if category_percentage >= 80
                else "safe"
            )
        })

    return result

