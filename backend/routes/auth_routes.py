# backend/routes/auth_routes.py
# Authentication + Forgot Password + Password Reset

import hashlib
import re
import secrets

from datetime import timedelta

import resend

from flask import Blueprint, jsonify, request, current_app

from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
)

from extensions import db, bcrypt
from models.user import User
from models.password_reset_token import (
    PasswordResetToken,
    utc_now_naive,
)


auth_bp = Blueprint("auth", __name__)


# ============================================================
# EMAIL VALIDATION
# ============================================================

def is_valid_email(email):
    """Check whether an email address has a valid basic format."""
    pattern = r"^[\w.\-]+@[\w.\-]+\.\w+$"
    return re.match(pattern, email) is not None


# ============================================================
# REGISTER
# ============================================================

@auth_bp.route("/api/auth/register", methods=["POST"])
def register():

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "No data provided"
        }), 400

    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")

    if not name:
        return jsonify({
            "error": "Name is required"
        }), 400

    if len(name) < 2:
        return jsonify({
            "error": "Name must be at least 2 characters"
        }), 400

    if not email:
        return jsonify({
            "error": "Email is required"
        }), 400

    if not is_valid_email(email):
        return jsonify({
            "error": "Invalid email format"
        }), 400

    if not password:
        return jsonify({
            "error": "Password is required"
        }), 400

    if len(password) < 6:
        return jsonify({
            "error": "Password must be at least 6 characters"
        }), 400

    existing_user = User.query.filter_by(email=email).first()

    if existing_user:
        return jsonify({
            "error": "Email is already registered"
        }), 409

    password_hash = (
        bcrypt
        .generate_password_hash(password)
        .decode("utf-8")
    )

    new_user = User(
        name=name,
        email=email,
        password_hash=password_hash,
        role="user",
        is_active=True,
    )

    try:
        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": (
                "Registration successful. "
                "Please login."
            ),
            "data": {
                "user_id": new_user.id,
                "name": new_user.name,
            },
        }), 201

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": (
                "Registration failed. "
                "Please try again."
            )
        }), 500


# ============================================================
# LOGIN
# ============================================================

@auth_bp.route("/api/auth/login", methods=["POST"])
def login():

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "No data provided"
        }), 400

    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")

    if not email and not password:
        return jsonify({
            "error": "Email and password are required"
        }), 400

    if not email:
        return jsonify({
            "error": "Email is required"
        }), 400

    if not password:
        return jsonify({
            "error": "Password is required"
        }), 400

    if not is_valid_email(email):
        return jsonify({
            "error": "Invalid email format"
        }), 401

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({
            "error": "Invalid email"
        }), 401

    if not user.is_active:
        return jsonify({
            "error": (
                "Your account has been deactivated. "
                "Contact admin."
            )
        }), 403

    password_correct = bcrypt.check_password_hash(
        user.password_hash,
        password,
    )

    if not password_correct:
        return jsonify({
            "error": "Wrong password"
        }), 401

    additional_claims = {
        "role": user.role,
        "name": user.name,
    }

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims=additional_claims,
    )

    return jsonify({
        "status": "success",
        "message": "Login successful",
        "data": {
            "access_token": access_token,
            "user": user.to_dict(),
        },
    }), 200


# ============================================================
# FORGOT PASSWORD
# POST /api/auth/forgot-password
# ============================================================

@auth_bp.route("/api/auth/forgot-password", methods=["POST"])
def forgot_password():

    data = request.get_json(silent=True) or {}

    email = str(
        data.get("email", "")
    ).strip().lower()

    # Same response whether account exists or not.
    generic_response = {
        "status": "success",
        "message": (
            "If an account exists for this email, "
            "a password reset link has been sent."
        ),
    }

    if not email or not is_valid_email(email):
        return jsonify(generic_response), 200

    user = User.query.filter_by(email=email).first()

    if not user or not user.is_active:
        return jsonify(generic_response), 200

    now = utc_now_naive()

    # --------------------------------------------------------
    # Delete expired/used reset tokens
    # --------------------------------------------------------

    try:
        old_tokens = (
            PasswordResetToken.query
            .filter_by(user_id=user.id)
            .all()
        )

        for old_token in old_tokens:
            if (
                old_token.used_at is not None
                or old_token.expires_at <= now
            ):
                db.session.delete(old_token)

        db.session.commit()

    except Exception:
        db.session.rollback()
        return jsonify(generic_response), 200

    # --------------------------------------------------------
    # Cooldown
    # --------------------------------------------------------

    latest_token = (
        PasswordResetToken.query
        .filter_by(user_id=user.id)
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )

    if latest_token:
        elapsed = (
            now - latest_token.created_at
        ).total_seconds()

        if elapsed < current_app.config[
            "RESET_REQUEST_COOLDOWN_SECONDS"
        ]:
            return jsonify(generic_response), 200

    # --------------------------------------------------------
    # Secure one-time token
    # --------------------------------------------------------

    raw_token = secrets.token_urlsafe(48)

    token_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    expires_at = now + timedelta(
        minutes=current_app.config[
            "RESET_TOKEN_TTL_MINUTES"
        ]
    )

    reset_record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )

    try:
        db.session.add(reset_record)
        db.session.commit()

    except Exception:
        db.session.rollback()
        return jsonify(generic_response), 200

    # --------------------------------------------------------
    # Laptop-only reset URL
    # --------------------------------------------------------

    frontend_base = current_app.config.get(
        "FRONTEND_BASE_URL",
        "http://localhost:3000",
    ).rstrip("/")

    reset_url = (
        f"{frontend_base}"
        f"/pages/reset_password.html"
        f"?token={raw_token}"
    )

    # --------------------------------------------------------
    # Send email
    # --------------------------------------------------------

    try:
        send_password_reset_email(
            user.email,
            reset_url,
        )

    except Exception as email_error:
        print(
            "[Auth] Password reset email failed:",
            email_error,
        )

        # Local-development fallback.
        print(
            "[Auth] DEV RESET URL:",
            reset_url,
        )

    return jsonify(generic_response), 200


# ============================================================
# SEND PASSWORD RESET EMAIL — RESEND API
# ============================================================

def send_password_reset_email(recipient, reset_url):

    resend_api_key = current_app.config.get(
        "RESEND_API_KEY",
        ""
    )

    mail_from = current_app.config.get(
        "RESEND_FROM_EMAIL",
        "onboarding@resend.dev"
    )

    if not resend_api_key:
        raise RuntimeError(
            "RESEND_API_KEY is not configured"
        )

    if not mail_from:
        raise RuntimeError(
            "RESEND_FROM_EMAIL is not configured"
        )

    resend.api_key = resend_api_key

    ttl_minutes = current_app.config[
        "RESET_TOKEN_TTL_MINUTES"
    ]

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport"
              content="width=device-width, initial-scale=1.0">
        <title>FinanceAI Password Reset</title>
    </head>

    <body style="
        margin:0;
        padding:0;
        background:#f4f7fb;
        font-family:Arial,Helvetica,sans-serif;
    ">

        <div style="
            max-width:600px;
            margin:40px auto;
            background:#ffffff;
            border-radius:12px;
            padding:32px;
            box-shadow:0 4px 18px rgba(0,0,0,0.08);
        ">

            <h2 style="
                margin-top:0;
                color:#2563eb;
            ">
                FinanceAI Password Reset
            </h2>

            <p style="color:#334155;font-size:16px;">
                You requested a password reset for your
                FinanceAI account.
            </p>

            <p style="color:#334155;font-size:16px;">
                Click the button below to create a new password:
            </p>

            <div style="text-align:center;margin:30px 0;">
                <a href="{reset_url}" style="
                    display:inline-block;
                    padding:12px 24px;
                    background:#2563eb;
                    color:#ffffff;
                    text-decoration:none;
                    border-radius:8px;
                    font-weight:600;
                ">
                    Reset Password
                </a>
            </div>

            <p style="
                color:#64748b;
                font-size:14px;
                line-height:1.6;
            ">
                This link expires in
                <strong>{ttl_minutes} minutes</strong>
                and can only be used once.
            </p>

            <p style="
                color:#64748b;
                font-size:14px;
                line-height:1.6;
            ">
                If you did not request this password reset,
                you can safely ignore this email.
            </p>

            <hr style="
                border:none;
                border-top:1px solid #e2e8f0;
                margin:25px 0;
            ">

            <p style="
                color:#94a3b8;
                font-size:12px;
                word-break:break-all;
            ">
                If the button does not work, copy and open this link:
                <br><br>
                {reset_url}
            </p>

        </div>

    </body>
    </html>
    """

    params = {
        "from": mail_from,
        "to": [recipient],
        "subject": "FinanceAI Password Reset",
        "html": html_content,
    }

    result = resend.Emails.send(params)

    if not result:
        raise RuntimeError(
            "Resend did not return a response"
        )

    return result


# ============================================================
# RESET PASSWORD
# POST /api/auth/reset-password
# ============================================================

@auth_bp.route("/api/auth/reset-password", methods=["POST"])
def reset_password():

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "Invalid request"
        }), 400

    token = str(
        data.get("token", "")
    ).strip()

    new_password = data.get(
        "new_password",
        "",
    )

    confirm_password = data.get(
        "confirm_password",
        "",
    )

    if not token:
        return jsonify({
            "error": "Invalid or expired reset link."
        }), 400

    if not new_password:
        return jsonify({
            "error": "New password is required"
        }), 400

    if not confirm_password:
        return jsonify({
            "error": "Please confirm your new password"
        }), 400

    if len(new_password) < 6:
        return jsonify({
            "error": "Password must be at least 6 characters"
        }), 400

    if new_password != confirm_password:
        return jsonify({
            "error": "Passwords do not match"
        }), 400

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    reset_record = (
        PasswordResetToken.query
        .filter_by(token_hash=token_hash)
        .first()
    )

    if not reset_record:
        return jsonify({
            "error": "Invalid or expired reset link."
        }), 400

    if not reset_record.is_valid():
        return jsonify({
            "error": "Invalid or expired reset link."
        }), 400

    user = db.session.get(
        User,
        reset_record.user_id,
    )

    if not user:
        return jsonify({
            "error": "Invalid reset request"
        }), 400

    if not user.is_active:
        return jsonify({
            "error": "Your account has been deactivated."
        }), 403

    # --------------------------------------------------------
    # Update password
    # --------------------------------------------------------

    user.password_hash = (
        bcrypt
        .generate_password_hash(new_password)
        .decode("utf-8")
    )

    # Current token becomes single-use.
    reset_record.used_at = utc_now_naive()

    # Invalidate every other active token for this user.
    other_tokens = (
        PasswordResetToken.query
        .filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.id != reset_record.id,
            PasswordResetToken.used_at.is_(None),
        )
        .all()
    )

    used_time = utc_now_naive()

    for other_token in other_tokens:
        other_token.used_at = used_time

    try:
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": (
                "Password reset successful. "
                "Please login with your new password."
            ),
        }), 200

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": (
                "Password reset failed. "
                "Please try again."
            )
        }), 500


# ============================================================
# LOGOUT
# ============================================================

@auth_bp.route("/api/auth/logout", methods=["POST"])
@jwt_required()
def logout():

    return jsonify({
        "status": "success",
        "message": "Logged out successfully",
    }), 200


# ============================================================
# CURRENT USER
# ============================================================

@auth_bp.route("/api/auth/me", methods=["GET"])
@jwt_required()
def get_me():

    user_id = int(
        get_jwt_identity()
    )

    user = db.session.get(
        User,
        user_id,
    )

    if not user:
        return jsonify({
            "error": "User not found"
        }), 404

    return jsonify({
        "status": "success",
        "data": user.to_dict(),
    }), 200
