from datetime import datetime, timezone

from extensions import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(150),
        nullable=False,
        unique=True
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.Enum('user', 'admin'),
        default='user',
        nullable=False
    )

    profile_picture = db.Column(
        db.String(255),
        nullable=True
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
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

    expenses = db.relationship(
        'Expense',
        backref='user',
        lazy=True,
        cascade='all, delete-orphan'
    )

    income = db.relationship(
        'Income',
        backref='user',
        lazy=True,
        cascade='all, delete-orphan'
    )

    budgets = db.relationship(
        'Budget',
        backref='user',
        lazy=True,
        cascade='all, delete-orphan'
    )

    savings_goals = db.relationship(
        'SavingsGoal',
        backref='user',
        lazy=True,
        cascade='all, delete-orphan'
    )

    notifications = db.relationship(
        'Notification',
        backref='user',
        lazy=True,
        cascade='all, delete-orphan'
    )

    ai_predictions = db.relationship(
        'AIPrediction',
        backref='user',
        lazy=True,
        cascade='all, delete-orphan'
    )

    categories = db.relationship(
        'Category',
        backref='user',
        lazy=True,
        cascade='all, delete-orphan',
        foreign_keys='Category.user_id'
    )

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'profile_picture': self.profile_picture,
            'is_active': self.is_active,
            'created_at': (
                self.created_at.isoformat()
                if self.created_at
                else None
            )
        }

    def __repr__(self):
        return f'<User {self.email}>'