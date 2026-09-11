# backend/models/password_reset_token.py
# Stores secure, single-use password reset tokens

from datetime import datetime, timezone

from extensions import db


def utc_now_naive():
    """
    Return current UTC time without timezone info.

    MySQL DATETIME does not store timezone information, so the
    application consistently stores UTC as a naive datetime.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    token_hash = db.Column(
        db.String(64),
        nullable=False,
        unique=True,
        index=True
    )

    created_at = db.Column(
        db.DateTime,
        default=utc_now_naive,
        nullable=False
    )

    expires_at = db.Column(
        db.DateTime,
        nullable=False,
        index=True
    )

    used_at = db.Column(
        db.DateTime,
        nullable=True
    )

    def is_valid(self):
        now = utc_now_naive()

        return (
            self.used_at is None
            and self.expires_at > now
        )

    def __repr__(self):
        return (
            f"<PasswordResetToken "
            f"user={self.user_id} "
            f"valid={self.is_valid()}>"
        )