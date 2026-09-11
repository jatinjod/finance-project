# backend/models/savings_goal.py
# Represents savings targets created by users

from datetime import datetime, timezone

from extensions import db


class SavingsGoal(db.Model):
    __tablename__ = 'savings_goals'

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

    name = db.Column(
        db.String(150),
        nullable=False
    )

    target_amount = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    saved_amount = db.Column(
        db.Numeric(12, 2),
        default=0.00,
        nullable=False
    )

    deadline = db.Column(
        db.Date,
        nullable=True
    )

    is_complete = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # ========================================================
    # API SERIALIZATION
    # ========================================================

    def to_dict(self):

        target = float(
            self.target_amount
        )

        saved = float(
            self.saved_amount
        )

        progress = (
            round(
                (saved / target) * 100,
                2
            )
            if target > 0
            else 0
        )

        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'target_amount': target,
            'saved_amount': saved,
            'remaining_amount': round(
                max(target - saved, 0),
                2
            ),
            'progress_percentage': min(
                progress,
                100
            ),
            'deadline': (
                self.deadline.isoformat()
                if self.deadline
                else None
            ),
            'is_complete': self.is_complete,
            'created_at': (
                self.created_at.isoformat()
                if self.created_at
                else None
            )
        }

    def __repr__(self):
        return f'<SavingsGoal {self.name}>'