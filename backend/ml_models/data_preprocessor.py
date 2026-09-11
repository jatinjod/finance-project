# backend/ml_models/data_preprocessor.py
# Central data preprocessing for all ML models
# Loads, cleans, and engineers features from transaction data

import pandas as pd
import numpy as np
from datetime import date, datetime


class DataPreprocessor:
    """
    Handles all data loading and feature engineering
    for ML models.
    """

    def __init__(self, user_id):
        self.user_id = user_id
        self.expense_df = None
        self.income_df  = None
        self.is_loaded  = False

    def load(self):
        """Load all user data from database into DataFrames."""
        from models.expense import Expense
        from models.income import Income

        # Load expenses
        expenses = Expense.query.filter_by(user_id=self.user_id).all()
        exp_data = []
        for e in expenses:
            exp_data.append({
                'id':            e.id,
                'amount':        float(e.amount),
                'date':          e.date,
                'category_id':   e.category_id,
                'category_name': e.category.name if e.category else 'Unknown',
                'note':          e.note or ''
            })

        if exp_data:
            self.expense_df = pd.DataFrame(exp_data)
            self.expense_df = self._engineer_expense_features(self.expense_df)
        else:
            self.expense_df = pd.DataFrame()

        # Load income
        incomes = Income.query.filter_by(user_id=self.user_id).all()
        inc_data = []
        for i in incomes:
            inc_data.append({
                'id':            i.id,
                'amount':        float(i.amount),
                'date':          i.date,
                'category_id':   i.category_id,
                'category_name': i.category.name if i.category else 'Unknown',
                'note':          i.note or ''
            })

        if inc_data:
            self.income_df = pd.DataFrame(inc_data)
            self.income_df = self._engineer_income_features(self.income_df)
        else:
            self.income_df = pd.DataFrame()

        self.is_loaded = True
        return self

    def _engineer_expense_features(self, df):
        """Add derived features to expense DataFrame."""
        df = df.copy()
        df['date']        = pd.to_datetime(df['date'])
        df['year']        = df['date'].dt.year
        df['month']       = df['date'].dt.month
        df['day']         = df['date'].dt.day
        df['day_of_week'] = df['date'].dt.dayofweek
        df['week_of_year']= df['date'].dt.isocalendar().week.astype(int)
        df['is_weekend']  = (df['day_of_week'] >= 5).astype(int)
        df['is_month_end']= (df['day'] >= 25).astype(int)
        df['month_num']   = (
            (df['year'] - df['year'].min()) * 12 + df['month']
        )
        df['log_amount']  = np.log1p(df['amount'])
        df['month_period'] = df['date'].dt.to_period('M')
        return df.sort_values('date').reset_index(drop=True)

    def _engineer_income_features(self, df):
        """Add derived features to income DataFrame."""
        df = df.copy()
        df['date']         = pd.to_datetime(df['date'])
        df['year']         = df['date'].dt.year
        df['month']        = df['date'].dt.month
        df['month_period'] = df['date'].dt.to_period('M')
        return df.sort_values('date').reset_index(drop=True)

    def get_monthly_totals(self):
        """
        Return a DataFrame with one row per month
        showing total income, expenses, and balance.
        """
        if self.expense_df is None or self.expense_df.empty:
            return pd.DataFrame()

        exp_monthly = self.expense_df.groupby(
            ['year', 'month', 'month_num']
        )['amount'].sum().reset_index()
        exp_monthly.columns = [
            'year', 'month', 'month_num', 'total_expenses'
        ]

        if self.income_df is not None and not self.income_df.empty:
            inc_monthly = self.income_df.groupby(
                ['year', 'month']
            )['amount'].sum().reset_index()
            inc_monthly.columns = ['year', 'month', 'total_income']
            monthly = pd.merge(
                exp_monthly, inc_monthly,
                on=['year', 'month'], how='left'
            )
            monthly['total_income'] = monthly['total_income'].fillna(0)
        else:
            exp_monthly['total_income'] = 0
            monthly = exp_monthly

        monthly['balance']      = monthly['total_income'] - monthly['total_expenses']
        monthly['savings_rate'] = monthly.apply(
            lambda r: (r['balance'] / r['total_income'] * 100)
                      if r['total_income'] > 0 else 0,
            axis=1
        )
        return monthly.sort_values('month_num').reset_index(drop=True)

    def get_category_monthly(self):
        """
        Return DataFrame with monthly totals per category.
        Used for category trend analysis.
        """
        if self.expense_df is None or self.expense_df.empty:
            return pd.DataFrame()

        return self.expense_df.groupby(
            ['year', 'month', 'month_num', 'category_name']
        )['amount'].sum().reset_index()

    def has_sufficient_data(self, min_records=10, min_months=2):
        """
        Check if user has enough data for ML analysis.
        Returns dict with flags and counts.
        """
        if self.expense_df is None or self.expense_df.empty:
            return {
                'sufficient':    False,
                'record_count':  0,
                'month_count':   0,
                'min_records':   min_records,
                'min_months':    min_months,
                'message':       f'Add at least {min_records} expense records '
                                 f'to unlock AI features.'
            }

        record_count = len(self.expense_df)
        month_count  = self.expense_df['month_period'].nunique()
        sufficient   = (
            record_count >= min_records and
            month_count  >= min_months
        )

        return {
            'sufficient':   sufficient,
            'record_count': record_count,
            'month_count':  month_count,
            'min_records':  min_records,
            'min_months':   min_months,
            'message': (
                'AI analysis ready.'
                if sufficient else
                f'Need {max(0, min_records - record_count)} more records '
                f'and {max(0, min_months - month_count)} more month(s) of data.'
            )
        }

    def get_stats(self):
        """Return basic statistics about the loaded data."""
        if self.expense_df is None or self.expense_df.empty:
            return {}

        amounts = self.expense_df['amount']
        return {
            'total_records':    len(self.expense_df),
            'total_months':     self.expense_df['month_period'].nunique(),
            'total_spent':      round(float(amounts.sum()), 2),
            'avg_per_record':   round(float(amounts.mean()), 2),
            'median_expense':   round(float(amounts.median()), 2),
            'std_expense':      round(float(amounts.std() or 0), 2),
            'min_expense':      round(float(amounts.min()), 2),
            'max_expense':      round(float(amounts.max()), 2),
            'unique_categories': self.expense_df['category_name'].nunique(),
            'date_range': {
                'from': str(self.expense_df['date'].min().date()),
                'to':   str(self.expense_df['date'].max().date())
            }
        }