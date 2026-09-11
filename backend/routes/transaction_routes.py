# backend/routes/transaction_routes.py
# Combined transaction history (income + expenses together) with search and filter

import math
from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models.income import Income
from models.expense import Expense

transaction_bp = Blueprint('transactions', __name__)


# ─────────────────────────────────────────────
# GET ALL TRANSACTIONS — GET /api/transactions
# ─────────────────────────────────────────────
@transaction_bp.route('/api/transactions', methods=['GET'])
@jwt_required()
def get_transactions():
    user_id    = int(get_jwt_identity())
    trans_type  = request.args.get('type', 'all')   # 'income', 'expense', 'all'
    category_id = request.args.get('category_id', type=int)
    start_date  = request.args.get('start_date')
    end_date    = request.args.get('end_date')
    keyword     = request.args.get('q', '').strip()
    month       = request.args.get('month', type=int)
    year        = request.args.get('year', type=int)
    page        = request.args.get('page', 1, type=int)
    per_page    = request.args.get('per_page', 20, type=int)

    results = []

    # ── Fetch Income ──────────────────────────
    if trans_type in ('income', 'all'):
        income_query = Income.query.filter_by(user_id=user_id)

        if category_id:
            income_query = income_query.filter_by(category_id=category_id)
        if month and year:
            income_query = income_query.filter(
                db.extract('month', Income.date) == month,
                db.extract('year',  Income.date) == year
            )
        if start_date:
            try:
                sd = datetime.strptime(start_date, '%Y-%m-%d').date()
                income_query = income_query.filter(Income.date >= sd)
            except ValueError:
                pass
        if end_date:
            try:
                ed = datetime.strptime(end_date, '%Y-%m-%d').date()
                income_query = income_query.filter(Income.date <= ed)
            except ValueError:
                pass
        if keyword:
            income_query = income_query.filter(
                Income.note.ilike(f'%{keyword}%')
            )

        for i in income_query.all():
            t = i.to_dict()
            t['transaction_type'] = 'income'
            results.append(t)

    # ── Fetch Expenses ────────────────────────
    if trans_type in ('expense', 'all'):
        expense_query = Expense.query.filter_by(user_id=user_id)

        if category_id:
            expense_query = expense_query.filter_by(category_id=category_id)
        if month and year:
            expense_query = expense_query.filter(
                db.extract('month', Expense.date) == month,
                db.extract('year',  Expense.date) == year
            )
        if start_date:
            try:
                sd = datetime.strptime(start_date, '%Y-%m-%d').date()
                expense_query = expense_query.filter(Expense.date >= sd)
            except ValueError:
                pass
        if end_date:
            try:
                ed = datetime.strptime(end_date, '%Y-%m-%d').date()
                expense_query = expense_query.filter(Expense.date <= ed)
            except ValueError:
                pass
        if keyword:
            expense_query = expense_query.filter(
                Expense.note.ilike(f'%{keyword}%')
            )

        for e in expense_query.all():
            t = e.to_dict()
            t['transaction_type'] = 'expense'
            results.append(t)

    # Sort combined results by date (newest first)
    results.sort(key=lambda x: x['date'] or '', reverse=True)

    # Manual pagination
    total     = len(results)
    start_idx = (page - 1) * per_page
    end_idx   = start_idx + per_page
    paginated = results[start_idx:end_idx]
    pages     = math.ceil(total / per_page) if per_page > 0 else 1

    return jsonify({
        "status": "success",
        "data":   paginated,
        "pagination": {
            "total":        total,
            "pages":        pages,
            "current_page": page,
            "per_page":     per_page
        }
    }), 200