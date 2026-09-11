# backend/models/ai_prediction.py
# Stores AI-generated prediction results

from datetime import datetime, timezone

from extensions import db


class AIPrediction(db.Model):
    __tablename__ = 'ai_predictions'

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            'users.id',
            ondelete='CASCADE'
        ),
        nullable=False
    )

    prediction_type = db.Column(
        db.Enum(
            'expense_pred',
            'budget_rec',
            'pattern',
            'anomaly',
            'tip'
        ),
        nullable=False
    )

    prediction_data = db.Column(
        db.JSON,
        nullable=False
    )

    generated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'prediction_type': self.prediction_type,
            'prediction_data': self.prediction_data,
            'generated_at': (
                self.generated_at.isoformat()
                if self.generated_at
                else None
            )
        }

    def __repr__(self):
        return (
            f'<AIPrediction [{self.prediction_type}] '
            f'for user {self.user_id}>'
        )