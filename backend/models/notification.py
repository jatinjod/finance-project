# backend/models/notification.py
# Represents system alerts and notifications sent to users

from datetime import datetime, timezone

from extensions import db


class Notification(db.Model):
    __tablename__ = 'notifications'

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

    message = db.Column(
        db.String(255),
        nullable=False
    )

    type = db.Column(
        db.Enum(
            'budget_warning',
            'budget_exceeded',
            'anomaly',
            'goal_achieved',
            'general'
        ),
        nullable=False,
        default='general'
    )

    is_read = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'message': self.message,
            'type': self.type,
            'is_read': self.is_read,
            'created_at': (
                self.created_at.isoformat()
                if self.created_at
                else None
            )
        }

    def __repr__(self):
        return (
            f'<Notification [{self.type}] '
            f'{self.message[:30]}>'
        )