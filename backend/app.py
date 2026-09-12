# backend/app.py

import os
from flask import Flask, jsonify, send_from_directory
from sqlalchemy import text

from config import Config
from extensions import db, bcrypt, jwt


# ============================================================
# MODELS
# ============================================================

from models.user import User
from models.category import Category
from models.income import Income
from models.expense import Expense
from models.budget import Budget
from models.savings_goal import SavingsGoal
from models.notification import Notification

from models.password_reset_token import (
    PasswordResetToken
)


try:
    from models.ai_prediction import AIPrediction
except ImportError:
    AIPrediction = None


# ============================================================
# CREATE APP
# ============================================================

def create_app(test_config=None):

    app = Flask(__name__)


    if test_config:

        app.config.from_mapping(
            test_config
        )

    else:

        app.config.from_object(
            Config
        )

    FRONTEND_DIR = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "frontend"
        )
    )

    @app.route("/pages/<path:filename>")
    def serve_frontend_page(filename):
        return send_from_directory(
            os.path.join(FRONTEND_DIR, "pages"),
            filename
        )

    @app.route("/js/<path:filename>")
    def serve_frontend_js(filename):
        return send_from_directory(
            os.path.join(FRONTEND_DIR, "js"),
            filename
        )

    @app.route("/css/<path:filename>")
    def serve_frontend_css(filename):
        return send_from_directory(
            os.path.join(FRONTEND_DIR, "css"),
            filename
        )
    # --------------------------------------------------------
    # Flask
    # --------------------------------------------------------

    app.url_map.strict_slashes = False


    # --------------------------------------------------------
    # Extensions
    # --------------------------------------------------------

    db.init_app(app)

    bcrypt.init_app(app)

    jwt.init_app(app)


    # --------------------------------------------------------
    # CORS
    # --------------------------------------------------------

    from flask_cors import CORS

    CORS(
    app,
    resources={
        r"/api/*": {
            "origins": os.getenv(
                "CORS_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000"
            ).split(","),
            "methods": [
                "GET",
                "POST",
                "PUT",
                "DELETE",
                "OPTIONS"
            ],
            "allow_headers": [
                "Content-Type",
                "Authorization"
            ]
        }
    },
    supports_credentials=False
)


    # --------------------------------------------------------
    # Blueprints
    # --------------------------------------------------------

    from routes.auth_routes import auth_bp
    from routes.user_routes import user_bp
    from routes.category_routes import category_bp
    from routes.income_routes import income_bp
    from routes.expense_routes import expense_bp
    from routes.budget_routes import budget_bp
    from routes.savings_routes import savings_bp
    from routes.transaction_routes import transaction_bp
    from routes.dashboard_routes import dashboard_bp
    from routes.report_routes import report_bp
    from routes.notification_routes import notification_bp
    from routes.ai_routes import ai_bp
    from routes.admin_routes import admin_bp
    from routes.analytics_routes import analytics_bp
    from routes.ai_chat_routes import ai_chat_bp
    from routes.investment_routes import investment_bp


    app.register_blueprint(
        auth_bp
    )

    app.register_blueprint(
        user_bp
    )

    app.register_blueprint(
        category_bp
    )

    app.register_blueprint(
        income_bp
    )

    app.register_blueprint(
        expense_bp
    )

    app.register_blueprint(
        budget_bp
    )

    app.register_blueprint(
        savings_bp
    )

    app.register_blueprint(
        transaction_bp
    )

    app.register_blueprint(
        dashboard_bp
    )

    app.register_blueprint(
        report_bp
    )

    app.register_blueprint(
        notification_bp
    )

    app.register_blueprint(
        ai_bp
    )

    app.register_blueprint(
        admin_bp
    )

    app.register_blueprint(
        analytics_bp
    )

    app.register_blueprint(
        ai_chat_bp
    )

    app.register_blueprint(
        investment_bp
    )


    # --------------------------------------------------------
    # JWT error handlers
    # --------------------------------------------------------

    @jwt.expired_token_loader
    def expired_token(
        jwt_header,
        jwt_payload
    ):

        return jsonify({
            "error": "Token has expired"
        }), 401


    @jwt.invalid_token_loader
    def invalid_token(error):

        return jsonify({
            "error": "Invalid token"
        }), 401


    @jwt.unauthorized_loader
    def missing_token(error):

        return jsonify({
            "error": (
                "Authorization token is required"
            )
        }), 401


    # --------------------------------------------------------
    # ROOT
    # --------------------------------------------------------

    @app.route("/")
    def index():

        return jsonify({
            "status": "ok",
            "message": (
                "FinanceAI backend is running"
            )
        }), 200


    # --------------------------------------------------------
    # HEALTH
    # --------------------------------------------------------

    @app.route(
        "/api/health",
        methods=["GET"]
    )
    def health():

        try:

            db.session.execute(
                text("SELECT 1")
            )


            return jsonify({
                "status": "ok",
                "database": "connected",
                "cors": "enabled"
            }), 200


        except Exception:

            db.session.rollback()

            return jsonify({
                "status": "error",
                "database": "disconnected",
                "cors": "enabled"
            }), 500


    # --------------------------------------------------------
    # 404
    # --------------------------------------------------------

    @app.errorhandler(404)
    def not_found(error):

        return jsonify({
            "error": "Resource not found"
        }), 404


    # --------------------------------------------------------
    # 405
    # --------------------------------------------------------

    @app.errorhandler(405)
    def method_not_allowed(error):

        return jsonify({
            "error": "Method not allowed"
        }), 405


    # --------------------------------------------------------
    # 500
    # --------------------------------------------------------

    @app.errorhandler(500)
    def internal_server_error(error):

        db.session.rollback()

        return jsonify({
            "error": "Internal server error"
        }), 500


    return app


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db(app):

    with app.app_context():

        db.create_all()


        # ----------------------------------------------------
        # Default categories
        # ----------------------------------------------------

        default_categories = [

            ("Salary", "income"),
            ("Freelance", "income"),
            ("Business", "income"),
            ("Investment", "income"),
            ("Gift", "income"),
            ("Other", "income"),

            ("Food", "expense"),
            ("Transport", "expense"),
            ("Rent", "expense"),
            ("Utilities", "expense"),
            ("Entertainment", "expense"),
            ("Shopping", "expense"),
            ("Healthcare", "expense"),
            ("Education", "expense"),
            ("Travel", "expense"),
            ("Other", "expense")
        ]


        for name, category_type in default_categories:

            existing = Category.query.filter_by(
                name=name,
                type=category_type,
                user_id=None
            ).first()


            if not existing:

                db.session.add(
                    Category(
                        name=name,
                        type=category_type,
                        user_id=None,
                        is_default=True
                    )
                )


        # ----------------------------------------------------
        # Default admin
        # ----------------------------------------------------

        admin_email = (
            "admin@finance.com"
        )


        admin = User.query.filter_by(
            email=admin_email
        ).first()


        if not admin:

            admin = User(
                name="Administrator",
                email=admin_email,
                password_hash=(
                    bcrypt
                    .generate_password_hash(
                        "admin123"
                    )
                    .decode("utf-8")
                ),
                role="admin",
                is_active=True
            )


            db.session.add(
                admin
            )


        else:

            admin.role = "admin"

            admin.is_active = True


        db.session.commit()


# ============================================================
# ENTRY POINT
# ============================================================

app = create_app()


if __name__ == "__main__":

    init_db(app)

    print("=" * 50)
    print(" FinanceAI Backend")
    print("=" * 50)
    print(
        " Backend: http://localhost:5000"
    )
    print(
        " Health : http://localhost:5000/api/health"
    )
    print("=" * 50)

    port = int(os.getenv("PORT", "5000"))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )