import os

from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db = SQLAlchemy()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me-in-production-0000")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() in {
        "1",
        "true",
        "yes",
    }
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "rental.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

    # First admin account, created by `seed.py`
    ADMIN_NAME = os.getenv("ADMIN_NAME", "Admin")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@rental.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@1234")
    RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
    RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "")


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    RESEND_API_KEY = ""
    RESEND_FROM_EMAIL = ""
