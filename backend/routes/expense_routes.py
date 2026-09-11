# backend/routes/expense_routes.py
# Handles all expense record CRUD operations
# Also triggers budget threshold check after each expense

from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models.expense import Expense
from models.category import Category

expense_bp = Blueprint("expenses", __name__)


def parse_amount(value):
    """Validate and return a positive Decimal amount."""
    try:
        amount = Decimal(str(value))

        if not amount.is_finite() or amount <= 0:
            return None

        return amount

    except (InvalidOperation, TypeError, ValueError):
        return None


def parse_date(value, field_name="date"):
    """Validate YYYY-MM-DD date format."""
    try:
        return datetime.strptime(
            str(value),
            "%Y-%m-%d"
        ).date()
    except (TypeError, ValueError):
        raise ValueError(
            f"Invalid {field_name}. Use YYYY-MM-DD"
        )


def get_user_expense_category(category_id, user_id):
    """Return a valid expense category for the current user."""
    return Category.query.filter(
        Category.id == category_id,
        Category.type == "expense",
        db.or_(
            Category.user_id.is_(None),
            Category.user_id == user_id
        )
    ).first()


def check_budget_safely(user_id, expense_date, category_id):
    """
    Run budget threshold checking without breaking the
    successful expense transaction if the notification
    service has a problem.
    """
    try:
        from services.budget_service import check_budget_threshold

        check_budget_threshold(
            user_id,
            expense_date,
            category_id
        )

    except Exception:
        # Budget notification is secondary.
        # The expense itself should remain successful.
        db.session.rollback()


# -------------------------------------------------
# GET ALL EXPENSES — GET /api/expenses
# -------------------------------------------------
@expense_bp.route("/api/expenses", methods=["GET"])
@jwt_required()
def get_expenses():
    user_id = int(get_jwt_identity())

    category_id = request.args.get(
        "category_id",
        type=int
    )

    month = request.args.get(
        "month",
        type=int
    )

    year = request.args.get(
        "year",
        type=int
    )

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    page = request.args.get(
        "page",
        1,
        type=int
    )

    per_page = request.args.get(
        "per_page",
        20,
        type=int
    )

    if page < 1:
        page = 1

    if per_page < 1:
        per_page = 20

    if per_page > 100:
        per_page = 100

    # IMPORTANT:
    # User can only access their own expenses.
    query = Expense.query.filter(
        Expense.user_id == user_id
    )

    if category_id:
        query = query.filter(
            Expense.category_id == category_id
        )

    # Month/year filter
    if month is not None or year is not None:

        if month is None or year is None:
            return jsonify({
                "error": "Both month and year are required"
            }), 400

        if month < 1 or month > 12:
            return jsonify({
                "error": "Invalid month"
            }), 400

        if year < 1:
            return jsonify({
                "error": "Invalid year"
            }), 400

        query = query.filter(
            db.extract(
                "month",
                Expense.date
            ) == month,

            db.extract(
                "year",
                Expense.date
            ) == year
        )

    # Start date
    if start_date:

        try:
            sd = parse_date(
                start_date,
                "start_date"
            )

            query = query.filter(
                Expense.date >= sd
            )

        except ValueError as error:
            return jsonify({
                "error": str(error)
            }), 400

    # End date
    if end_date:

        try:
            ed = parse_date(
                end_date,
                "end_date"
            )

            query = query.filter(
                Expense.date <= ed
            )

        except ValueError as error:
            return jsonify({
                "error": str(error)
            }), 400

    # Validate date range
    if start_date and end_date:

        try:
            sd = parse_date(
                start_date,
                "start_date"
            )

            ed = parse_date(
                end_date,
                "end_date"
            )

            if sd > ed:
                return jsonify({
                    "error": "start_date cannot be after end_date"
                }), 400

        except ValueError:
            pass

    query = query.order_by(
        Expense.date.desc(),
        Expense.id.desc()
    )

    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    return jsonify({
        "status": "success",
        "data": [
            expense.to_dict()
            for expense in pagination.items
        ],
        "pagination": {
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": pagination.page,
            "per_page": pagination.per_page
        }
    }), 200


# -------------------------------------------------
# ADD EXPENSE — POST /api/expenses
# -------------------------------------------------
@expense_bp.route("/api/expenses", methods=["POST"])
@jwt_required()
def add_expense():
    user_id = int(get_jwt_identity())

    data = request.get_json(
        silent=True
    )

    if not data:
        return jsonify({
            "error": "No data provided"
        }), 400

    amount_value = data.get("amount")
    category_id = data.get("category_id")
    date_str = data.get("date")
    note = data.get("note", "")

    if amount_value is None:
        return jsonify({
            "error": "Amount is required"
        }), 400

    if not category_id:
        return jsonify({
            "error": "Category is required"
        }), 400

    if not date_str:
        return jsonify({
            "error": "Date is required"
        }), 400

    amount = parse_amount(
        amount_value
    )

    if amount is None:
        return jsonify({
            "error": "Amount must be greater than zero"
        }), 400

    try:
        expense_date = parse_date(
            date_str
        )

    except ValueError as error:
        return jsonify({
            "error": str(error)
        }), 400

    category = get_user_expense_category(
        category_id,
        user_id
    )

    if not category:
        return jsonify({
            "error": "Invalid expense category"
        }), 400

    if note is None:
        note = None
    else:
        note = str(note).strip() or None

    new_expense = Expense(
        user_id=user_id,
        category_id=category.id,
        amount=amount,
        date=expense_date,
        note=note
    )

    try:
        db.session.add(new_expense)
        db.session.commit()

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Failed to add expense"
        }), 500

    # Budget notification check
    check_budget_safely(
        user_id,
        expense_date,
        category.id
    )

    return jsonify({
        "status": "success",
        "message": "Expense added successfully",
        "data": new_expense.to_dict()
    }), 201


# -------------------------------------------------
# UPDATE EXPENSE — PUT /api/expenses/<id>
# -------------------------------------------------
@expense_bp.route(
    "/api/expenses/<int:expense_id>",
    methods=["PUT"]
)
@jwt_required()
def update_expense(expense_id):

    user_id = int(
        get_jwt_identity()
    )

    # IMPORTANT:
    # Only current user's expense can be updated.
    expense = Expense.query.filter_by(
        id=expense_id,
        user_id=user_id
    ).first()

    if not expense:
        return jsonify({
            "error": "Expense not found"
        }), 404

    data = request.get_json(
        silent=True
    )

    if not data:
        return jsonify({
            "error": "No data provided"
        }), 400

    # Amount
    if "amount" in data:

        amount = parse_amount(
            data["amount"]
        )

        if amount is None:
            return jsonify({
                "error": "Amount must be greater than zero"
            }), 400

        expense.amount = amount

    # Category
    if "category_id" in data:

        try:
            category_id = int(
                data["category_id"]
            )

        except (TypeError, ValueError):
            return jsonify({
                "error": "Invalid category"
            }), 400

        category = get_user_expense_category(
            category_id,
            user_id
        )

        if not category:
            return jsonify({
                "error": "Invalid expense category"
            }), 400

        expense.category_id = category.id

    # Date
    if "date" in data:

        try:
            expense.date = parse_date(
                data["date"]
            )

        except ValueError as error:
            return jsonify({
                "error": str(error)
            }), 400

    # Note
    if "note" in data:

        note = data["note"]

        if note is None:
            expense.note = None

        else:
            expense.note = (
                str(note).strip()
                or None
            )

    try:
        db.session.commit()

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Update failed"
        }), 500

    # Re-check budget after update
    check_budget_safely(
        user_id,
        expense.date,
        expense.category_id
    )

    return jsonify({
        "status": "success",
        "message": "Expense updated successfully",
        "data": expense.to_dict()
    }), 200


# -------------------------------------------------
# DELETE EXPENSE — DELETE /api/expenses/<id>
# -------------------------------------------------
@expense_bp.route(
    "/api/expenses/<int:expense_id>",
    methods=["DELETE"]
)
@jwt_required()
def delete_expense(expense_id):

    user_id = int(
        get_jwt_identity()
    )

    # IMPORTANT:
    # User can delete ONLY their own expense.
    expense = Expense.query.filter_by(
        id=expense_id,
        user_id=user_id
    ).first()

    if not expense:
        return jsonify({
            "error": "Expense not found"
        }), 404

    try:
        db.session.delete(expense)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Expense deleted successfully"
        }), 200

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Delete failed"
        }), 500