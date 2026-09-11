# backend/routes/savings_routes.py
# Handles savings goal CRUD operations

from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models.savings_goal import SavingsGoal
from models.notification import Notification

savings_bp = Blueprint('savings', __name__)


# ─────────────────────────────────────────────
# GET ALL GOALS — GET /api/savings
# ─────────────────────────────────────────────
@savings_bp.route('/api/savings', methods=['GET'])
@jwt_required()
def get_savings_goals():
    user_id = int(get_jwt_identity())
    goals   = SavingsGoal.query.filter_by(user_id=user_id).order_by(
        SavingsGoal.is_complete.asc(),
        SavingsGoal.deadline.asc()
    ).all()

    return jsonify({
        "status": "success",
        "data":   [g.to_dict() for g in goals]
    }), 200


# ─────────────────────────────────────────────
# CREATE GOAL — POST /api/savings
# ─────────────────────────────────────────────
@savings_bp.route('/api/savings', methods=['POST'])
@jwt_required()
def create_savings_goal():
    user_id = int(get_jwt_identity())
    data    = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    name          = data.get('name', '').strip()
    target_amount = data.get('target_amount')
    saved_amount  = data.get('saved_amount', 0)
    deadline_str  = data.get('deadline')

    if not name:
        return jsonify({"error": "Goal name is required"}), 400

    try:
        target_amount = float(target_amount)
        if target_amount <= 0:
            return jsonify({"error": "Target amount must be greater than zero"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid target amount"}), 400

    try:
        saved_amount = float(saved_amount)
        if saved_amount < 0:
            return jsonify({"error": "Saved amount cannot be negative"}), 400
    except (TypeError, ValueError):
        saved_amount = 0

    deadline = None
    if deadline_str:
        try:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Invalid deadline format. Use YYYY-MM-DD"}), 400

    new_goal = SavingsGoal(
        user_id=user_id,
        name=name,
        target_amount=target_amount,
        saved_amount=saved_amount,
        deadline=deadline
    )

    try:
        db.session.add(new_goal)
        db.session.commit()
        return jsonify({
            "status":  "success",
            "message": "Savings goal created",
            "data":    new_goal.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create savings goal"}), 500


# ─────────────────────────────────────────────
# UPDATE GOAL — PUT /api/savings/<id>
# ─────────────────────────────────────────────
@savings_bp.route('/api/savings/<int:goal_id>', methods=['PUT'])
@jwt_required()
def update_savings_goal(goal_id):
    user_id = int(get_jwt_identity())
    goal    = SavingsGoal.query.filter_by(id=goal_id, user_id=user_id).first()

    if not goal:
        return jsonify({"error": "Savings goal not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    if 'name' in data:
        name = data['name'].strip()
        if not name:
            return jsonify({"error": "Name cannot be empty"}), 400
        goal.name = name

    if 'target_amount' in data:
        try:
            target = float(data['target_amount'])
            if target <= 0:
                return jsonify({"error": "Target must be greater than zero"}), 400
            goal.target_amount = target
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid target amount"}), 400

    if 'saved_amount' in data:
        try:
            saved = float(data['saved_amount'])
            if saved < 0:
                return jsonify({"error": "Saved amount cannot be negative"}), 400
            goal.saved_amount = saved
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid saved amount"}), 400

    if 'deadline' in data:
        if data['deadline']:
            try:
                goal.deadline = datetime.strptime(data['deadline'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({"error": "Invalid deadline format. Use YYYY-MM-DD"}), 400
        else:
            goal.deadline = None

    if 'is_complete' in data:
        goal.is_complete = bool(data['is_complete'])

    # Auto-complete and notify if saved amount reached target
    if float(goal.saved_amount) >= float(goal.target_amount) and not goal.is_complete:
        goal.is_complete = True
        notification = Notification(
            user_id=user_id,
            message=f"🎉 Congratulations! You achieved your '{goal.name}' savings goal!",
            type='goal_achieved'
        )
        db.session.add(notification)

    try:
        db.session.commit()
        return jsonify({
            "status":  "success",
            "message": "Savings goal updated",
            "data":    goal.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Update failed"}), 500


# ─────────────────────────────────────────────
# DELETE GOAL — DELETE /api/savings/<id>
# ─────────────────────────────────────────────
@savings_bp.route('/api/savings/<int:goal_id>', methods=['DELETE'])
@jwt_required()
def delete_savings_goal(goal_id):
    user_id = int(get_jwt_identity())
    goal    = SavingsGoal.query.filter_by(id=goal_id, user_id=user_id).first()

    if not goal:
        return jsonify({"error": "Savings goal not found"}), 404

    try:
        db.session.delete(goal)
        db.session.commit()
        return jsonify({
            "status":  "success",
            "message": "Savings goal deleted"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Delete failed"}), 500