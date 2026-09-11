# backend/services/ai_service.py
# Orchestrates all AI/ML models into a unified analysis pipeline

from extensions import db
from models.expense import Expense
from models.income import Income
from models.savings_goal import SavingsGoal
from models.ai_prediction import AIPrediction


# ─────────────────────────────────────────────
# DATA HELPERS
# ─────────────────────────────────────────────

def has_sufficient_data(user_id, minimum=10):
    """Quick check if user has enough expense records."""
    count = Expense.query.filter_by(user_id=user_id).count()
    return count >= minimum


def get_expense_data_for_ai(user_id):
    """Fetch expense data as list of dicts for ML models."""
    expenses = Expense.query.filter_by(
        user_id=user_id
    ).order_by(Expense.date.asc()).all()

    return [{
        'id':            e.id,
        'amount':        float(e.amount),
        'date':          e.date.isoformat() if e.date else None,
        'category_id':   e.category_id,
        'category_name': e.category.name if e.category else 'Unknown',
        'note':          e.note or ''
    } for e in expenses]


def get_income_data_for_ai(user_id):
    """Fetch income data as list of dicts for ML models."""
    incomes = Income.query.filter_by(
        user_id=user_id
    ).order_by(Income.date.asc()).all()

    return [{
        'id':            i.id,
        'amount':        float(i.amount),
        'date':          i.date.isoformat() if i.date else None,
        'category_id':   i.category_id,
        'category_name': i.category.name if i.category else 'Unknown',
        'note':          i.note or ''
    } for i in incomes]


def get_savings_data_for_ai(user_id):
    """Fetch savings goals as list of dicts."""
    goals = SavingsGoal.query.filter_by(user_id=user_id).all()
    return [{
        'id':                 g.id,
        'name':               g.name,
        'target_amount':      float(g.target_amount),
        'saved_amount':       float(g.saved_amount),
        'deadline':           g.deadline.isoformat() if g.deadline else None,
        'is_complete':        g.is_complete,
        'progress_percentage': round(
            float(g.saved_amount) / float(g.target_amount) * 100, 2
        ) if float(g.target_amount) > 0 else 0
    } for g in goals]


# ─────────────────────────────────────────────
# MAIN AI ANALYSIS ORCHESTRATOR
# ─────────────────────────────────────────────

def run_full_ai_analysis(user_id):
    """
    Run all AI/ML models and return combined results.
    """
    expense_count = Expense.query.filter_by(user_id=user_id).count()

    if expense_count < 10:
        return {
            'status':           'insufficient_data',
            'message':          f'Add at least {max(0, 10 - expense_count)} more '
                                f'expense records to unlock AI insights.',
            'current_count':    expense_count,
            'minimum_required': 10
        }

    expense_data = get_expense_data_for_ai(user_id)
    income_data  = get_income_data_for_ai(user_id)
    goals_data   = get_savings_data_for_ai(user_id)

    results = {'status': 'success'}

    # ── Expense Prediction ─────────────────────
    try:
        from ml_models.expense_predictor import predict_next_month_expense
        results['prediction'] = predict_next_month_expense(expense_data)
        _save_prediction(user_id, 'expense_pred', results['prediction'])
    except Exception as e:
        results['prediction'] = {'status': 'error', 'message': str(e)}

    # ── Budget Recommendations ─────────────────
    try:
        from ml_models.budget_recommender import recommend_budget
        results['recommendations'] = recommend_budget(expense_data)
        _save_prediction(user_id, 'budget_rec', results['recommendations'])
    except Exception as e:
        results['recommendations'] = {'status': 'error', 'message': str(e)}

    # ── Pattern Detection ──────────────────────
    try:
        from ml_models.pattern_detector import detect_spending_patterns
        results['patterns'] = detect_spending_patterns(expense_data, income_data)
        _save_prediction(user_id, 'pattern', results['patterns'])
    except Exception as e:
        results['patterns'] = {'status': 'error', 'message': str(e)}

    # ── Anomaly Detection ──────────────────────
    try:
        from ml_models.anomaly_detector import detect_anomalies
        results['anomalies'] = detect_anomalies(expense_data)
        if results['anomalies'].get('anomalies_found', 0) > 0:
            _notify_anomalies(user_id, results['anomalies']['anomalies'])
        _save_prediction(user_id, 'anomaly', results['anomalies'])
    except Exception as e:
        results['anomalies'] = {'status': 'error', 'message': str(e)}

    # ── Financial Health Score ─────────────────
    try:
        from ml_models.financial_health_scorer import FinancialHealthScorer
        from services.budget_analysis import get_budget_utilization
        import pandas as pd

        exp_df = pd.DataFrame(expense_data)
        inc_df = pd.DataFrame(income_data) if income_data else None
        budget_data = get_budget_utilization(user_id, months=3)

        scorer = FinancialHealthScorer()
        scorer.compute(exp_df, inc_df, budget_data, goals_data)
        results['health_score'] = scorer.get_results()
        _save_prediction(user_id, 'tip', results['health_score'])
    except Exception as e:
        results['health_score'] = {'status': 'error', 'message': str(e)}

    # ── Consolidated Tips ──────────────────────
    all_tips = []
    if results.get('patterns', {}).get('tips'):
        all_tips.extend(results['patterns']['tips'])
    if results.get('patterns', {}).get('warnings'):
        all_tips.extend(results['patterns']['warnings'])
    results['tips'] = list(dict.fromkeys(all_tips))  # deduplicate

    return results


def suggest_category_for_note(user_id, note):
    """
    Suggest a category for a given expense note.
    """
    from ml_models.category_suggester import suggest_category
    from models.category import Category

    # Get available categories for this user
    categories = Category.query.filter(
        (Category.user_id.is_(None)) |
        (Category.user_id == user_id),
        Category.type == 'expense'
    ).all()

    available = [{'name': c.name, 'id': c.id} for c in categories]
    expense_data = get_expense_data_for_ai(user_id)

    return suggest_category(note, available, expense_data)


def get_savings_projection_analysis(user_id, goal_id, monthly_saving):
    """Get savings projection for a specific goal."""
    from ml_models.financial_health_scorer import FinancialHealthScorer
    from services.savings_analysis import get_savings_projection
    return get_savings_projection(user_id, goal_id, monthly_saving)


# ─────────────────────────────────────────────
# PRIVATE HELPERS
# ─────────────────────────────────────────────

def _save_prediction(user_id, prediction_type, data):
    """Persist prediction result to database."""
    try:
        pred = AIPrediction(
            user_id=user_id,
            prediction_type=prediction_type,
            prediction_data=data
        )
        db.session.add(pred)
        db.session.commit()
    except Exception:
        db.session.rollback()


def _notify_anomalies(user_id, anomalies):
    """Create notifications for top anomalous transactions."""
    from models.notification import Notification
    try:
        for anomaly in anomalies[:2]:
            msg = (
                f"Unusual transaction: ₹{anomaly['amount']:,.0f} "
                f"in {anomaly['category_name']} on {anomaly['date']}"
            )
            existing = Notification.query.filter_by(
                user_id=user_id, type='anomaly', is_read=False
            ).filter(
                Notification.message.like(f"%{anomaly['category_name']}%")
            ).first()

            if not existing:
                db.session.add(Notification(
                    user_id=user_id,
                    message=msg,
                    type='anomaly'
                ))
        db.session.commit()
    except Exception:
        db.session.rollback()