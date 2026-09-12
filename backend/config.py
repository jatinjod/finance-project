# backend/config.py

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL


# ============================================================
# LOAD .env FROM backend/.env
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(
    dotenv_path=ENV_FILE,
    override=True
)


class Config:

    # ========================================================
    # FLASK
    # ========================================================

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "financeai-secret-key-change-in-production"
    )

    DEBUG = (
        os.getenv("DEBUG", "False").lower() == "true"
    )

    # ========================================================
    # DATABASE
    # ========================================================

    DB_USER = os.getenv(
        "DB_USER",
        "root"
    )

    DB_PASSWORD = os.getenv(
        "DB_PASSWORD",
        ""
    )

    DB_HOST = os.getenv(
        "DB_HOST",
        "localhost"
    )

    DB_PORT = int(
        os.getenv(
            "DB_PORT",
            "3306"
        )
    )

    DB_NAME = os.getenv(
        "DB_NAME",
        "finance_db"
    )

    # Production DATABASE_URL support
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        ""
    )

    if DATABASE_URL:
        if DATABASE_URL.startswith("mysql://"):
            DATABASE_URL = DATABASE_URL.replace(
                "mysql://",
                "mysql+pymysql://",
                1
            )

        SQLALCHEMY_DATABASE_URI = DATABASE_URL

    else:
        SQLALCHEMY_DATABASE_URI = URL.create(
            "mysql+pymysql",
            username=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ECHO = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 280,
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
        "connect_args": {
            "connect_timeout": 10
        }
    }

    # ========================================================
    # JWT
    # ========================================================

    JWT_SECRET_KEY = os.getenv(
        "JWT_SECRET_KEY",
        SECRET_KEY
    )

    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=24
    )

    # ========================================================
    # JSON
    # ========================================================

    JSON_SORT_KEYS = False

    # ========================================================
    # PASSWORD RESET
    # ========================================================

    RESET_TOKEN_TTL_MINUTES = int(
        os.getenv(
            "RESET_TOKEN_TTL_MINUTES",
            "30"
        )
    )

    RESET_REQUEST_COOLDOWN_SECONDS = int(
        os.getenv(
            "RESET_REQUEST_COOLDOWN_SECONDS",
            "60"
        )
    )

    FRONTEND_BASE_URL = os.getenv(
        "FRONTEND_BASE_URL",
        "http://localhost:3000"
    )

    # ========================================================
    # RESEND EMAIL API
    # ========================================================

    RESEND_API_KEY = os.getenv(
        "RESEND_API_KEY",
        ""
    )

    RESEND_FROM_EMAIL = os.getenv(
        "RESEND_FROM_EMAIL",
        "onboarding@resend.dev"
    )
    
    # ========================================================
    # SMTP
    # ========================================================

    SMTP_HOST = os.getenv(
        "SMTP_HOST",
        ""
    )

    SMTP_PORT = int(
        os.getenv(
            "SMTP_PORT",
            "587"
        )
    )

    SMTP_USERNAME = os.getenv(
        "SMTP_USERNAME",
        ""
    )

    SMTP_PASSWORD = os.getenv(
        "SMTP_PASSWORD",
        ""
    )

    SMTP_USE_TLS = (
        os.getenv(
            "SMTP_USE_TLS",
            "True"
        ).lower() == "true"
    )

    MAIL_FROM = os.getenv(
        "MAIL_FROM",
        SMTP_USERNAME
    )

    # ========================================================
    # OPENAI AI CHAT
    # ========================================================

    OPENAI_API_KEY = os.getenv(
        "OPENAI_API_KEY",
        ""
    )

    OPENAI_MODEL = os.getenv(
        "OPENAI_MODEL",
        "gpt-5.6-luna"
    )


# ============================================================
# DEVELOPMENT CONFIG
# ============================================================

class DevelopmentConfig(Config):

    DEBUG = True


# ============================================================
# PRODUCTION CONFIG
# ============================================================

class ProductionConfig(Config):

    DEBUG = False


# ============================================================
# TESTING CONFIG
# ============================================================

class TestingConfig(Config):

    TESTING = True

    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

    JWT_SECRET_KEY = "test-jwt-secret"


# ============================================================
# CONFIG SELECTOR
# ============================================================

config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig
}


def get_config():

    env = os.getenv(
        "FLASK_ENV",
        "development"
    )

    return config_map.get(
        env,
        DevelopmentConfig
    )