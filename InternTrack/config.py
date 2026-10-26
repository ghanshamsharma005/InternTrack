import os
from datetime import timedelta

class Config:
    # Secret key for session security (defaults to a development key)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-interntrack-2026'
    
    # Base directory of the application
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # SQLite database configuration (normalized with forward slashes for cross-platform compatibility)
    _db_path = os.path.join(BASE_DIR, "database", "interntrack_v2.db").replace(os.sep, '/')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{_db_path}'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload configurations
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB maximum upload size

    # Session & Cookie Security Hardening
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key-2026'
