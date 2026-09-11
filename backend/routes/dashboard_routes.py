# backend/routes/dashboard_routes.py
# Provides complete dashboard summary data

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.dashboard_service import get_dashboard_summary

dashboard_bp = Blueprint("dashboard", __name__)


# GET DASHBOARD — GET /api/dashboard/summary
@dashboard_bp.route("/api/dashboard/summary", methods=["GET"])
@jwt_required()
def get_dashboard():
    user_id = int(get_jwt_identity())

    try:
        data = get_dashboard_summary(user_id)

        return jsonify({
            "status": "success",
            "data": data
        }), 200

    except Exception:
        return jsonify({
            "error": "Failed to load dashboard"
        }), 500