# backend/services/category_analysis.py
# Deep category-level spending analysis

import pandas as pd
import numpy as np
from services.analytics_service import load_expense_df, load_income_df


def get_category_breakdown(user_id, year=None, month=None):
    """
    Complete category-wise expense breakdown.
    Includes amount, count, percentage, average, max transaction.
    """
    from datetime import date
    today = date.today()
    year  = year  or today.year
    month = month or today.month

    exp_df = load_expense_df(user_id)

    if exp_df.empty:
        return {
            'categories':     [],
            'total_expenses': 0,
            'top_category':   None,
            'month':          month,
            'year':           year
        }

    # Filter to period
    filtered = exp_df[
        (exp_df['month'] == month) & (exp_df['year'] == year)
    ]

    if filtered.empty:
        return {
            'categories':     [],
            'total_expenses': 0,
            'top_category':   None,
            'month':          month,
            'year':           year
        }

    total = float(filtered['amount'].sum())

    category_data = []
    for cat_name, group in filtered.groupby('category_name'):
        cat_total  = float(group['amount'].sum())
        cat_count  = len(group)
        cat_avg    = float(group['amount'].mean())
        cat_max    = float(group['amount'].max())
        cat_pct    = round((cat_total / total * 100), 2) if total > 0 else 0

        # Recent transactions in this category
        recent_txs = group.sort_values('date', ascending=False).head(3)
        recent_txs = recent_txs[['date', 'amount', 'note']].copy()
        recent_txs['date'] = recent_txs['date'].dt.strftime('%Y-%m-%d')

        category_data.append({
            'category_name':  cat_name,
            'total_amount':   round(cat_total, 2),
            'transaction_count': cat_count,
            'average_amount': round(cat_avg, 2),
            'max_amount':     round(cat_max, 2),
            'percentage':     cat_pct,
            'recent':         recent_txs.to_dict('records')
        })

    # Sort by total amount descending
    category_data.sort(key=lambda x: x['total_amount'], reverse=True)

    top_cat = category_data[0]['category_name'] if category_data else None

    return {
        'categories':     category_data,
        'total_expenses': round(total, 2),
        'top_category':   top_cat,
        'month':          month,
        'year':           year,
        'category_count': len(category_data)
    }


def get_category_trends(user_id, months=6):
    """
    Track each category's spending across multiple months.
    Used for the stacked bar / multi-line chart showing
    how each category grows or shrinks over time.
    """
    from datetime import date
    today  = date.today()
    exp_df = load_expense_df(user_id)

    if exp_df.empty:
        return {'months': [], 'categories': [], 'data': {}}

    # Build list of months
    month_list = []
    for i in range(months - 1, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        month_list.append({'month': m, 'year': y,
                            'label': f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][m-1]} {y}"})

    # All unique categories the user has used
    all_categories = list(exp_df['category_name'].unique())

    # Build data matrix: category → list of monthly totals
    data = {}
    for cat in all_categories:
        cat_totals = []
        for mp in month_list:
            subset = exp_df[
                (exp_df['category_name'] == cat) &
                (exp_df['month'] == mp['month']) &
                (exp_df['year']  == mp['year'])
            ]
            cat_totals.append(
                round(float(subset['amount'].sum()), 2)
            )
        data[cat] = cat_totals

    # Only include categories that have at least one non-zero month
    active_categories = [
        cat for cat in all_categories
        if any(v > 0 for v in data[cat])
    ]

    return {
        'months':     [mp['label'] for mp in month_list],
        'categories': active_categories,
        'data': {cat: data[cat] for cat in active_categories}
    }


def get_spending_velocity(user_id, year=None, month=None):
    """
    Calculate spending velocity — how fast money is being spent.
    Compares first half of month vs second half.
    Identifies if user front-loads or end-loads their spending.
    """
    from datetime import date
    today = date.today()
    year  = year  or today.year
    month = month or today.month

    exp_df = load_expense_df(user_id)

    if exp_df.empty:
        return {'first_half': 0, 'second_half': 0, 'pattern': 'no_data'}

    filtered = exp_df[
        (exp_df['month'] == month) & (exp_df['year'] == year)
    ]

    if filtered.empty:
        return {'first_half': 0, 'second_half': 0, 'pattern': 'no_data'}

    filtered = filtered.copy()
    filtered['day'] = filtered['date'].dt.day

    first_half  = filtered[filtered['day'] <= 15]['amount'].sum()
    second_half = filtered[filtered['day'] > 15]['amount'].sum()
    total       = first_half + second_half

    first_pct  = round((float(first_half)  / float(total) * 100), 1) if total > 0 else 0
    second_pct = round((float(second_half) / float(total) * 100), 1) if total > 0 else 0

    if first_pct > 60:
        pattern = 'front_loaded'
        insight = 'You spend most of your money in the first half of the month.'
    elif second_pct > 60:
        pattern = 'end_loaded'
        insight = 'You spend most of your money in the second half of the month.'
    else:
        pattern = 'balanced'
        insight = 'Your spending is evenly distributed throughout the month.'

    return {
        'first_half':     round(float(first_half), 2),
        'second_half':    round(float(second_half), 2),
        'first_pct':      first_pct,
        'second_pct':     second_pct,
        'pattern':        pattern,
        'insight':        insight,
        'total_expenses': round(float(total), 2)
    }