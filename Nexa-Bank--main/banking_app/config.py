import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DOCUMENT_ENCRYPTION_KEY = os.environ.get('DOCUMENT_ENCRYPTION_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{os.path.join(BASE_DIR, "database", "banking.db")}'
    DOCUMENT_STORAGE_PATH = os.environ.get('DOCUMENT_STORAGE_PATH') or \
        os.path.join(BASE_DIR, 'instance', 'private-documents')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Application settings
    MAX_WITHDRAWAL_LIMIT = 100000  # ₹1,00,000 per transaction (demo limit)
    MIN_BALANCE = 0                 # Minimum balance allowed (demo: 0)
    APP_NAME = "NexaBank"
    APP_VERSION = "1.0.0"
    DEMO_MODE = True                # Clearly marks this as a demo app


class DevelopmentConfig(Config):
    SECRET_KEY = Config.SECRET_KEY or 'dev-secret-key-change-this'
    DOCUMENT_ENCRYPTION_KEY = Config.DOCUMENT_ENCRYPTION_KEY or SECRET_KEY
    DEBUG = True
    HOST = '127.0.0.1'
    PORT = 5000


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True

    @staticmethod
    def init_app(app):
        if not app.config.get('SECRET_KEY'):
            raise RuntimeError(
                'SECRET_KEY must be set when using the production configuration.'
            )
        if not app.config.get('DOCUMENT_ENCRYPTION_KEY'):
            raise RuntimeError(
                'DOCUMENT_ENCRYPTION_KEY must be set when using the production configuration.'
            )


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
