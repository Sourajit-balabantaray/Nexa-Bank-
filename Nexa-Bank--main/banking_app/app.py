"""
NexaBank - Banking Management Application
Main application factory.
"""

import os
from io import BytesIO

from flask import Flask, Request, render_template
from werkzeug.exceptions import RequestEntityTooLarge

from config import config
from extensions import csrf, db, login_manager


class PrivateUploadRequest(Request):
    def _get_file_stream(self, total_content_length, content_type, filename=None, content_length=None):
        return BytesIO()


def create_app(config_name=None):
    """Create and configure the Flask application."""

    if config_name is None:
        config_name = os.environ.get(
            "FLASK_CONFIG",
            os.environ.get("FLASK_ENV", "development")
        )

    app = Flask(__name__)
    app.request_class = PrivateUploadRequest

    config_class = config.get(config_name)

    if config_class is None:
        available_configs = ", ".join(sorted(config))
        raise ValueError(
            f"Unknown configuration '{config_name}'. "
            f"Choose one of: {available_configs}."
        )

    # Load application configuration
    app.config.from_object(config_class)

    if hasattr(config_class, "init_app"):
        config_class.init_app(app)

    # Initialize shared extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Flask-Login configuration
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    # Import models before creating database tables
    from models.account import Account
    from models.notification import Notification
    from models.kyc_document import KycDocument
    from models.transaction import Transaction
    from models.user import User

    # Load authenticated users
    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    # Register blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.accounts import accounts_bp
    from routes.transactions import transactions_bp
    from routes.analytics import analytics_bp
    from routes.statements import statements_bp
    from routes.admin import admin_bp
    from routes.notifications import notifications_bp
    from routes.documents import documents_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(accounts_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(statements_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(documents_bp)

    # Landing page
    @app.route("/")
    def landing():
        return render_template("landing.html")

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    @app.errorhandler(RequestEntityTooLarge)
    def request_too_large(error):
        return render_template("errors/413.html"), 413

    # Create database tables
    with app.app_context():
        os.makedirs(
            os.path.join(app.root_path, "database"),
            exist_ok=True
        )
        db.create_all()

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    if not app.config["DEBUG"]:
        raise RuntimeError(
            "Do not use Flask's development server in production. "
            "Run the app with a production WSGI server instead."
        )

    app.run(
        debug=app.config["DEBUG"],
        host=app.config["HOST"],
        port=app.config["PORT"]
    )