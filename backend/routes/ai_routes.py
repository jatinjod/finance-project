# backend/routes/ai_routes.py
# All AI/ML API endpoints

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.ai_service import (
    run_full_ai_analysis,
    has_sufficient_data,
    get_expense_data_for_ai,
    get_income_data_for_ai,
    suggest_category_for_note,
    get_savings_projection_analysis
)

ai_bp = Blueprint('ai', __name__)


# ─────────────────────────────────────────────
# FULL AI INSIGHTS
# GET /api/ai/insights
# ─────────────────────────────────────────────
@ai_bp.route('/api/ai/insights', methods=['GET'])
@jwt_required()
def get_ai_insights():
    user_id = int(get_jwt_identity())
    try:
        insights = run_full_ai_analysis(user_id)
        return jsonify({"status": "success", "data": insights}), 200
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": f"AI analysis failed: {str(e)}"}), 500


# ─────────────────────────────────────────────
# EXPENSE PREDICTION ONLY
# GET /api/ai/prediction
# ─────────────────────────────────────────────
@ai_bp.route('/api/ai/prediction', methods=['GET'])
@jwt_required()
def get_prediction():
    user_id = int(get_jwt_identity())

    if not has_sufficient_data(user_id):
        return jsonify({
            "status":  "insufficient_data",
            "message": "Add more expenses to unlock predictions"
        }), 200

    try:
        from ml_models.expense_predictor import predict_next_month_expense
        data   = get_expense_data_for_ai(user_id)
        result = predict_next_month_expense(data)
        return jsonify({"status": "success", "data": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# SPENDING PATTERNS ONLY
# GET /api/ai/patterns
# ─────────────────────────────────────────────
@ai_bp.route('/api/ai/patterns', methods=['GET'])
@jwt_required()
def get_patterns():
    user_id = int(get_jwt_identity())

    if not has_sufficient_data(user_id):
        return jsonify({
            "status":  "insufficient_data",
            "message": "Add more expenses to detect patterns"
        }), 200

    try:
        from ml_models.pattern_detector import detect_spending_patterns
        exp_data = get_expense_data_for_ai(user_id)
        inc_data = get_income_data_for_ai(user_id)
        result   = detect_spending_patterns(exp_data, inc_data)
        return jsonify({"status": "success", "data": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# BUDGET RECOMMENDATIONS ONLY
# GET /api/ai/recommendations
# ─────────────────────────────────────────────
@ai_bp.route('/api/ai/recommendations', methods=['GET'])
@jwt_required()
def get_recommendations():
    user_id = int(get_jwt_identity())

    if not has_sufficient_data(user_id):
        return jsonify({
            "status":  "insufficient_data",
            "message": "Add more expenses for budget recommendations"
        }), 200

    try:
        from ml_models.budget_recommender import recommend_budget
        data   = get_expense_data_for_ai(user_id)
        result = recommend_budget(data)
        return jsonify({"status": "success", "data": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# ANOMALY DETECTION ONLY
# GET /api/ai/anomalies
# ─────────────────────────────────────────────
@ai_bp.route('/api/ai/anomalies', methods=['GET'])
@jwt_required()
def get_anomalies():
    user_id = int(get_jwt_identity())

    if not has_sufficient_data(user_id):
        return jsonify({
            "status":  "insufficient_data",
            "message": "Add more expenses for anomaly detection"
        }), 200

    try:
        from ml_models.anomaly_detector import detect_anomalies
        data   = get_expense_data_for_ai(user_id)
        result = detect_anomalies(data)
        return jsonify({"status": "success", "data": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# FINANCIAL HEALTH SCORE
# GET /api/ai/health-score
# ─────────────────────────────────────────────
@ai_bp.route('/api/ai/health-score', methods=['GET'])
@jwt_required()
def get_health_score():
    user_id = int(get_jwt_identity())

    try:
        import pandas as pd
        from ml_models.financial_health_scorer import FinancialHealthScorer
        from services.budget_analysis import get_budget_utilization

        exp_data   = get_expense_data_for_ai(user_id)
        inc_data   = get_income_data_for_ai(user_id)
        goals_data = []

        from models.savings_goal import SavingsGoal
        goals = SavingsGoal.query.filter_by(user_id=user_id).all()
        goals_data = [{
            'is_complete':        g.is_complete,
            'progress_percentage': round(
                float(g.saved_amount) / float(g.target_amount) * 100, 2
            ) if float(g.target_amount) > 0 else 0
        } for g in goals]

        exp_df      = pd.DataFrame(exp_data) if exp_data else None
        inc_df      = pd.DataFrame(inc_data) if inc_data else None
        budget_data = get_budget_utilization(user_id, months=3)

        scorer = FinancialHealthScorer()
        scorer.compute(exp_df, inc_df, budget_data, goals_data)
        result = scorer.get_results()

        return jsonify({"status": "success", "data": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# CATEGORY SUGGESTION
# POST /api/ai/suggest-category
# ─────────────────────────────────────────────
@ai_bp.route('/api/ai/suggest-category', methods=['POST'])
@jwt_required()
def suggest_category():
    user_id = int(get_jwt_identity())
    data    = request.get_json()
    note    = data.get('note', '').strip() if data else ''

    if not note:
        return jsonify({"error": "Note is required"}), 400

    try:
        result = suggest_category_for_note(user_id, note)
        return jsonify({"status": "success", "data": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# SAVINGS PROJECTION
# GET /api/ai/savings-projection/<goal_id>
# ─────────────────────────────────────────────
@ai_bp.route('/api/ai/savings-projection/<int:goal_id>', methods=['GET'])
@jwt_required()
def savings_projection(goal_id):
    user_id        = int(get_jwt_identity())
    monthly_saving = request.args.get('monthly_saving', 0, type=float)

    if monthly_saving <= 0:
        return jsonify({"error": "monthly_saving must be positive"}), 400

    try:
        result = get_savings_projection_analysis(
            user_id, goal_id, monthly_saving
        )
        return jsonify({"status": "success", "data": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# AI DATA STATS
# GET /api/ai/stats
# ─────────────────────────────────────────────
@ai_bp.route('/api/ai/stats', methods=['GET'])
@jwt_required()
def ai_stats():
    user_id = int(get_jwt_identity())

    try:
        from ml_models.data_preprocessor import DataPreprocessor
        preprocessor = DataPreprocessor(user_id).load()
        check        = preprocessor.has_sufficient_data()
        stats        = preprocessor.get_stats()

        return jsonify({
            "status": "success",
            "data": {
                "sufficient":    check['sufficient'],
                "record_count":  check['record_count'],
                "month_count":   check['month_count'],
                "message":       check['message'],
                "data_stats":    stats
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500