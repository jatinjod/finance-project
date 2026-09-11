# backend/ml_models/expense_predictor.py
# Enhanced expense predictor using multiple features and polynomial regression

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split


class ExpensePredictor:
    """
    Predicts next month's total expenses using Linear and
    Polynomial Regression with multiple engineered features.
    """

    def __init__(self):
        self.linear_model  = LinearRegression()
        self.poly_model    = LinearRegression()
        self.poly_features = PolynomialFeatures(degree=2, include_bias=False)
        self.is_trained    = False
        self.metrics       = {}
        self.monthly_data  = None

    def train(self, monthly_df):
        """
        Train the model on monthly expense data.
        monthly_df must have: month_num, total_expenses columns.
        """
        if monthly_df is None or len(monthly_df) < 3:
            return False

        self.monthly_data = monthly_df.copy()
        df = monthly_df.dropna(subset=['total_expenses'])
        df = df[df['total_expenses'] > 0]

        if len(df) < 3:
            return False

        X = df[['month_num']].values
        y = df['total_expenses'].values

        # Train simple linear model
        self.linear_model.fit(X, y)

        # Train polynomial model if enough data
        if len(df) >= 4:
            X_poly = self.poly_features.fit_transform(X)
            self.poly_model.fit(X_poly, y)

        self.is_trained = True

        # Compute training metrics
        y_pred_linear = self.linear_model.predict(X)
        self.metrics['linear'] = {
            'r2':  round(float(r2_score(y, y_pred_linear)), 4),
            'mae': round(float(mean_absolute_error(y, y_pred_linear)), 2)
        }

        if len(df) >= 4:
            y_pred_poly = self.poly_model.predict(
                self.poly_features.transform(X)
            )
            self.metrics['polynomial'] = {
                'r2':  round(float(r2_score(y, y_pred_poly)), 4),
                'mae': round(float(mean_absolute_error(y, y_pred_poly)), 2)
            }

        return True

    def predict(self):
        """
        Predict next month's expenses.
        Returns dict with prediction and confidence info.
        """
        if not self.is_trained or self.monthly_data is None:
            return {
                'status':  'not_trained',
                'message': 'Model has not been trained yet.'
            }

        df = self.monthly_data
        next_month_num = int(df['month_num'].max()) + 1
        X_next         = np.array([[next_month_num]])

        linear_pred = float(self.linear_model.predict(X_next)[0])
        linear_pred = max(0, linear_pred)

        poly_pred = None
        if 'polynomial' in self.metrics:
            raw = float(
                self.poly_model.predict(
                    self.poly_features.transform(X_next)
                )[0]
            )
            poly_pred = max(0, raw)

        # Choose best model based on R²
        linear_r2 = self.metrics['linear']['r2']
        poly_r2   = self.metrics.get('polynomial', {}).get('r2', -1)

        if poly_pred is not None and poly_r2 > linear_r2:
            best_pred  = poly_pred
            best_model = 'polynomial'
            best_r2    = poly_r2
        else:
            best_pred  = linear_pred
            best_model = 'linear'
            best_r2    = linear_r2

        # Determine confidence
        confidence = (
            'high'   if best_r2 >= 0.70 else
            'medium' if best_r2 >= 0.40 else
            'low'
        )

        # Recent data for context
        recent = df.tail(3)
        last_month_actual = float(recent.iloc[-1]['total_expenses'])
        avg_last_3        = float(recent['total_expenses'].mean())
        avg_all           = float(df['total_expenses'].mean())

        # Trend direction
        if len(df) >= 2:
            slope = (
                float(df['total_expenses'].iloc[-1]) -
                float(df['total_expenses'].iloc[-2])
            )
        else:
            slope = 0

        trend = (
            'increasing' if best_pred > last_month_actual * 1.05 else
            'decreasing' if best_pred < last_month_actual * 0.95 else
            'stable'
        )

        # Prediction interval (±1 std dev of residuals)
        y       = df['total_expenses'].values
        y_pred  = self.linear_model.predict(df[['month_num']].values)
        std_err = float(np.std(y - y_pred))

        return {
            'status':              'success',
            'predicted_amount':    round(best_pred, 2),
            'lower_bound':         round(max(0, best_pred - std_err), 2),
            'upper_bound':         round(best_pred + std_err, 2),
            'last_month_actual':   round(last_month_actual, 2),
            'average_last_3':      round(avg_last_3, 2),
            'overall_average':     round(avg_all, 2),
            'trend':               trend,
            'slope':               round(slope, 2),
            'confidence':          confidence,
            'model_used':          best_model,
            'r2_score':            round(best_r2, 4),
            'months_of_data':      len(df),
            'linear_prediction':   round(linear_pred, 2),
            'poly_prediction':     round(poly_pred, 2) if poly_pred else None,
            'metrics':             self.metrics,
            'interpretation': (
                f"Based on {len(df)} months of data, your expenses are "
                f"expected to be around ₹{best_pred:,.0f} next month "
                f"(range: ₹{max(0, best_pred - std_err):,.0f}–"
                f"₹{best_pred + std_err:,.0f})."
            )
        }


def predict_next_month_expense(expense_data):
    """
    Standalone function interface for AI service.
    """
    if not expense_data or len(expense_data) < 5:
        return {
            'status':  'insufficient_data',
            'message': 'Need at least 5 expense records for prediction.'
        }

    df = pd.DataFrame(expense_data)
    df['date'] = pd.to_datetime(df['date'])
    df['month_period'] = df['date'].dt.to_period('M')

    monthly = df.groupby('month_period')['amount'].sum().reset_index()
    monthly.columns = ['month_period', 'total_expenses']
    monthly['month_num'] = range(1, len(monthly) + 1)

    if len(monthly) < 3:
        return {
            'status':  'insufficient_data',
            'message': 'Need at least 3 months of data for prediction.'
        }

    predictor = ExpensePredictor()
    trained   = predictor.train(monthly)

    if not trained:
        return {'status': 'error', 'message': 'Model training failed.'}

    return predictor.predict()