# backend/ml_models/pattern_detector.py
# Advanced spending pattern detection with actionable insights

import pandas as pd
import numpy as np


class PatternDetector:
    """
    Detects spending patterns using data analysis rules.
    Generates human-readable insights and improvement tips.
    """

    def __init__(self):
        self.patterns = []
        self.tips     = []
        self.warnings = []
        self.positives = []

    def analyze(self, expense_df, income_df=None):
        """Run all pattern detection algorithms."""
        if expense_df is None or expense_df.empty or len(expense_df) < 10:
            return {
                'status':  'insufficient_data',
                'message': 'Need at least 10 transactions to detect patterns.'
            }

        df = expense_df.copy()
        df['date'] = pd.to_datetime(df['date'])
        if 'month_period' not in df.columns:
            df['month_period'] = df['date'].dt.to_period('M')
        if 'day_of_week' not in df.columns:
            df['day_of_week'] = df['date'].dt.dayofweek
        if 'is_weekend' not in df.columns:
            df['is_weekend']  = (df['day_of_week'] >= 5).astype(int)

        self._detect_weekend_pattern(df)
        self._detect_monthly_trends(df)
        self._detect_top_category(df)
        self._detect_recurring_expenses(df)
        self._detect_savings_behavior(df, income_df)
        self._generate_tips()

        return {
            'status':    'success',
            'patterns':  self.patterns,
            'tips':      self.tips,
            'warnings':  self.warnings,
            'positives': self.positives,
            'total_analyzed': len(df)
        }

    def _detect_weekend_pattern(self, df):
        """Check if user spends significantly more on weekends."""
        weekend_df = df[df['is_weekend'] == 1]
        weekday_df = df[df['is_weekend'] == 0]

        if weekend_df.empty or weekday_df.empty:
            return

        w_avg = float(weekend_df['amount'].mean())
        d_avg = float(weekday_df['amount'].mean())

        if d_avg == 0:
            return

        ratio = w_avg / d_avg
        diff  = (ratio - 1) * 100

        if ratio > 1.25:
            self.patterns.append({
                'type':        'weekend_spending',
                'description': f'Weekend spending is {diff:.0f}% higher than weekdays.',
                'weekend_avg': round(w_avg, 2),
                'weekday_avg': round(d_avg, 2),
                'ratio':       round(ratio, 2),
                'severity':    'high' if diff > 50 else 'medium'
            })
            self.warnings.append(
                f'You spend {diff:.0f}% more per transaction on weekends '
                f'(avg ₹{w_avg:,.0f}) vs weekdays (avg ₹{d_avg:,.0f}). '
                f'Try setting a weekend spending limit.'
            )

        elif ratio < 0.75:
            self.positives.append(
                f'Your weekend spending (avg ₹{w_avg:,.0f}) is lower '
                f'than weekday spending — great discipline!'
            )

    def _detect_monthly_trends(self, df):
        """Detect which categories are growing or shrinking month-over-month."""
        months = sorted(df['month_period'].unique())

        if len(months) < 2:
            return

        last_month = df[df['month_period'] == months[-1]]
        prev_month = df[df['month_period'] == months[-2]]

        last_by_cat = last_month.groupby('category_name')['amount'].sum()
        prev_by_cat = prev_month.groupby('category_name')['amount'].sum()

        for cat in last_by_cat.index:
            last_amt = float(last_by_cat[cat])
            if cat not in prev_by_cat.index:
                continue
            prev_amt = float(prev_by_cat[cat])
            if prev_amt == 0:
                continue

            pct_change = ((last_amt - prev_amt) / prev_amt) * 100

            if pct_change > 30:
                self.patterns.append({
                    'type':          'category_increase',
                    'category':      cat,
                    'description':   f'{cat} spending up {pct_change:.0f}% this month.',
                    'last_month':    round(last_amt, 2),
                    'previous_month': round(prev_amt, 2),
                    'change_percent': round(pct_change, 1),
                    'severity':      'high' if pct_change > 75 else 'medium'
                })
                self.warnings.append(
                    f'Your {cat} spending increased by {pct_change:.0f}% '
                    f'(₹{prev_amt:,.0f} → ₹{last_amt:,.0f}). '
                    f'Review if this is expected.'
                )

            elif pct_change < -20:
                self.patterns.append({
                    'type':           'category_decrease',
                    'category':       cat,
                    'description':    f'{cat} spending down {abs(pct_change):.0f}%.',
                    'last_month':     round(last_amt, 2),
                    'previous_month': round(prev_amt, 2),
                    'change_percent': round(pct_change, 1),
                    'severity':       'positive'
                })
                self.positives.append(
                    f'Well done! Your {cat} spending dropped by '
                    f'{abs(pct_change):.0f}% this month.'
                )

    def _detect_top_category(self, df):
        """Identify if any single category dominates spending."""
        cat_totals  = df.groupby('category_name')['amount'].sum()
        total_spent = float(df['amount'].sum())

        if total_spent == 0 or cat_totals.empty:
            return

        top_cat    = cat_totals.idxmax()
        top_amount = float(cat_totals.max())
        top_pct    = round(top_amount / total_spent * 100, 1)

        self.patterns.append({
            'type':        'top_category',
            'category':    top_cat,
            'description': f'{top_cat} is your highest spending category '
                           f'({top_pct}% of total).',
            'amount':      round(top_amount, 2),
            'percentage':  top_pct
        })

        if top_pct > 50:
            self.warnings.append(
                f'{top_cat} makes up {top_pct}% of your spending. '
                f'Consider if this is appropriate for your goals.'
            )

    def _detect_recurring_expenses(self, df):
        """
        Detect likely recurring expenses — same category, similar amount,
        appearing in multiple months.
        """
        months     = df['month_period'].nunique()
        if months < 2:
            return

        # Group by category and check consistency
        for cat, group in df.groupby('category_name'):
            cat_months = group['month_period'].nunique()
            if cat_months < 2:
                continue

            monthly_totals = group.groupby('month_period')['amount'].sum()
            cv = float(
                monthly_totals.std() / monthly_totals.mean()
            ) if float(monthly_totals.mean()) > 0 else 1

            # Very consistent spending = likely recurring
            if cv < 0.10 and cat_months >= 2:
                avg = float(monthly_totals.mean())
                self.patterns.append({
                    'type':          'recurring',
                    'category':      cat,
                    'description':   f'{cat} appears to be a recurring expense '
                                     f'(avg ₹{avg:,.0f}/month, very consistent).',
                    'avg_monthly':   round(avg, 2),
                    'consistency':   f'{(1 - cv) * 100:.0f}%',
                    'months_seen':   cat_months
                })

    def _detect_savings_behavior(self, df, income_df):
        """Check if user is saving money based on income vs expenses."""
        if income_df is None or income_df.empty:
            return

        if 'month_period' not in income_df.columns:
            income_df = income_df.copy()
            income_df['date']         = pd.to_datetime(income_df['date'])
            income_df['month_period'] = income_df['date'].dt.to_period('M')

        common_months = set(df['month_period'].unique()) & \
                        set(income_df['month_period'].unique())

        if not common_months:
            return

        savings_rates = []
        for month in common_months:
            inc = float(
                income_df[income_df['month_period'] == month]['amount'].sum()
            )
            exp = float(
                df[df['month_period'] == month]['amount'].sum()
            )
            if inc > 0:
                rate = ((inc - exp) / inc) * 100
                savings_rates.append(rate)

        if not savings_rates:
            return

        avg_rate = float(np.mean(savings_rates))

        if avg_rate >= 20:
            self.positives.append(
                f'Excellent! You save approximately {avg_rate:.0f}% '
                f'of your income on average.'
            )
        elif avg_rate >= 10:
            self.positives.append(
                f'Good saving habit! You save approximately {avg_rate:.0f}% '
                f'of your income.'
            )
        elif avg_rate >= 0:
            self.warnings.append(
                f'You are saving only {avg_rate:.0f}% of your income. '
                f'Financial experts recommend saving at least 20%.'
            )
        else:
            self.warnings.append(
                f'Warning: You are spending {abs(avg_rate):.0f}% more than '
                f'you earn on average. Review your expenses urgently.'
            )

    def _generate_tips(self):
        """Generate actionable improvement tips based on detected patterns."""
        tips = []

        for pattern in self.patterns:
            p_type = pattern.get('type')

            if p_type == 'weekend_spending' and pattern.get('severity') != 'positive':
                tips.append(
                    f"💡 Set a weekend spending limit to control your "
                    f"{pattern['ratio']:.1f}x higher weekend expenses."
                )

            elif p_type == 'category_increase':
                tips.append(
                    f"💡 Your {pattern['category']} spending rose "
                    f"{pattern['change_percent']:.0f}% — consider "
                    f"setting a stricter category budget."
                )

            elif p_type == 'top_category' and pattern.get('percentage', 0) > 40:
                tips.append(
                    f"💡 {pattern['category']} is {pattern['percentage']}% "
                    f"of your spending. Look for ways to reduce this category."
                )

            elif p_type == 'recurring':
                tips.append(
                    f"💡 Your {pattern['category']} is a recurring "
                    f"₹{pattern['avg_monthly']:,.0f}/month expense. "
                    f"Check if you can negotiate or reduce this."
                )

        if not tips:
            tips.append(
                '✅ Your spending patterns look balanced. '
                'Keep maintaining your current habits!'
            )

        self.tips = tips


def detect_spending_patterns(expense_data, income_data=None):
    """
    Standalone function interface.
    """
    if not expense_data or len(expense_data) < 10:
        return {
            'status':  'insufficient_data',
            'message': 'Need at least 10 transactions to detect patterns.',
            'patterns': [], 'tips': [], 'warnings': [], 'positives': []
        }

    exp_df = pd.DataFrame(expense_data)
    exp_df['date'] = pd.to_datetime(exp_df['date'])

    inc_df = None
    if income_data:
        inc_df = pd.DataFrame(income_data)
        inc_df['date'] = pd.to_datetime(inc_df['date'])

    detector = PatternDetector()
    return detector.analyze(exp_df, inc_df)