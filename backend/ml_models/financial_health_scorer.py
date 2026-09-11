# backend/ml_models/financial_health_scorer.py
# Computes an overall financial health score (0–100) for the user

import numpy as np
import pandas as pd
from datetime import date


class FinancialHealthScorer:
    """
    Computes a financial health score from 0 to 100.
    
    Score components:
    1. Savings Rate (25 pts) — What % of income is saved
    2. Budget Adherence (20 pts) — How well user stays on budget
    3. Spending Consistency (20 pts) — Stable, not erratic spending
    4. Expense Diversity (15 pts) — Not too reliant on one category
    5. Savings Goals Progress (10 pts) — Working toward goals
    6. Income Stability (10 pts) — Consistent income
    """

    def __init__(self):
        self.scores      = {}
        self.total_score = 0
        self.grade       = 'N/A'
        self.insights    = []
        self.breakdown   = []

    def compute(self, expense_df, income_df=None,
                budget_data=None, goals_data=None):
        """
        Compute full financial health score.
        """
        self.scores = {}

        self._score_savings_rate(expense_df, income_df)
        self._score_spending_consistency(expense_df)
        self._score_expense_diversity(expense_df)
        self._score_savings_goals(goals_data)
        self._score_income_stability(income_df)
        self._score_budget_adherence(budget_data)

        # Total score (weighted sum)
        self.total_score = round(sum(self.scores.values()), 1)
        self.total_score = max(0, min(100, self.total_score))

        # Grade
        self.grade = (
            'A+' if self.total_score >= 90 else
            'A'  if self.total_score >= 80 else
            'B'  if self.total_score >= 70 else
            'C'  if self.total_score >= 60 else
            'D'  if self.total_score >= 45 else
            'F'
        )

        self._generate_insights()
        return self

    def _score_savings_rate(self, expense_df, income_df):
        """
        Score based on savings rate.
        Max 25 points.
        20%+ savings rate → 25 pts
        10-20% → 15 pts
        0-10% → 8 pts
        Negative → 0 pts
        """
        if income_df is None or income_df.empty or \
           expense_df is None or expense_df.empty:
            self.scores['savings_rate'] = 10  # Neutral if no income data
            self.breakdown.append({
                'metric':      'Savings Rate',
                'score':       10,
                'max_score':   25,
                'description': 'No income data to compute savings rate.',
                'status':      'neutral'
            })
            return

        if 'month_period' not in expense_df.columns:
            expense_df = expense_df.copy()
            expense_df['date']         = pd.to_datetime(expense_df['date'])
            expense_df['month_period'] = expense_df['date'].dt.to_period('M')

        if 'month_period' not in income_df.columns:
            income_df = income_df.copy()
            income_df['date']         = pd.to_datetime(income_df['date'])
            income_df['month_period'] = income_df['date'].dt.to_period('M')

        common = set(expense_df['month_period'].unique()) & \
                 set(income_df['month_period'].unique())

        if not common:
            self.scores['savings_rate'] = 5
            self.breakdown.append({
                'metric':      'Savings Rate',
                'score':       5,
                'max_score':   25,
                'description': 'No matching months between income and expense data.',
                'status':      'poor'
            })
            return

        rates = []
        for m in common:
            inc = float(
                income_df[income_df['month_period'] == m]['amount'].sum()
            )
            exp = float(
                expense_df[expense_df['month_period'] == m]['amount'].sum()
            )
            if inc > 0:
                rates.append(((inc - exp) / inc) * 100)

        avg_rate = float(np.mean(rates)) if rates else 0

        if avg_rate >= 20:
            score = 25
            status = 'excellent'
            desc   = f'Excellent! Saving {avg_rate:.0f}% of income.'
        elif avg_rate >= 10:
            score = 18
            status = 'good'
            desc   = f'Good. Saving {avg_rate:.0f}% of income.'
        elif avg_rate >= 0:
            score = 10
            status = 'fair'
            desc   = f'Only saving {avg_rate:.0f}% of income. Aim for 20%.'
        else:
            score = 0
            status = 'poor'
            desc   = f'Spending {abs(avg_rate):.0f}% more than income!'

        self.scores['savings_rate'] = score
        self.breakdown.append({
            'metric':      'Savings Rate',
            'score':       score,
            'max_score':   25,
            'value':       round(avg_rate, 1),
            'description': desc,
            'status':      status
        })

    def _score_spending_consistency(self, expense_df):
        """
        Score based on spending consistency (low volatility = good).
        Max 20 points.
        """
        if expense_df is None or expense_df.empty:
            self.scores['consistency'] = 10
            return

        if 'month_period' not in expense_df.columns:
            expense_df = expense_df.copy()
            expense_df['date'] = pd.to_datetime(expense_df['date'])
            expense_df['month_period'] = expense_df['date'].dt.to_period('M')

        monthly = expense_df.groupby('month_period')['amount'].sum()

        if len(monthly) < 2:
            self.scores['consistency'] = 10
            self.breakdown.append({
                'metric': 'Spending Consistency', 'score': 10,
                'max_score': 20, 'description': 'Need 2+ months of data.',
                'status': 'neutral'
            })
            return

        mean = float(monthly.mean())
        std  = float(monthly.std())
        cv   = (std / mean) if mean > 0 else 1

        if cv < 0.10:
            score = 20
            status = 'excellent'
            desc   = 'Very consistent spending month-to-month.'
        elif cv < 0.20:
            score = 15
            status = 'good'
            desc   = 'Fairly consistent spending.'
        elif cv < 0.35:
            score = 10
            status = 'fair'
            desc   = 'Some variation in monthly spending.'
        else:
            score = 5
            status = 'poor'
            desc   = 'High variability in spending — hard to plan.'

        self.scores['consistency'] = score
        self.breakdown.append({
            'metric':      'Spending Consistency',
            'score':       score,
            'max_score':   20,
            'value':       round(cv * 100, 1),
            'description': desc,
            'status':      status
        })

    def _score_expense_diversity(self, expense_df):
        """
        Score based on expense diversity — not over-spending on one category.
        Max 15 points.
        """
        if expense_df is None or expense_df.empty:
            self.scores['diversity'] = 8
            return

        cat_totals  = expense_df.groupby('category_name')['amount'].sum()
        total       = float(cat_totals.sum())
        if total == 0:
            self.scores['diversity'] = 8
            return

        top_pct = float(cat_totals.max() / total * 100)

        if top_pct < 35:
            score = 15
            status = 'excellent'
            desc   = 'Well-diversified spending across categories.'
        elif top_pct < 50:
            score = 10
            status = 'good'
            desc   = f'Top category is {top_pct:.0f}% of spending — reasonable.'
        elif top_pct < 65:
            score = 6
            status = 'fair'
            desc   = f'One category dominates {top_pct:.0f}% of your expenses.'
        else:
            score = 2
            status = 'poor'
            desc   = f'Over-concentrated! {top_pct:.0f}% of spending in one category.'

        self.scores['diversity'] = score
        self.breakdown.append({
            'metric':      'Expense Diversity',
            'score':       score,
            'max_score':   15,
            'value':       round(top_pct, 1),
            'description': desc,
            'status':      status
        })

    def _score_savings_goals(self, goals_data):
        """
        Score based on savings goals progress.
        Max 10 points.
        """
        if not goals_data:
            self.scores['goals'] = 5
            self.breakdown.append({
                'metric': 'Savings Goals', 'score': 5, 'max_score': 10,
                'description': 'No savings goals set.',
                'status': 'neutral'
            })
            return

        total_goals     = len(goals_data)
        completed_goals = sum(1 for g in goals_data if g.get('is_complete'))
        active_goals    = total_goals - completed_goals

        if total_goals == 0:
            score = 3
            desc  = 'No savings goals set.'
            status = 'poor'
        elif active_goals > 0:
            avg_progress = np.mean([
                g.get('progress_percentage', 0)
                for g in goals_data
                if not g.get('is_complete')
            ])
            score  = min(10, int(avg_progress / 10) + 3)
            desc   = f'{active_goals} active goal(s), avg {avg_progress:.0f}% complete.'
            status = 'good' if avg_progress >= 50 else 'fair'
        else:
            score  = 10
            desc   = f'All {total_goals} savings goals completed!'
            status = 'excellent'

        self.scores['goals'] = score
        self.breakdown.append({
            'metric':      'Savings Goals',
            'score':       score,
            'max_score':   10,
            'description': desc,
            'status':      status
        })

    def _score_income_stability(self, income_df):
        """
        Score based on income consistency.
        Max 10 points.
        """
        if income_df is None or income_df.empty:
            self.scores['income_stability'] = 5
            self.breakdown.append({
                'metric': 'Income Stability', 'score': 5, 'max_score': 10,
                'description': 'No income data available.',
                'status': 'neutral'
            })
            return

        if 'month_period' not in income_df.columns:
            income_df = income_df.copy()
            income_df['date'] = pd.to_datetime(income_df['date'])
            income_df['month_period'] = income_df['date'].dt.to_period('M')

        monthly = income_df.groupby('month_period')['amount'].sum()

        if len(monthly) < 2:
            self.scores['income_stability'] = 7
            self.breakdown.append({
                'metric': 'Income Stability', 'score': 7, 'max_score': 10,
                'description': 'Not enough months of income data.',
                'status': 'neutral'
            })
            return

        mean = float(monthly.mean())
        std  = float(monthly.std())
        cv   = (std / mean) if mean > 0 else 1

        if cv < 0.05:
            score = 10
            status = 'excellent'
            desc   = 'Very stable, predictable income.'
        elif cv < 0.15:
            score = 8
            status = 'good'
            desc   = 'Fairly stable income.'
        elif cv < 0.30:
            score = 5
            status = 'fair'
            desc   = 'Some income variability.'
        else:
            score = 2
            status = 'poor'
            desc   = 'Highly variable income — plan carefully.'

        self.scores['income_stability'] = score
        self.breakdown.append({
            'metric':      'Income Stability',
            'score':       score,
            'max_score':   10,
            'description': desc,
            'status':      status
        })

    def _score_budget_adherence(self, budget_data):
        """
        Score based on how well user sticks to budgets.
        Max 20 points.
        """
        if not budget_data:
            self.scores['budget_adherence'] = 10
            self.breakdown.append({
                'metric': 'Budget Adherence', 'score': 10, 'max_score': 20,
                'description': 'No budget set. Set one to improve this score.',
                'status': 'neutral'
            })
            return

        # budget_data is a list of monthly budget utilization dicts
        utilizations = []
        for month_data in budget_data:
            util = month_data.get('overall_utilization')
            if util is not None:
                utilizations.append(util)

        if not utilizations:
            self.scores['budget_adherence'] = 10
            return

        avg_util = float(np.mean(utilizations))

        if avg_util <= 75:
            score = 20
            status = 'excellent'
            desc   = f'Excellent! Average budget usage: {avg_util:.0f}%.'
        elif avg_util <= 90:
            score = 15
            status = 'good'
            desc   = f'Good. Average budget usage: {avg_util:.0f}%.'
        elif avg_util <= 100:
            score = 8
            status = 'fair'
            desc   = f'Close to budget limit. Usage: {avg_util:.0f}%.'
        else:
            score = 2
            status = 'poor'
            desc   = f'Over budget! Average usage: {avg_util:.0f}%.'

        self.scores['budget_adherence'] = score
        self.breakdown.append({
            'metric':      'Budget Adherence',
            'score':       score,
            'max_score':   20,
            'value':       round(avg_util, 1),
            'description': desc,
            'status':      status
        })

    def _generate_insights(self):
        """Generate overall insights based on the score."""
        self.insights = []

        if self.total_score >= 80:
            self.insights.append(
                '🌟 Your financial health is excellent! Keep up the great work.'
            )
        elif self.total_score >= 65:
            self.insights.append(
                '👍 Your finances are in good shape. A few improvements can '
                'take you to excellent.'
            )
        elif self.total_score >= 50:
            self.insights.append(
                '⚠️ Your financial health needs attention. Focus on the areas '
                'below to improve.'
            )
        else:
            self.insights.append(
                '🚨 Your financial health needs urgent improvement. '
                'Review your spending and budget immediately.'
            )

        # Specific insights from breakdown
        for item in self.breakdown:
            if item.get('status') == 'poor' and item.get('score', 10) < 5:
                self.insights.append(
                    f"❗ {item['metric']}: {item['description']}"
                )
            elif item.get('status') == 'excellent':
                self.insights.append(
                    f"✅ {item['metric']}: {item['description']}"
                )

    def get_results(self):
        return {
            'total_score':  self.total_score,
            'grade':        self.grade,
            'breakdown':    self.breakdown,
            'insights':     self.insights,
            'component_scores': self.scores,
            'grade_description': {
                'A+': 'Excellent financial health',
                'A':  'Very good financial health',
                'B':  'Good financial health',
                'C':  'Fair — room for improvement',
                'D':  'Poor — needs attention',
                'F':  'Critical — immediate action needed'
            }.get(self.grade, '')
        }