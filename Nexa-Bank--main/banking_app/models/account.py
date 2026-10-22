"""
Account model for NexaBank.
Each user can have one or more accounts.
"""

from extensions import db
from utils.time import utc_now


class Account(db.Model):
    __tablename__ = 'accounts'

    id = db.Column(db.Integer, primary_key=True)
    account_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Account type: savings, current, salary
    account_type = db.Column(db.String(20), nullable=False, default='savings')

    # Balance in INR (float, stored as decimal for demo purposes)
    balance = db.Column(db.Float, nullable=False, default=0.0)

    # Demo IFSC code
    ifsc_code = db.Column(db.String(15), nullable=False, default='NXAB0001234')

    # Nominee information
    nominee_name = db.Column(db.String(100), nullable=True)
    nominee_relationship = db.Column(db.String(50), nullable=True)

    # Status: active, inactive, frozen
    status = db.Column(db.String(20), nullable=False, default='active')

    opening_date = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    transactions = db.relationship(
        'Transaction',
        foreign_keys='Transaction.account_id',
        backref='account',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    @property
    def masked_number(self):
        """Return masked account number: XXXX XXXX 1234"""
        num = self.account_number
        return f"XXXX XXXX {num[-4:]}"

    @property
    def available_balance(self):
        """Available balance (same as balance in demo)."""
        return self.balance

    def __repr__(self):
        return f'<Account {self.account_number}: ₹{self.balance:.2f}>'
