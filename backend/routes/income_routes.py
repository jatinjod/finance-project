# backend/routes/income_routes.py
# Handles all income record CRUD operations

from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models.income import Income
from models.category import Category

income_bp = Blueprint('income', __name__)


# ─────────────────────────────────────────────
# GET ALL INCOME — GET /api/income
# ─────────────────────────────────────────────
@income_bp.route('/api/income', methods=['GET'])
@jwt_required()
def get_income():
    user_id     = int(get_jwt_identity())
    category_id = request.args.get('category_id', type=int)
    month       = request.args.get('month', type=int)
    year        = request.args.get('year', type=int)
    start_date  = request.args.get('start_date')
    end_date    = request.args.get('end_date')
    page        = request.args.get('page', 1, type=int)
    per_page    = request.args.get('per_page', 20, type=int)

    query = Income.query.filter_by(user_id=user_id)

    # Apply filters
    if category_id:
        query = query.filter_by(category_id=category_id)

    if month and year:
        query = query.filter(
            db.extract('month', Income.date) == month,
            db.extract('year',  Income.date) == year
        )

    if start_date:
        try:
            sd    = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Income.date >= sd)
        except ValueError:
            return jsonify({"error": "Invalid start_date. Use YYYY-MM-DD"}), 400

    if end_date:
        try:
            ed    = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Income.date <= ed)
        except ValueError:
            return jsonify({"error": "Invalid end_date. Use YYYY-MM-DD"}), 400

    query      = query.order_by(Income.date.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "status": "success",
        "data":   [i.to_dict() for i in pagination.items],
        "pagination": {
            "total":        pagination.total,
            "pages":        pagination.pages,
            "current_page": page,
            "per_page":     per_page
        }
    }), 200


# ─────────────────────────────────────────────
# ADD INCOME — POST /api/income
# ─────────────────────────────────────────────
@income_bp.route('/api/income', methods=['POST'])
@jwt_required()
def add_income():
    user_id = int(get_jwt_identity())
    data    = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    amount      = data.get('amount')
    category_id = data.get('category_id')
    date_str    = data.get('date')
    note        = data.get('note', '').strip()

    # Validate required fields
    if amount is None:
        return jsonify({"error": "Amount is required"}), 400
    if not category_id:
        return jsonify({"error": "Category is required"}), 400
    if not date_str:
        return jsonify({"error": "Date is required"}), 400

    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({"error": "Amount must be greater than zero"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid amount value"}), 400

    try:
        income_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    # Validate category exists, is income type, and belongs to user or is default
    category = Category.query.filter(
        Category.id   == category_id,
        Category.type == 'income',
        (Category.user_id == None) | (Category.user_id == user_id)
    ).first()

    if not category:
        return jsonify({"error": "Invalid income category"}), 400

    new_income = Income(
        user_id=user_id,
        category_id=category_id,
        amount=amount,
        date=income_date,
        note=note if note else None
    )

    try:
        db.session.add(new_income)
        db.session.commit()
        return jsonify({
            "status":  "success",
            "message": "Income added successfully",
            "data":    new_income.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to add income"}), 500


# ─────────────────────────────────────────────
# UPDATE INCOME — PUT /api/income/<id>
# ─────────────────────────────────────────────
@income_bp.route('/api/income/<int:income_id>', methods=['PUT'])
@jwt_required()
def update_income(income_id):
    user_id = int(get_jwt_identity())
    income  = Income.query.filter_by(id=income_id, user_id=user_id).first()

    if not income:
        return jsonify({"error": "Income record not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    if 'amount' in data:
        try:
            amount = float(data['amount'])
            if amount <= 0:
                return jsonify({"error": "Amount must be greater than zero"}), 400
            income.amount = amount
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid amount"}), 400

    if 'category_id' in data:
        category = Category.query.filter(
            Category.id   == data['category_id'],
            Category.type == 'income',
            (Category.user_id == None) | (Category.user_id == user_id)
        ).first()
        if not category:
            return jsonify({"error": "Invalid income category"}), 400
        income.category_id = data['category_id']

    if 'date' in data:
        try:
            income.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    if 'note' in data:
        income.note = data['note'].strip() or None

    try:
        db.session.commit()
        return jsonify({
            "status":  "success",
            "message": "Income updated successfully",
            "data":    income.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Update failed"}), 500


# ─────────────────────────────────────────────
# DELETE INCOME — DELETE /api/income/<id>
# ─────────────────────────────────────────────
@income_bp.route('/api/income/<int:income_id>', methods=['DELETE'])
@jwt_required()
def delete_income(income_id):
    user_id = int(get_jwt_identity())
    income  = Income.query.filter_by(id=income_id, user_id=user_id).first()

    if not income:
        return jsonify({"error": "Income record not found"}), 404

    try:
        db.session.delete(income)
        db.session.commit()
        return jsonify({
            "status":  "success",
            "message": "Income deleted successfully"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Delete failed"}), 500