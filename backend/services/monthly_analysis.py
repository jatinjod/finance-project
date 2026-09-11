# backend/services/monthly_analysis.py
# Month-by-month income, expense, balance, and comparison analysis

import pandas as pd
import numpy as np
from services.analytics_service import (
    load_income_df, load_expense_df, get_basic_stats
)

MONTH_NAMES = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]
SHORT_MONTHS = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
]


def get_monthly_summary(user_id, year=None, month=None):
    """
    Get complete monthly financial summary.
    If year and month are given: summary for that specific month.
    Otherwise: summary for current month.
    """
    from datetime import date
    today = date.today()
    year  = year  or today.year
    month = month or today.month

    inc_df = load_income_df(user_id)
    exp_df = load_expense_df(user_id)

    # Filter to selected month/year
    inc_month = inc_df[
        (inc_df['month'] == month) & (inc_df['year'] == year)
    ] if not inc_df.empty else inc_df

    exp_month = exp_df[
        (exp_df['month'] == month) & (exp_df['year'] == year)
    ] if not exp_df.empty else exp_df

    total_income   = float(inc_month['amount'].sum()) if not inc_month.empty else 0
    total_expenses = float(exp_month['amount'].sum()) if not exp_month.empty else 0
    balance        = total_income - total_expenses
    savings_rate   = round(
        (balance / total_income * 100), 2
    ) if total_income > 0 else 0

    # Daily spending for this month
    daily_expenses = []
    if not exp_month.empty:
        daily = exp_month.groupby(
            exp_month['date'].dt.day
        )['amount'].sum().reset_index()
        daily.columns = ['day', 'amount']
        daily_expenses = daily.to_dict('records')

    # Cumulative spending through the month
    cumulative = 0
    cumulative_data = []
    if daily_expenses:
        for d in sorted(daily_expenses, key=lambda x: x['day']):
            cumulative += d['amount']
            cumulative_data.append({
                'day':        int(d['day']),
                'daily':      round(d['amount'], 2),
                'cumulative': round(cumulative, 2)
            })

    # Income sources breakdown
    income_by_source = {}
    if not inc_month.empty:
        source_totals = inc_month.groupby('category_name')['amount'].sum()
        income_by_source = {
            k: round(float(v), 2)
            for k, v in source_totals.to_dict().items()
        }

    # Expense categories breakdown
    expense_by_category = {}
    if not exp_month.empty:
        cat_totals = exp_month.groupby('category_name')['amount'].sum()
        expense_by_category = {
            k: round(float(v), 2)
            for k, v in sorted(
                cat_totals.to_dict().items(),
                key=lambda x: x[1], reverse=True
            )
        }

    # Largest single transactions
    top_expenses = []
    if not exp_month.empty:
        top = exp_month.nlargest(5, 'amount')
        top_expenses = top[[
            'amount', 'category_name', 'date', 'note'
        ]].copy()
        top_expenses['date'] = top_expenses['date'].dt.strftime('%Y-%m-%d')
        top_expenses = top_expenses.to_dict('records')

    return {
        'month':               month,
        'year':                year,
        'month_name':          MONTH_NAMES[month - 1],
        'total_income':        round(total_income, 2),
        'total_expenses':      round(total_expenses, 2),
        'balance':             round(balance, 2),
        'savings_rate':        savings_rate,
        'income_count':        len(inc_month),
        'expense_count':       len(exp_month),
        'income_by_source':    income_by_source,
        'expense_by_category': expense_by_category,
        'daily_expenses':      cumulative_data,
        'top_expenses':        top_expenses,
        'income_stats':        get_basic_stats(inc_month),
        'expense_stats':       get_basic_stats(exp_month)
    }


def get_monthly_trend(user_id, months=6):
    """
    Build month-by-month trend data for the last N months.
    Returns list of monthly summaries with income, expenses,
    balance, savings rate, and growth percentages.
    """
    from datetime import date

    today   = date.today()
    inc_df  = load_income_df(user_id)
    exp_df  = load_expense_df(user_id)
    results = []

    for i in range(months - 1, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1

        inc_m = inc_df[
            (inc_df['month'] == m) & (inc_df['year'] == y)
        ] if not inc_df.empty else inc_df

        exp_m = exp_df[
            (exp_df['month'] == m) & (exp_df['year'] == y)
        ] if not exp_df.empty else exp_df

        income   = float(inc_m['amount'].sum()) if not inc_m.empty else 0
        expenses = float(exp_m['amount'].sum()) if not exp_m.empty else 0
        balance  = income - expenses

        results.append({
            'month':        m,
            'year':         y,
            'month_name':   MONTH_NAMES[m - 1],
            'month_short':  SHORT_MONTHS[m - 1],
            'month_label':  f"{SHORT_MONTHS[m - 1]} {y}",
            'total_income':   round(income, 2),
            'total_expenses': round(expenses, 2),
            'balance':        round(balance, 2),
            'savings_rate':   round(
                (balance / income * 100), 2
            ) if income > 0 else 0,
            'transaction_count': len(inc_m) + len(exp_m)
        })

    # Calculate month-over-month growth
    for i in range(1, len(results)):
        prev_exp = results[i - 1]['total_expenses']
        curr_exp = results[i]['total_expenses']
        if prev_exp > 0:
            growth = ((curr_exp - prev_exp) / prev_exp) * 100
            results[i]['expense_growth'] = round(growth, 2)
        else:
            results[i]['expense_growth'] = 0

        prev_inc = results[i - 1]['total_income']
        curr_inc = results[i]['total_income']
        if prev_inc > 0:
            growth = ((curr_inc - prev_inc) / prev_inc) * 100
            results[i]['income_growth'] = round(growth, 2)
        else:
            results[i]['income_growth'] = 0

    if results:
        results[0]['expense_growth'] = 0
        results[0]['income_growth']  = 0

    return results


def get_monthly_comparison(user_id, year, month):
    """
    Compare selected month with previous month.
    Shows what increased, decreased, and by how much.
    """
    prev_month = month - 1 if month > 1 else 12
    prev_year  = year if month > 1 else year - 1

    current  = get_monthly_summary(user_id, year, month)
    previous = get_monthly_summary(user_id, prev_year, prev_month)

    def pct_change(curr, prev):
        if prev == 0:
            return 100.0 if curr > 0 else 0.0
        return round(((curr - prev) / prev) * 100, 2)

    comparison = {
        'current_month':  current,
        'previous_month': previous,
        'changes': {
            'income': {
                'current':    current['total_income'],
                'previous':   previous['total_income'],
                'difference': round(
                    current['total_income'] - previous['total_income'], 2
                ),
                'percent':    pct_change(
                    current['total_income'], previous['total_income']
                )
            },
            'expenses': {
                'current':    current['total_expenses'],
                'previous':   previous['total_expenses'],
                'difference': round(
                    current['total_expenses'] - previous['total_expenses'], 2
                ),
                'percent':    pct_change(
                    current['total_expenses'], previous['total_expenses']
                )
            },
            'balance': {
                'current':    current['balance'],
                'previous':   previous['balance'],
                'difference': round(
                    current['balance'] - previous['balance'], 2
                ),
                'percent':    pct_change(
                    current['balance'], previous['balance']
                )
            }
        }
    }

    # Category-level changes
    category_changes = []
    all_cats = set(
        list(current['expense_by_category'].keys()) +
        list(previous['expense_by_category'].keys())
    )

    for cat in all_cats:
        curr_amt = current['expense_by_category'].get(cat, 0)
        prev_amt = previous['expense_by_category'].get(cat, 0)
        diff     = round(curr_amt - prev_amt, 2)
        pct      = pct_change(curr_amt, prev_amt)

        category_changes.append({
            'category':    cat,
            'current':     curr_amt,
            'previous':    prev_amt,
            'difference':  diff,
            'percent':     pct,
            'direction':   'up'   if diff > 0 else
                           'down' if diff < 0 else 'same'
        })

    comparison['category_changes'] = sorted(
        category_changes,
        key=lambda x: abs(x['difference']),
        reverse=True
    )

    return comparison