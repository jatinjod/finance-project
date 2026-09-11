# backend/routes/report_routes.py
# Provides monthly, category, and trend reports

from datetime import date
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from services.report_service import (
    get_monthly_report,
    get_spending_trend,
    get_category_report
)

report_bp = Blueprint("reports", __name__)


# ─────────────────────────────────────────────
# MONTHLY REPORT — GET /api/reports/monthly
# ─────────────────────────────────────────────
@report_bp.route("/api/reports/monthly", methods=["GET"])
@jwt_required()
def monthly_report():
    user_id = int(get_jwt_identity())
    today = date.today()

    month = request.args.get("month", today.month, type=int)
    year = request.args.get("year", today.year, type=int)

    if month is None or not 1 <= month <= 12:
        return jsonify({
            "error": "Month must be between 1 and 12"
        }), 400

    if year is None or year < 1:
        return jsonify({
            "error": "Invalid year"
        }), 400

    try:
        report = get_monthly_report(user_id, year, month)

        return jsonify({
            "status": "success",
            "data": report
        }), 200

    except Exception:
        return jsonify({
            "error": "Report failed"
        }), 500


# ─────────────────────────────────────────────
# TREND REPORT — GET /api/reports/trend
# ─────────────────────────────────────────────
@report_bp.route("/api/reports/trend", methods=["GET"])
@jwt_required()
def spending_trend():
    user_id = int(get_jwt_identity())

    months = request.args.get("months", 6, type=int)

    if months is None:
        months = 6

    # Keep months between 2 and 12
    months = max(2, min(12, months))

    try:
        trend = get_spending_trend(user_id, months)

        return jsonify({
            "status": "success",
            "data": trend
        }), 200

    except Exception:
        return jsonify({
            "error": "Trend report failed"
        }), 500


# ─────────────────────────────────────────────
# CATEGORY REPORT — GET /api/reports/category
# ─────────────────────────────────────────────
@report_bp.route("/api/reports/category", methods=["GET"])
@jwt_required()
def category_report():
    user_id = int(get_jwt_identity())
    today = date.today()

    month = request.args.get("month", today.month, type=int)
    year = request.args.get("year", today.year, type=int)

    if month is None or not 1 <= month <= 12:
        return jsonify({
            "error": "Month must be between 1 and 12"
        }), 400

    if year is None or year < 1:
        return jsonify({
            "error": "Invalid year"
        }), 400

    try:
        report = get_category_report(user_id, year, month)

        return jsonify({
            "status": "success",
            "data": report
        }), 200

    except Exception:
        return jsonify({
            "error": "Category report failed"
        }), 500