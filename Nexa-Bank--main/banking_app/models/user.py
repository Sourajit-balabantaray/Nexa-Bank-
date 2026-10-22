"""
User model for NexaBank.
Handles customer and admin accounts.
"""

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from utils.time import utc_now


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    # Unique customer identifier (e.g., NXB20240001)
    customer_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(50), nullable=True)
    state = db.Column(db.String(50), nullable=True)
    postal_code = db.Column(db.String(10), nullable=True)

    # Security — password is NEVER stored as plain text
    password_hash = db.Column(db.String(256), nullable=False)

    # Role: 'customer' or 'admin'
    role = db.Column(db.String(20), nullable=False, default='customer')

    # Demo PIN (hashed) for withdrawal confirmation
    pin_hash = db.Column(db.String(256), nullable=True)

    # Theme preference
    theme = db.Column(db.String(10), default='light')

    # Account status
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    accounts = db.relationship('Account', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    documents = db.relationship(
        'KycDocument',
        back_populates='user',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )

    def set_password(self, password):
        """Hash and store the password securely."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify the password against its hash."""
        return check_password_hash(self.password_hash, password)

    def set_pin(self, pin):
        """Hash and store PIN."""
        self.pin_hash = generate_password_hash(pin)

    def check_pin(self, pin):
        """Verify PIN."""
        if not self.pin_hash:
            return False
        return check_password_hash(self.pin_hash, pin)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def primary_account(self):
        """Return the user's first active account."""
        return self.accounts.filter_by(status='active').first()

    def __repr__(self):
        return f'<User {self.customer_id}: {self.full_name}>'
