# backend/routes/category_routes.py
# Handles income and expense category management

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models.category import Category
from models.income import Income
from models.expense import Expense

category_bp = Blueprint("categories", __name__)


# -------------------------------------------------
# GET CATEGORIES — GET /api/categories
# -------------------------------------------------
@category_bp.route("/api/categories", methods=["GET"])
@jwt_required()
def get_categories():
    user_id = int(get_jwt_identity())
    cat_type = request.args.get("type")

    query = Category.query.filter(
        db.or_(
            Category.user_id.is_(None),
            Category.user_id == user_id
        )
    )

    if cat_type in ("income", "expense"):
        query = query.filter(Category.type == cat_type)

    categories = query.order_by(
        Category.is_default.desc(),
        Category.name.asc()
    ).all()

    return jsonify({
        "status": "success",
        "data": [category.to_dict() for category in categories]
    }), 200


# -------------------------------------------------
# CREATE CATEGORY — POST /api/categories
# -------------------------------------------------
@category_bp.route("/api/categories", methods=["POST"])
@jwt_required()
def create_category():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "No data provided"}), 400

    name = str(data.get("name", "")).strip()
    cat_type = data.get("type", "")

    if not name:
        return jsonify({
            "error": "Category name is required"
        }), 400

    if len(name) > 100:
        return jsonify({
            "error": "Category name must not exceed 100 characters"
        }), 400

    if cat_type not in ("income", "expense"):
        return jsonify({
            "error": "Type must be 'income' or 'expense'"
        }), 400

    # Prevent duplicate custom category for same user
    existing = Category.query.filter_by(
        user_id=user_id,
        name=name,
        type=cat_type
    ).first()

    if existing:
        return jsonify({
            "error": "Category with this name already exists"
        }), 409

    new_category = Category(
        user_id=user_id,
        name=name,
        type=cat_type,
        is_default=False
    )

    try:
        db.session.add(new_category)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Category created",
            "data": new_category.to_dict()
        }), 201

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Failed to create category"
        }), 500


# -------------------------------------------------
# UPDATE CATEGORY — PUT /api/categories/<id>
# -------------------------------------------------
@category_bp.route("/api/categories/<int:cat_id>", methods=["PUT"])
@jwt_required()
def update_category(cat_id):
    user_id = int(get_jwt_identity())

    category = Category.query.filter_by(
        id=cat_id,
        user_id=user_id
    ).first()

    if not category:
        return jsonify({
            "error": "Category not found or not authorized"
        }), 404

    if category.is_default:
        return jsonify({
            "error": "Default categories cannot be edited"
        }), 403

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "No data provided"
        }), 400

    name = str(data.get("name", "")).strip()

    if not name:
        return jsonify({
            "error": "Category name is required"
        }), 400

    if len(name) > 100:
        return jsonify({
            "error": "Category name must not exceed 100 characters"
        }), 400

    # Prevent duplicate custom category names
    duplicate = Category.query.filter(
        Category.user_id == user_id,
        Category.type == category.type,
        Category.name == name,
        Category.id != cat_id
    ).first()

    if duplicate:
        return jsonify({
            "error": "Category with this name already exists"
        }), 409

    category.name = name

    try:
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Category updated",
            "data": category.to_dict()
        }), 200

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Update failed"
        }), 500


# -------------------------------------------------
# DELETE CATEGORY — DELETE /api/categories/<id>
# -------------------------------------------------
@category_bp.route("/api/categories/<int:cat_id>", methods=["DELETE"])
@jwt_required()
def delete_category(cat_id):
    user_id = int(get_jwt_identity())

    category = Category.query.filter_by(
        id=cat_id,
        user_id=user_id
    ).first()

    if not category:
        return jsonify({
            "error": "Category not found or not authorized"
        }), 404

    if category.is_default:
        return jsonify({
            "error": "Default categories cannot be deleted"
        }), 403

    # Check whether category is used by user's records
    expense_exists = Expense.query.filter_by(
        user_id=user_id,
        category_id=cat_id
    ).first()

    if expense_exists:
        return jsonify({
            "error": "Cannot delete: category is used in expense records"
        }), 400

    income_exists = Income.query.filter_by(
        user_id=user_id,
        category_id=cat_id
    ).first()

    if income_exists:
        return jsonify({
            "error": "Cannot delete: category is used in income records"
        }), 400

    try:
        db.session.delete(category)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Category deleted"
        }), 200

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Delete failed"
        }), 500