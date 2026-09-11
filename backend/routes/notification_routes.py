# backend/routes/notification_routes.py
# Handles viewing and marking notifications as read

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models.notification import Notification

notification_bp = Blueprint("notifications", __name__)


# ─────────────────────────────────────────────
# GET NOTIFICATIONS — GET /api/notifications
# ─────────────────────────────────────────────
@notification_bp.route("/api/notifications", methods=["GET"])
@jwt_required()
def get_notifications():
    user_id = int(get_jwt_identity())
    is_read = request.args.get("is_read")

    query = Notification.query.filter_by(user_id=user_id)

    if is_read == "false":
        query = query.filter_by(is_read=False)
    elif is_read == "true":
        query = query.filter_by(is_read=True)

    notifications = (
        query
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )

    unread_count = Notification.query.filter_by(
        user_id=user_id,
        is_read=False
    ).count()

    return jsonify({
        "status": "success",
        "data": [notification.to_dict() for notification in notifications],
        "unread_count": unread_count
    }), 200


# ─────────────────────────────────────────────
# MARK ONE AS READ — PUT /api/notifications/<id>/read
# ─────────────────────────────────────────────
@notification_bp.route(
    "/api/notifications/<int:notif_id>/read",
    methods=["PUT"]
)
@jwt_required()
def mark_as_read(notif_id):
    user_id = int(get_jwt_identity())

    notification = Notification.query.filter_by(
        id=notif_id,
        user_id=user_id
    ).first()

    if not notification:
        return jsonify({
            "error": "Notification not found"
        }), 404

    notification.is_read = True

    try:
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Notification marked as read"
        }), 200

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Update failed"
        }), 500


# ─────────────────────────────────────────────
# MARK ALL AS READ — PUT /api/notifications/read-all
# ─────────────────────────────────────────────
@notification_bp.route(
    "/api/notifications/read-all",
    methods=["PUT"]
)
@jwt_required()
def mark_all_as_read():
    user_id = int(get_jwt_identity())

    try:
        Notification.query.filter_by(
            user_id=user_id,
            is_read=False
        ).update(
            {"is_read": True},
            synchronize_session=False
        )

        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "All notifications marked as read"
        }), 200

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Update failed"
        }), 500