# backend/routes/budget_routes.py
# Handles user budget management and budget status

from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models.budget import Budget
from models.category import Category
from services.budget_service import get_budget_status

budget_bp = Blueprint("budgets", __name__)


def parse_amount(value):
    """Validate and return a positive Decimal amount."""
    try:
        amount = Decimal(str(value))

        if not amount.is_finite() or amount <= 0:
            return None

        return amount

    except (InvalidOperation, TypeError, ValueError):
        return None


def parse_month_year(month_value, year_value):
    """Validate month/year and return first day of month."""
    try:
        month = int(month_value)
        year = int(year_value)

        if month < 1 or month > 12:
            return None, None

        if year < 1:
            return None, None

        first_of_month = date(year, month, 1)

        return month, first_of_month

    except (TypeError, ValueError):
        return None, None


def get_valid_expense_category(category_id, user_id):
    """Return an expense category accessible by this user."""
    return Category.query.filter(
        Category.id == category_id,
        Category.type == "expense",
        db.or_(
            Category.user_id.is_(None),
            Category.user_id == user_id
        )
    ).first()


def get_budget_for_user(budget_id, user_id):
    """Return budget only if it belongs to current user."""
    return Budget.query.filter_by(
        id=budget_id,
        user_id=user_id
    ).first()


# -------------------------------------------------
# GET BUDGET STATUS — GET /api/budget
# -------------------------------------------------
@budget_bp.route("/api/budget", methods=["GET"])
@jwt_required()
def get_budgets():
    user_id = int(get_jwt_identity())

    today = date.today()

    month = request.args.get(
        "month",
        today.month,
        type=int
    )

    year = request.args.get(
        "year",
        today.year,
        type=int
    )

    if month < 1 or month > 12:
        return jsonify({
            "error": "Invalid month"
        }), 400

    if year < 1:
        return jsonify({
            "error": "Invalid year"
        }), 400

    try:
        status = get_budget_status(
            user_id,
            year,
            month
        )

        return jsonify({
            "status": "success",
            "data": status,
            "month": month,
            "year": year
        }), 200

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Failed to fetch budget status"
        }), 500


# -------------------------------------------------
# GET BUDGET STATUS — GET /api/budget/status
# Compatibility endpoint for integration/frontend
# -------------------------------------------------
@budget_bp.route("/api/budget/status", methods=["GET"])
@jwt_required()
def get_budget_status_endpoint():
    user_id = int(get_jwt_identity())

    today = date.today()

    month = request.args.get(
        "month",
        today.month,
        type=int
    )

    year = request.args.get(
        "year",
        today.year,
        type=int
    )

    if month < 1 or month > 12:
        return jsonify({
            "error": "Invalid month"
        }), 400

    if year < 1:
        return jsonify({
            "error": "Invalid year"
        }), 400

    try:
        status = get_budget_status(
            user_id,
            year,
            month
        )

        return jsonify({
            "status": "success",
            "data": status,
            "month": month,
            "year": year
        }), 200

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Failed to fetch budget status"
        }), 500


# -------------------------------------------------
# SET / UPDATE BUDGET — POST /api/budget
# -------------------------------------------------
@budget_bp.route("/api/budget", methods=["POST"])
@jwt_required()
def set_budget():
    user_id = int(get_jwt_identity())

    data = request.get_json(
        silent=True
    )

    if not data:
        return jsonify({
            "error": "No data provided"
        }), 400

    amount_value = data.get("amount")

    if amount_value is None:
        return jsonify({
            "error": "Amount is required"
        }), 400

    amount = parse_amount(
        amount_value
    )

    if amount is None:
        return jsonify({
            "error": "Amount must be greater than zero"
        }), 400

    # Category
    category_id = data.get(
        "category_id"
    )

    if category_id in ("", 0, "0", None):
        category_id = None

    else:
        try:
            category_id = int(category_id)

        except (TypeError, ValueError):
            return jsonify({
                "error": "Invalid category ID"
            }), 400

        if category_id <= 0:
            return jsonify({
                "error": "Invalid category ID"
            }), 400

    # Month/year
    today = date.today()

    month_value = data.get(
        "month",
        today.month
    )

    year_value = data.get(
        "year",
        today.year
    )

    month, first_of_month = parse_month_year(
        month_value,
        year_value
    )

    if first_of_month is None:
        return jsonify({
            "error": "Invalid month or year"
        }), 400

    year = first_of_month.year

    # Validate category ownership/type
    if category_id is not None:

        category = get_valid_expense_category(
            category_id,
            user_id
        )

        if not category:
            return jsonify({
                "error": "Invalid expense category"
            }), 400

    # Find existing budget.
    # Overall budget has category_id = NULL.
    if category_id is None:

        existing = Budget.query.filter(
            Budget.user_id == user_id,
            Budget.category_id.is_(None),
            Budget.month == first_of_month
        ).first()

    else:

        existing = Budget.query.filter(
            Budget.user_id == user_id,
            Budget.category_id == category_id,
            Budget.month == first_of_month
        ).first()

    # Update existing budget
    if existing:

        existing.amount = amount

        try:
            db.session.commit()

            return jsonify({
                "status": "success",
                "message": "Budget updated",
                "data": existing.to_dict()
            }), 200

        except Exception:
            db.session.rollback()

            return jsonify({
                "error": "Update failed"
            }), 500

    # Create new budget
    new_budget = Budget(
        user_id=user_id,
        category_id=category_id,
        month=first_of_month,
        amount=amount
    )

    try:
        db.session.add(new_budget)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Budget set successfully",
            "data": new_budget.to_dict()
        }), 201

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Failed to set budget"
        }), 500


# -------------------------------------------------
# DELETE BUDGET — DELETE /api/budget/<id>
# -------------------------------------------------
@budget_bp.route(
    "/api/budget/<int:budget_id>",
    methods=["DELETE"]
)
@jwt_required()
def delete_budget(budget_id):
    user_id = int(get_jwt_identity())

    budget = get_budget_for_user(
        budget_id,
        user_id
    )

    if not budget:
        return jsonify({
            "error": "Budget not found"
        }), 404

    try:
        db.session.delete(budget)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Budget deleted"
        }), 200

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Delete failed"
        }), 500