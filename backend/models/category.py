# backend/models/category.py
# Represents income and expense categories

from datetime import datetime, timezone

from extensions import db


class Category(db.Model):
    __tablename__ = 'categories'

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
        nullable=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    type = db.Column(
        db.Enum(
            'income',
            'expense'
        ),
        nullable=False
    )

    is_default = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # ========================================================
    # RELATIONSHIPS
    # ========================================================

    income_records = db.relationship(
        'Income',
        backref='category',
        lazy=True
    )

    expense_records = db.relationship(
        'Expense',
        backref='category',
        lazy=True
    )

    # ========================================================
    # API SERIALIZATION
    # ========================================================

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'type': self.type,
            'is_default': self.is_default
        }

    # ========================================================
    # DEBUG REPRESENTATION
    # ========================================================

    def __repr__(self):
        return f'<Category {self.name} ({self.type})>'