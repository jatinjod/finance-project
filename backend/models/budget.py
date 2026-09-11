# backend/models/budget.py
# Represents monthly budget limits set by users

from datetime import datetime, timezone

from extensions import db


class Budget(db.Model):
    __tablename__ = 'budgets'

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
            ondelete='SET NULL'
        ),
        nullable=True
    )

    category = db.relationship(
        'Category',
        backref='budgets',
        lazy=True
    )

    month = db.Column(
        db.Date,
        nullable=False
    )

    amount = db.Column(
        db.Numeric(12, 2),
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

    # One budget per user/category/month
    __table_args__ = (
        db.UniqueConstraint(
            'user_id',
            'category_id',
            'month',
            name='uq_budget_user_category_month'
        ),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'category_id': self.category_id,
            'category_name': (
                self.category.name
                if self.category
                else 'Overall'
            ),
            'month': (
                self.month.isoformat()
                if self.month
                else None
            ),
            'amount': float(self.amount),
            'created_at': (
                self.created_at.isoformat()
                if self.created_at
                else None
            )
        }

    def __repr__(self):
        return (
            f'<Budget {self.amount} for {self.month}>'
        )