# backend/services/budget_analysis.py
# Detailed budget utilization analysis

import pandas as pd
from datetime import date
from extensions import db
from models.budget import Budget
from models.expense import Expense
from models.category import Category
from sqlalchemy import func, extract
from services.analytics_service import load_expense_df


def get_budget_utilization(user_id, months=3):
    """
    Track budget utilization across multiple months.
    Shows how well the user is sticking to their budgets.
    """
    today   = date.today()
    results = []

    for i in range(months - 1, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1

        first_of_month = date(y, m, 1)

        # Get overall budget for this month
        overall = Budget.query.filter(
            Budget.user_id     == user_id,
            Budget.category_id.is_(None),
            Budget.month       == first_of_month
        ).first()

        # Total expenses this month
        total_exp = db.session.query(
            func.sum(Expense.amount)
        ).filter(
            Expense.user_id == user_id,
            extract('month', Expense.date) == m,
            extract('year',  Expense.date) == y
        ).scalar() or 0

        total_exp = float(total_exp)

        month_data = {
            'month':  m,
            'year':   y,
            'month_label': f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][m-1]} {y}",
            'total_expenses': round(total_exp, 2),
            'overall_budget': None,
            'overall_utilization': None,
            'category_budgets': []
        }

        if overall:
            budget_amt = float(overall.amount)
            utilization = round((total_exp / budget_amt * 100), 2) if budget_amt > 0 else 0
            month_data['overall_budget']      = budget_amt
            month_data['overall_utilization'] = utilization
            month_data['overall_status'] = (
                'exceeded' if utilization >= 100 else
                'warning'  if utilization >= 80  else
                'safe'
            )

        # Category budgets
        cat_budgets = Budget.query.filter(
            Budget.user_id     == user_id,
            Budget.category_id.isnot(None),
            Budget.month       == first_of_month
        ).all()

        for cb in cat_budgets:
            cat_exp = db.session.query(
                func.sum(Expense.amount)
            ).filter(
                Expense.user_id     == user_id,
                Expense.category_id == cb.category_id,
                extract('month', Expense.date) == m,
                extract('year',  Expense.date) == y
            ).scalar() or 0

            cat_exp    = float(cat_exp)
            cat_budget = float(cb.amount)
            cat_util   = round(
                (cat_exp / cat_budget * 100), 2
            ) if cat_budget > 0 else 0

            month_data['category_budgets'].append({
                'category_id':   cb.category_id,
                'category_name': cb.category.name if cb.category else 'Unknown',
                'budget_amount': cat_budget,
                'spent_amount':  round(cat_exp, 2),
                'utilization':   cat_util,
                'remaining':     round(max(cat_budget - cat_exp, 0), 2),
                'status': (
                    'exceeded' if cat_util >= 100 else
                    'warning'  if cat_util >= 80  else
                    'safe'
                )
            })

        results.append(month_data)

    return results


def get_budget_adherence_score(user_id):
    """
    Calculate an overall budget adherence score (0-100).
    100 = always within budget, 0 = always over budget.
    """
    utilization_data = get_budget_utilization(user_id, months=6)

    scores = []
    for month_data in utilization_data:
        if month_data['overall_utilization'] is not None:
            util = month_data['overall_utilization']
            # Score: 100 if under 80%, decreasing as it goes over
            if util <= 80:
                score = 100
            elif util <= 100:
                score = 100 - ((util - 80) * 2.5)  # Lose 2.5 pts per % over 80
            else:
                score = max(0, 50 - ((util - 100) * 2))  # Steep penalty over 100%
            scores.append(score)

    if not scores:
        return {
            'score':   None,
            'grade':   'N/A',
            'message': 'Set a budget to track adherence.'
        }

    avg_score = round(sum(scores) / len(scores), 1)
    grade     = (
        'A' if avg_score >= 90 else
        'B' if avg_score >= 75 else
        'C' if avg_score >= 60 else
        'D' if avg_score >= 45 else
        'F'
    )
    message = {
        'A': 'Excellent! You consistently stay within your budget.',
        'B': 'Good. You mostly stay within your budget.',
        'C': 'Fair. You occasionally exceed your budget.',
        'D': 'Poor. You frequently exceed your budget.',
        'F': 'Critical. You are significantly over budget most months.'
    }[grade]

    return {
        'score':          avg_score,
        'grade':          grade,
        'message':        message,
        'months_tracked': len(scores)
    }