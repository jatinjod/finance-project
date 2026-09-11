# backend/routes/admin_routes.py
# Admin-only routes for user and system management

from functools import wraps

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
    get_jwt
)

from extensions import db
from models.user import User
from models.income import Income
from models.expense import Expense


admin_bp = Blueprint("admin", __name__)


# ============================================================
# ADMIN AUTHORIZATION
# ============================================================

def admin_required(fn):
    """
    Allow access only to authenticated admin users.
    """

    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):

        claims = get_jwt()

        if claims.get("role") != "admin":
            return jsonify({
                "error": "Admin access required"
            }), 403

        return fn(*args, **kwargs)

    return wrapper


# ============================================================
# GET ALL USERS
# GET /api/admin/users
# ============================================================

@admin_bp.route(
    "/api/admin/users",
    methods=["GET"]
)
@admin_required
def get_all_users():

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

    search = request.args.get(
        "q",
        "",
        type=str
    ).strip()


    # --------------------------------------------------------
    # SAFE PAGINATION
    # --------------------------------------------------------

    if page < 1:
        page = 1

    if per_page < 1:
        per_page = 20

    if per_page > 100:
        per_page = 100


    # --------------------------------------------------------
    # USER QUERY
    # --------------------------------------------------------

    query = User.query.filter_by(
        role="user"
    )


    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    if search:

        query = query.filter(
            db.or_(
                User.name.ilike(
                    f"%{search}%"
                ),
                User.email.ilike(
                    f"%{search}%"
                )
            )
        )


    # --------------------------------------------------------
    # PAGINATION
    # --------------------------------------------------------

    pagination = (
        query
        .order_by(
            User.created_at.desc()
        )
        .paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
    )


    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    users = []

    for user in pagination.items:

        user_data = user.to_dict()

        # Keep list endpoint lightweight.
        # Detailed transaction statistics are loaded
        # when admin opens a specific user.
        users.append(
            user_data
        )


    return jsonify({
        "status": "success",
        "data": users,
        "pagination": {
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": pagination.page,
            "per_page": pagination.per_page
        }
    }), 200


# ============================================================
# GET USER DETAIL
# GET /api/admin/users/<id>
# ============================================================

@admin_bp.route(
    "/api/admin/users/<int:user_id>",
    methods=["GET"]
)
@admin_required
def get_user_detail(user_id):

    # --------------------------------------------------------
    # FIND NORMAL USER
    # --------------------------------------------------------

    user = User.query.filter_by(
        id=user_id,
        role="user"
    ).first()


    if not user:

        return jsonify({
            "error": "User not found"
        }), 404


    # --------------------------------------------------------
    # COUNT USER INCOME RECORDS
    # --------------------------------------------------------

    income_count = (
        db.session
        .query(
            db.func.count(
                Income.id
            )
        )
        .filter(
            Income.user_id == user.id
        )
        .scalar()
        or 0
    )


    # --------------------------------------------------------
    # COUNT USER EXPENSE RECORDS
    # --------------------------------------------------------

    expense_count = (
        db.session
        .query(
            db.func.count(
                Expense.id
            )
        )
        .filter(
            Expense.user_id == user.id
        )
        .scalar()
        or 0
    )


    # --------------------------------------------------------
    # TOTAL TRANSACTIONS
    # --------------------------------------------------------

    transaction_count = (
        income_count +
        expense_count
    )


    # --------------------------------------------------------
    # USER RESPONSE
    # IMPORTANT:
    # Frontend expects statistics under `stats`.
    # We also keep old top-level fields for compatibility.
    # --------------------------------------------------------

    user_data = user.to_dict()

    user_data["stats"] = {
        "income_records": int(
            income_count
        ),
        "expense_records": int(
            expense_count
        ),
        "total_records": int(
            transaction_count
        )
    }

    # Backward-compatible fields
    user_data["income_count"] = int(
        income_count
    )

    user_data["expense_count"] = int(
        expense_count
    )

    user_data["transaction_count"] = int(
        transaction_count
    )


    return jsonify({
        "status": "success",
        "data": user_data
    }), 200


# ============================================================
# TOGGLE USER STATUS
# PUT /api/admin/users/<id>/deactivate
# ============================================================

@admin_bp.route(
    "/api/admin/users/<int:user_id>/deactivate",
    methods=["PUT"]
)
@admin_required
def toggle_user_status(user_id):

    user = User.query.filter_by(
        id=user_id,
        role="user"
    ).first()


    if not user:

        return jsonify({
            "error": "User not found"
        }), 404


    # Toggle status
    user.is_active = not bool(
        user.is_active
    )


    action = (
        "activated"
        if user.is_active
        else "deactivated"
    )


    try:

        db.session.commit()

        return jsonify({
            "status": "success",
            "message": (
                f"User {action} successfully"
            ),
            "data": user.to_dict()
        }), 200


    except Exception:

        db.session.rollback()

        return jsonify({
            "error": "Update failed"
        }), 500


# ============================================================
# DELETE USER
# DELETE /api/admin/users/<id>
# ============================================================

@admin_bp.route(
    "/api/admin/users/<int:user_id>",
    methods=["DELETE"]
)
@admin_required
def delete_user(user_id):

    current_admin_id = int(
        get_jwt_identity()
    )


    # --------------------------------------------------------
    # NEVER DELETE CURRENT ADMIN
    # --------------------------------------------------------

    if user_id == current_admin_id:

        return jsonify({
            "error": (
                "Cannot delete your own admin account"
            )
        }), 400


    # --------------------------------------------------------
    # ONLY NORMAL USERS
    # --------------------------------------------------------

    user = User.query.filter_by(
        id=user_id,
        role="user"
    ).first()


    if not user:

        return jsonify({
            "error": "User not found"
        }), 404


    try:

        db.session.delete(
            user
        )

        db.session.commit()


        return jsonify({
            "status": "success",
            "message": (
                "User and all their data "
                "deleted successfully"
            )
        }), 200


    except Exception:

        db.session.rollback()

        return jsonify({
            "error": "Delete failed"
        }), 500


# ============================================================
# SYSTEM STATS
# GET /api/admin/stats
# ============================================================

@admin_bp.route(
    "/api/admin/stats",
    methods=["GET"]
)
@admin_required
def get_system_stats():

    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

    total_users = (
        User.query
        .filter_by(
            role="user"
        )
        .count()
    )


    active_users = (
        User.query
        .filter_by(
            role="user",
            is_active=True
        )
        .count()
    )


    inactive_users = (
        total_users -
        active_users
    )


    # --------------------------------------------------------
    # INCOME RECORDS
    # --------------------------------------------------------

    total_income_records = (
        db.session
        .query(
            db.func.count(
                Income.id
            )
        )
        .scalar()
        or 0
    )


    # --------------------------------------------------------
    # EXPENSE RECORDS
    # --------------------------------------------------------

    total_expense_records = (
        db.session
        .query(
            db.func.count(
                Expense.id
            )
        )
        .scalar()
        or 0
    )


    # --------------------------------------------------------
    # TOTAL TRANSACTIONS
    # --------------------------------------------------------

    total_transactions = (
        total_income_records +
        total_expense_records
    )


    return jsonify({
        "status": "success",
        "data": {

            "total_users":
                int(total_users),

            "active_users":
                int(active_users),

            "inactive_users":
                int(inactive_users),

            "total_income_records":
                int(total_income_records),

            "total_expense_records":
                int(total_expense_records),

            "total_transactions":
                int(total_transactions)
        }
    }), 200