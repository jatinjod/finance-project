# backend/services/report_service.py
# Generates detailed financial reports

from datetime import date

from sqlalchemy import func

from extensions import db
from models.income import Income
from models.expense import Expense


def get_month_date_range(year, month):
    """Return first day of month and first day of next month."""

    year = int(year)
    month = int(month)

    if month < 1 or month > 12:
        raise ValueError("Invalid month")

    if year < 1:
        raise ValueError("Invalid year")

    first_day = date(year, month, 1)

    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)

    return first_day, next_month


def get_monthly_report(user_id, year, month):
    """Generate a complete monthly income and expense summary."""

    year = int(year)
    month = int(month)

    first_day, next_month = get_month_date_range(
        year,
        month
    )

    income_records = (
        Income.query
        .filter(
            Income.user_id == user_id,
            Income.date >= first_day,
            Income.date < next_month
        )
        .order_by(
            Income.date.asc(),
            Income.id.asc()
        )
        .all()
    )

    expense_records = (
        Expense.query
        .filter(
            Expense.user_id == user_id,
            Expense.date >= first_day,
            Expense.date < next_month
        )
        .order_by(
            Expense.date.asc(),
            Expense.id.asc()
        )
        .all()
    )

    total_income = round(
        sum(
            float(income.amount or 0)
            for income in income_records
        ),
        2
    )

    total_expenses = round(
        sum(
            float(expense.amount or 0)
            for expense in expense_records
        ),
        2
    )

    balance = round(
        total_income - total_expenses,
        2
    )

    savings_rate = (
        round(
            (balance / total_income) * 100,
            2
        )
        if total_income > 0
        else 0
    )

    # -------------------------------------------------
    # EXPENSE BY CATEGORY
    # -------------------------------------------------

    expense_by_category = {}

    for expense in expense_records:

        category_name = (
            expense.category.name
            if expense.category
            else "Unknown"
        )

        expense_by_category[category_name] = round(
            expense_by_category.get(
                category_name,
                0
            ) + float(expense.amount or 0),
            2
        )

    # -------------------------------------------------
    # INCOME BY CATEGORY
    # -------------------------------------------------

    income_by_category = {}

    for income in income_records:

        category_name = (
            income.category.name
            if income.category
            else "Unknown"
        )

        income_by_category[category_name] = round(
            income_by_category.get(
                category_name,
                0
            ) + float(income.amount or 0),
            2
        )

    # -------------------------------------------------
    # TOP EXPENSE CATEGORY
    # -------------------------------------------------

    top_expense_category = (
        max(
            expense_by_category,
            key=expense_by_category.get
        )
        if expense_by_category
        else None
    )

    return {
        "month": month,
        "year": year,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "balance": balance,
        "savings_rate": savings_rate,
        "income_by_category": income_by_category,
        "expense_by_category": expense_by_category,
        "top_expense_category": top_expense_category,
        "income_count": len(income_records),
        "expense_count": len(expense_records)
    }


def get_spending_trend(user_id, months=6):
    """Get monthly income vs expense data for the last N months."""

    today = date.today()

    months = max(
        2,
        min(12, int(months))
    )

    trend_data = []

    month_names = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December"
    ]

    for offset in range(
        months - 1,
        -1,
        -1
    ):

        target_month = today.month - offset
        target_year = today.year

        while target_month <= 0:
            target_month += 12
            target_year -= 1

        first_day, next_month = get_month_date_range(
            target_year,
            target_month
        )

        month_income = (
            db.session
            .query(
                func.coalesce(
                    func.sum(Income.amount),
                    0
                )
            )
            .filter(
                Income.user_id == user_id,
                Income.date >= first_day,
                Income.date < next_month
            )
            .scalar()
            or 0
        )

        month_expenses = (
            db.session
            .query(
                func.coalesce(
                    func.sum(Expense.amount),
                    0
                )
            )
            .filter(
                Expense.user_id == user_id,
                Expense.date >= first_day,
                Expense.date < next_month
            )
            .scalar()
            or 0
        )

        month_income = round(
            float(month_income),
            2
        )

        month_expenses = round(
            float(month_expenses),
            2
        )

        trend_data.append({
            "month": target_month,
            "year": target_year,
            "month_label": (
                f"{month_names[target_month - 1]} "
                f"{target_year}"
            ),
            "total_income": month_income,
            "total_expenses": month_expenses,
            "balance": round(
                month_income - month_expenses,
                2
            )
        })

    return trend_data


def get_category_report(user_id, year, month):
    """Detailed expense breakdown by category for a given month."""

    year = int(year)
    month = int(month)

    first_day, next_month = get_month_date_range(
        year,
        month
    )

    expense_records = (
        Expense.query
        .filter(
            Expense.user_id == user_id,
            Expense.date >= first_day,
            Expense.date < next_month
        )
        .order_by(
            Expense.date.desc(),
            Expense.id.desc()
        )
        .all()
    )

    total_expenses = round(
        sum(
            float(expense.amount or 0)
            for expense in expense_records
        ),
        2
    )

    category_data = {}

    for expense in expense_records:

        category_name = (
            expense.category.name
            if expense.category
            else "Unknown"
        )

        if category_name not in category_data:

            category_data[category_name] = {
                "amount": 0,
                "count": 0,
                "transactions": []
            }

        amount = round(
            float(expense.amount or 0),
            2
        )

        category_data[category_name]["amount"] += amount

        category_data[category_name]["count"] += 1

        category_data[category_name]["transactions"].append({
            "id": expense.id,
            "date": (
                expense.date.isoformat()
                if expense.date
                else None
            ),
            "amount": amount,
            "note": expense.note
        })

    # -------------------------------------------------
    # CATEGORY PERCENTAGES
    # -------------------------------------------------

    for category_name, category in category_data.items():

        amount = round(
            float(category["amount"]),
            2
        )

        percentage = (
            round(
                (amount / total_expenses) * 100,
                2
            )
            if total_expenses > 0
            else 0
        )

        category["amount"] = amount
        category["percentage"] = percentage

    # -------------------------------------------------
    # SORT HIGHEST SPENDING FIRST
    # -------------------------------------------------

    sorted_categories = dict(
        sorted(
            category_data.items(),
            key=lambda item: item[1]["amount"],
            reverse=True
        )
    )

    return {
        "month": month,
        "year": year,
        "total_expenses": total_expenses,
        "categories": sorted_categories
    }