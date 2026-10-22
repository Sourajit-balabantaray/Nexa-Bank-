from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

# One shared instance for the entire application
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()