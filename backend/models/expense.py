# backend/models/expense.py
# Represents expense transactions

from datetime import datetime, timezone

from extensions import db


class Expense(db.Model):
    __tablename__ = 'expenses'

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

    category_id = db.Column(
        db.Integer,
        db.ForeignKey(
            'categories.id',
            ondelete='RESTRICT'
        ),
        nullable=False
    )

    amount = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    date = db.Column(
        db.Date,
        nullable=False
    )

    note = db.Column(
        db.String(255),
        nullable=True
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

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'category_id': self.category_id,
            'category_name': (
                self.category.name
                if self.category
                else None
            ),
            'amount': float(self.amount),
            'date': (
                self.date.isoformat()
                if self.date
                else None
            ),
            'note': self.note,
            'created_at': (
                self.created_at.isoformat()
                if self.created_at
                else None
            )
        }

    def __repr__(self):
        return (
            f'<Expense {self.amount} on {self.date}>'
        )