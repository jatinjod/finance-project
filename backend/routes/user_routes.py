# backend/routes/user_routes.py
# Handles user profile management

import re

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db, bcrypt
from models.user import User

user_bp = Blueprint("user", __name__)


def is_valid_email(email):
    pattern = r"^[\w.-]+@[\w.-]+\.\w+$"
    return re.match(pattern, email) is not None


# -------------------------------------------------
# GET PROFILE — GET /api/user/profile
# -------------------------------------------------
@user_bp.route("/api/user/profile", methods=["GET"])
@jwt_required()
def get_profile():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "status": "success",
        "data": user.to_dict()
    }), 200


# -------------------------------------------------
# UPDATE PROFILE — PUT /api/user/profile
# -------------------------------------------------
@user_bp.route("/api/user/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "name" in data:
        name = str(data["name"]).strip()

        if not name or len(name) < 2:
            return jsonify({
                "error": "Name must be at least 2 characters"
            }), 400

        user.name = name

    if "email" in data:
        new_email = str(data["email"]).strip().lower()

        if not is_valid_email(new_email):
            return jsonify({
                "error": "Invalid email format"
            }), 400

        existing = User.query.filter_by(email=new_email).first()

        if existing and existing.id != user_id:
            return jsonify({
                "error": "Email is already in use"
            }), 409

        user.email = new_email

    try:
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Profile updated successfully",
            "data": user.to_dict()
        }), 200

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Update failed. Please try again."
        }), 500


# -------------------------------------------------
# CHANGE PASSWORD — PUT /api/user/password
# -------------------------------------------------
@user_bp.route("/api/user/password", methods=["PUT"])
@jwt_required()
def change_password():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "No data provided"}), 400

    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")

    if not current_password or not new_password:
        return jsonify({
            "error": "Current and new password are required"
        }), 400

    if not bcrypt.check_password_hash(
        user.password_hash,
        current_password
    ):
        return jsonify({
            "error": "Current password is incorrect"
        }), 401

    if len(new_password) < 6:
        return jsonify({
            "error": "New password must be at least 6 characters"
        }), 400

    user.password_hash = bcrypt.generate_password_hash(
        new_password
    ).decode("utf-8")

    try:
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Password changed successfully. Please login again."
        }), 200

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Password change failed."
        }), 500