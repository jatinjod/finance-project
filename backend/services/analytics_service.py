# backend/services/analytics_service.py
# Core data loading and analysis using Pandas + NumPy

import pandas as pd
import numpy as np
from datetime import date, datetime
from extensions import db
from models.income import Income
from models.expense import Expense
from models.budget import Budget
from models.savings_goal import SavingsGoal
from sqlalchemy import func, extract


# ─────────────────────────────────────────────
# DATA LOADERS
# ─────────────────────────────────────────────

def load_income_df(user_id):
    """
    Load all income records for a user into a Pandas DataFrame.
    Returns empty DataFrame if no records exist.
    """
    records = Income.query.filter_by(user_id=user_id).all()

    if not records:
        return pd.DataFrame(columns=[
            'id', 'user_id', 'category_id', 'category_name',
            'amount', 'date', 'note', 'month', 'year',
            'month_period'
        ])

    data = []
    for r in records:
        data.append({
            'id':            r.id,
            'user_id':       r.user_id,
            'category_id':   r.category_id,
            'category_name': r.category.name if r.category else 'Unknown',
            'amount':        float(r.amount),
            'date':          pd.to_datetime(r.date),
            'note':          r.note or ''
        })

    df = pd.DataFrame(data)
    df['date']         = pd.to_datetime(df['date'])
    df['month']        = df['date'].dt.month
    df['year']         = df['date'].dt.year
    df['month_period'] = df['date'].dt.to_period('M')
    df['day_of_week']  = df['date'].dt.dayofweek
    df['week_type']    = df['day_of_week'].apply(
        lambda x: 'weekend' if x >= 5 else 'weekday'
    )

    return df.sort_values('date', ascending=False)


def load_expense_df(user_id):
    """
    Load all expense records for a user into a Pandas DataFrame.
    Returns empty DataFrame if no records exist.
    """
    records = Expense.query.filter_by(user_id=user_id).all()

    if not records:
        return pd.DataFrame(columns=[
            'id', 'user_id', 'category_id', 'category_name',
            'amount', 'date', 'note', 'month', 'year',
            'month_period', 'day_of_week', 'week_type'
        ])

    data = []
    for r in records:
        data.append({
            'id':            r.id,
            'user_id':       r.user_id,
            'category_id':   r.category_id,
            'category_name': r.category.name if r.category else 'Unknown',
            'amount':        float(r.amount),
            'date':          pd.to_datetime(r.date),
            'note':          r.note or ''
        })

    df = pd.DataFrame(data)
    df['date']         = pd.to_datetime(df['date'])
    df['month']        = df['date'].dt.month
    df['year']         = df['date'].dt.year
    df['month_period'] = df['date'].dt.to_period('M')
    df['day_of_week']  = df['date'].dt.dayofweek
    df['week_type']    = df['day_of_week'].apply(
        lambda x: 'weekend' if x >= 5 else 'weekday'
    )

    return df.sort_values('date', ascending=False)


def get_basic_stats(df):
    """
    Compute basic statistical summary for a DataFrame amount column.
    Returns dict with sum, mean, median, std, min, max, count.
    """
    if df.empty or 'amount' not in df.columns:
        return {
            'total': 0, 'mean': 0, 'median': 0,
            'std': 0, 'min': 0, 'max': 0, 'count': 0
        }

    amounts = df['amount']
    return {
        'total':  round(float(amounts.sum()), 2),
        'mean':   round(float(amounts.mean()), 2),
        'median': round(float(amounts.median()), 2),
        'std':    round(float(amounts.std() or 0), 2),
        'min':    round(float(amounts.min()), 2),
        'max':    round(float(amounts.max()), 2),
        'count':  int(len(amounts))
    }