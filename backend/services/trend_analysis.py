# backend/services/trend_analysis.py
# Advanced spending trend analysis using NumPy

import numpy as np
import pandas as pd
from services.analytics_service import (
    load_expense_df, load_income_df
)


def get_overall_trend(user_id, months=6):
    """
    Detect overall spending trend using linear regression.
    Determines if spending is increasing, decreasing, or stable.
    """
    exp_df = load_expense_df(user_id)

    if exp_df.empty:
        return {'trend': 'no_data', 'monthly_totals': []}

    from datetime import date
    today  = date.today()
    totals = []

    for i in range(months - 1, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1

        subset = exp_df[
            (exp_df['month'] == m) & (exp_df['year'] == y)
        ]
        totals.append(float(subset['amount'].sum()))

    if len(totals) < 3 or sum(totals) == 0:
        return {
            'trend':         'insufficient_data',
            'monthly_totals': totals,
            'slope':          0,
            'message':        'Need at least 3 months of data'
        }

    x     = np.arange(len(totals), dtype=float)
    y_arr = np.array(totals, dtype=float)

    # NumPy linear regression
    slope, intercept = np.polyfit(x, y_arr, 1)

    # Percentage change per month
    avg = np.mean(y_arr[y_arr > 0]) if np.any(y_arr > 0) else 1
    monthly_change_pct = (slope / avg) * 100 if avg != 0 else 0

    if monthly_change_pct > 5:
        trend = 'increasing'
        msg   = f'Spending is growing by ~{monthly_change_pct:.1f}% per month.'
    elif monthly_change_pct < -5:
        trend = 'decreasing'
        msg   = f'Spending is reducing by ~{abs(monthly_change_pct):.1f}% per month.'
    else:
        trend = 'stable'
        msg   = 'Spending is relatively stable month over month.'

    # Volatility — how much spending fluctuates
    std  = float(np.std(y_arr))
    mean = float(np.mean(y_arr)) if float(np.mean(y_arr)) != 0 else 1
    cv   = (std / mean) * 100

    volatility = 'high' if cv > 30 else 'medium' if cv > 15 else 'low'

    return {
        'trend':             trend,
        'message':           msg,
        'slope':             round(float(slope), 2),
        'monthly_change_pct': round(monthly_change_pct, 2),
        'monthly_totals':    [round(t, 2) for t in totals],
        'average_monthly':   round(float(np.mean(y_arr)), 2),
        'std_deviation':     round(std, 2),
        'volatility':        volatility,
        'months_analyzed':   len(totals)
    }


def get_percentile_analysis(user_id):
    """
    Compute spending percentiles to identify unusual transactions.
    Transactions above 90th percentile are flagged.
    """
    exp_df = load_expense_df(user_id)

    if exp_df.empty or len(exp_df) < 5:
        return {'percentiles': {}, 'high_value_threshold': 0, 'flagged': []}

    amounts = exp_df['amount'].values

    percentiles = {
        'p25':  round(float(np.percentile(amounts, 25)), 2),
        'p50':  round(float(np.percentile(amounts, 50)), 2),
        'p75':  round(float(np.percentile(amounts, 75)), 2),
        'p90':  round(float(np.percentile(amounts, 90)), 2),
        'p95':  round(float(np.percentile(amounts, 95)), 2),
    }

    threshold = percentiles['p90']

    # Transactions above 90th percentile
    high_value = exp_df[exp_df['amount'] > threshold].copy()
    high_value['date'] = high_value['date'].dt.strftime('%Y-%m-%d')
    flagged = high_value[[
        'date', 'category_name', 'amount', 'note'
    ]].nlargest(10, 'amount').to_dict('records')

    return {
        'percentiles':          percentiles,
        'high_value_threshold': threshold,
        'flagged_count':        len(high_value),
        'flagged':              flagged,
        'total_records':        len(exp_df)
    }


def get_weekday_analysis(user_id):
    """
    Analyze spending by day of week.
    Identifies which days the user spends most.
    """
    exp_df = load_expense_df(user_id)

    if exp_df.empty:
        return {'by_day': [], 'highest_day': None, 'lowest_day': None}

    day_names = ['Monday', 'Tuesday', 'Wednesday',
                 'Thursday', 'Friday', 'Saturday', 'Sunday']

    by_day = exp_df.groupby('day_of_week')['amount'].agg(
        ['sum', 'mean', 'count']
    ).reset_index()

    result = []
    for _, row in by_day.iterrows():
        day_idx = int(row['day_of_week'])
        result.append({
            'day':        day_names[day_idx],
            'day_index':  day_idx,
            'total':      round(float(row['sum']), 2),
            'average':    round(float(row['mean']), 2),
            'count':      int(row['count'])
        })

    # Fill missing days with 0
    existing_days = {r['day_index'] for r in result}
    for i, name in enumerate(day_names):
        if i not in existing_days:
            result.append({
                'day': name, 'day_index': i,
                'total': 0, 'average': 0, 'count': 0
            })

    result.sort(key=lambda x: x['day_index'])

    highest = max(result, key=lambda x: x['total'])
    lowest  = min(
        [r for r in result if r['total'] > 0],
        key=lambda x: x['total'],
        default=None
    )

    # Weekend vs weekday
    weekend_total  = sum(
        r['total'] for r in result if r['day_index'] >= 5
    )
    weekday_total  = sum(
        r['total'] for r in result if r['day_index'] < 5
    )
    total          = weekend_total + weekday_total
    weekend_pct    = round((weekend_total / total * 100), 1) if total > 0 else 0

    return {
        'by_day':         result,
        'highest_day':    highest['day'] if highest else None,
        'lowest_day':     lowest['day'] if lowest else None,
        'weekend_total':  round(float(weekend_total), 2),
        'weekday_total':  round(float(weekday_total), 2),
        'weekend_pct':    weekend_pct,
        'weekday_pct':    round(100 - weekend_pct, 1)
    }


def get_income_vs_expense_ratio(user_id, months=6):
    """
    Calculate income-to-expense ratio for each month.
    Ratio > 1.0 means saving money, < 1.0 means overspending.
    """
    from datetime import date
    today  = date.today()
    inc_df = load_income_df(user_id)
    exp_df = load_expense_df(user_id)

    results = []
    for i in range(months - 1, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1

        inc_m = inc_df[
            (inc_df['month'] == m) & (inc_df['year'] == y)
        ] if not inc_df.empty else pd.DataFrame()

        exp_m = exp_df[
            (exp_df['month'] == m) & (exp_df['year'] == y)
        ] if not exp_df.empty else pd.DataFrame()

        income   = float(inc_m['amount'].sum()) if not inc_m.empty else 0
        expenses = float(exp_m['amount'].sum()) if not exp_m.empty else 0

        ratio = round(income / expenses, 2) if expenses > 0 else None

        results.append({
            'month':        m,
            'year':         y,
            'month_label':  f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][m-1]} {y}",
            'income':       round(income, 2),
            'expenses':     round(expenses, 2),
            'ratio':        ratio,
            'status':       'saving'     if ratio and ratio > 1.1 else
                            'balanced'   if ratio and ratio >= 0.9 else
                            'overspending' if ratio else 'no_income'
        })

    return results