# backend/ml_models/anomaly_detector.py
# Enhanced anomaly detector using Isolation Forest + Z-Score + IQR

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


class AnomalyDetector:
    """
    Multi-method anomaly detector combining:
    1. Isolation Forest (ML-based)
    2. Z-Score (statistical)
    3. IQR (interquartile range)

    A transaction is flagged only if detected by at least 2 methods.
    This reduces false positives significantly.
    """

    def __init__(self, contamination=0.1):
        self.iso_forest   = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.scaler         = StandardScaler()
        self.contamination  = contamination
        self.thresholds     = {}
        self.is_fitted      = False

    def _zscore_detect(self, amounts, threshold=2.5):
        """Flag amounts more than `threshold` std devs from mean."""
        mean = np.mean(amounts)
        std  = np.std(amounts)
        if std == 0:
            return np.zeros(len(amounts), dtype=bool)
        z_scores = np.abs((amounts - mean) / std)
        return z_scores > threshold

    def _iqr_detect(self, amounts, multiplier=1.5):
        """Flag amounts beyond Q3 + multiplier * IQR."""
        q1  = np.percentile(amounts, 25)
        q3  = np.percentile(amounts, 75)
        iqr = q3 - q1
        upper_bound = q3 + multiplier * iqr
        return amounts > upper_bound

    def fit_predict(self, expense_df):
        """
        Run all three anomaly detection methods on expense data.
        Returns the original df with anomaly columns added.
        """
        if expense_df.empty or len(expense_df) < 10:
            return expense_df, []

        df      = expense_df.copy()
        amounts = df['amount'].values

        # ── Method 1: Isolation Forest ─────────
        X_scaled       = self.scaler.fit_transform(amounts.reshape(-1, 1))
        iso_labels     = self.iso_forest.fit_predict(X_scaled)
        df['iso_flag'] = (iso_labels == -1).astype(int)

        # ── Method 2: Z-Score ──────────────────
        df['zscore_flag'] = self._zscore_detect(amounts).astype(int)

        # ── Method 3: IQR ──────────────────────
        df['iqr_flag'] = self._iqr_detect(amounts).astype(int)

        # ── Consensus: flag if 2+ methods agree ─
        df['anomaly_score'] = (
            df['iso_flag'] + df['zscore_flag'] + df['iqr_flag']
        )
        df['is_anomaly'] = (df['anomaly_score'] >= 2).astype(int)

        # Store thresholds
        q3  = float(np.percentile(amounts, 75))
        iqr = float(np.percentile(amounts, 75) - np.percentile(amounts, 25))
        self.thresholds = {
            'mean':       round(float(np.mean(amounts)), 2),
            'std':        round(float(np.std(amounts)), 2),
            'q1':         round(float(np.percentile(amounts, 25)), 2),
            'q3':         round(q3, 2),
            'iqr_upper':  round(q3 + 1.5 * iqr, 2),
            'zscore_threshold': 2.5
        }

        self.is_fitted = True

        # Build anomaly list
        anomalies_df = df[df['is_anomaly'] == 1].copy()
        anomalies    = []

        for _, row in anomalies_df.iterrows():
            methods = []
            if row['iso_flag']:    methods.append('Isolation Forest')
            if row['zscore_flag']: methods.append('Z-Score')
            if row['iqr_flag']:    methods.append('IQR')

            anomalies.append({
                'id':            int(row.get('id', 0)),
                'date':          str(row['date'].date()) if hasattr(row['date'], 'date') else str(row['date']),
                'category_name': str(row.get('category_name', 'Unknown')),
                'amount':        round(float(row['amount']), 2),
                'note':          str(row.get('note', '')),
                'anomaly_score': int(row['anomaly_score']),
                'detected_by':   methods,
                'reason': (
                    f"This ₹{row['amount']:,.0f} transaction is unusually high "
                    f"compared to your typical spending "
                    f"(avg: ₹{self.thresholds['mean']:,.0f})."
                )
            })

        anomalies.sort(key=lambda x: x['amount'], reverse=True)
        return df, anomalies


def detect_anomalies(expense_data):
    """
    Standalone function interface.
    """
    if not expense_data or len(expense_data) < 10:
        return {
            'status':          'insufficient_data',
            'anomalies':       [],
            'anomalies_found': 0,
            'message':         'Need at least 10 transactions for anomaly detection.'
        }

    df = pd.DataFrame(expense_data)
    df['date'] = pd.to_datetime(df['date'])

    detector     = AnomalyDetector(contamination=0.1)
    _, anomalies = detector.fit_predict(df)

    return {
        'status':          'success',
        'anomalies':       anomalies,
        'anomalies_found': len(anomalies),
        'total_checked':   len(df),
        'thresholds':      detector.thresholds,
        'methods_used':    ['Isolation Forest', 'Z-Score', 'IQR'],
        'consensus_rule':  'Flagged if detected by 2 or more methods'
    }