# backend/ml_models/budget_recommender.py
# Enhanced budget recommender using percentile-based smart suggestions

import numpy as np
import pandas as pd


class BudgetRecommender:
    """
    Recommends monthly budgets using:
    - Historical average (baseline)
    - 75th percentile (covers most months)
    - Conservative buffer (+15% for safety)
    - Category-specific intelligence
    """

    def __init__(self):
        self.recommendations = {}
        self.is_computed     = False
        self.summary         = {}

    def compute(self, expense_df, income_df=None):
        """
        Compute budget recommendations from expense history.
        """
        if expense_df is None or expense_df.empty:
            return False

        df = expense_df.copy()
        if 'month_period' not in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df['month_period'] = df['date'].dt.to_period('M')

        # Overall monthly totals
        monthly_totals = df.groupby('month_period')['amount'].sum()

        if len(monthly_totals) == 0:
            return False

        # Overall statistics
        overall_mean   = float(monthly_totals.mean())
        overall_median = float(monthly_totals.median())
        overall_p75    = float(np.percentile(monthly_totals.values, 75))
        overall_max    = float(monthly_totals.max())

        # Recommended overall budget
        # Uses 75th percentile + 15% buffer — covers most months safely
        overall_recommended = overall_p75 * 1.15

        self.summary = {
            'overall_average':     round(overall_mean, 2),
            'overall_median':      round(overall_median, 2),
            'overall_p75':         round(overall_p75, 2),
            'overall_max':         round(overall_max, 2),
            'recommended_overall': round(overall_recommended, 2),
            'months_analyzed':     len(monthly_totals)
        }

        # Category-wise recommendations
        category_recs = []
        for cat_name, group in df.groupby('category_name'):
            cat_monthly = group.groupby('month_period')['amount'].sum()

            cat_mean   = float(cat_monthly.mean())
            cat_p75    = float(np.percentile(cat_monthly.values, 75)) \
                         if len(cat_monthly) > 1 else cat_mean
            cat_max    = float(cat_monthly.max())
            cat_months = int(len(cat_monthly))

            # Recommend: p75 + 10% buffer if consistent,
            #            or mean + 20% if volatile
            if len(cat_monthly) >= 3:
                std = float(cat_monthly.std())
                cv  = (std / cat_mean) if cat_mean > 0 else 0
                if cv > 0.3:
                    # High variability — use more conservative estimate
                    recommended = cat_mean * 1.25
                else:
                    recommended = cat_p75 * 1.10
            else:
                recommended = cat_mean * 1.20

            category_recs.append({
                'category_name':      cat_name,
                'average_spending':   round(cat_mean, 2),
                'median_spending':    round(float(cat_monthly.median()), 2),
                'p75_spending':       round(cat_p75, 2),
                'max_spending':       round(cat_max, 2),
                'recommended_budget': round(recommended, 2),
                'months_active':      cat_months,
                'basis': (
                    'High variability — conservative estimate'
                    if len(cat_monthly) >= 3 and
                       float(cat_monthly.std() / cat_mean if cat_mean > 0 else 0) > 0.3
                    else '75th percentile + 10% buffer'
                )
            })

        category_recs.sort(
            key=lambda x: x['recommended_budget'], reverse=True
        )
        self.recommendations = category_recs
        self.is_computed     = True
        return True

    def get_results(self):
        if not self.is_computed:
            return {
                'status':  'not_computed',
                'message': 'Recommender has not been run yet.'
            }

        return {
            'status':                    'success',
            'overall':                   self.summary,
            'category_recommendations':  self.recommendations,
            'note': (
                'Recommendations use the 75th percentile of your '
                'historical spending plus a safety buffer.'
            )
        }


def recommend_budget(expense_data):
    """
    Standalone function interface.
    """
    if not expense_data or len(expense_data) < 5:
        return {
            'status':  'insufficient_data',
            'message': 'Need more expense records for recommendations.'
        }

    df = pd.DataFrame(expense_data)
    df['date']         = pd.to_datetime(df['date'])
    df['month_period'] = df['date'].dt.to_period('M')

    recommender = BudgetRecommender()
    recommender.compute(df)
    return recommender.get_results()