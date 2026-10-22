"""
Transaction model for NexaBank.
Records every financial operation.
"""

import uuid
from extensions import db
from utils.time import utc_now


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)

    # Unique transaction reference (e.g., TXN20240001ABCD)
    transaction_id = db.Column(db.String(30), unique=True, nullable=False, index=True)

    # The account this transaction belongs to
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)

    # Type: credit, debit
    transaction_type = db.Column(db.String(10), nullable=False)

    # Category: salary, food, shopping, bills, travel, education, transfer, atm, other
    category = db.Column(db.String(30), nullable=False, default='other')

    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    # Sender/Receiver names or account references (for display)
    sender = db.Column(db.String(100), nullable=True)
    receiver = db.Column(db.String(100), nullable=True)

    # Balance after this transaction
    balance_after = db.Column(db.Float, nullable=True)

    # Status: success, pending, failed
    status = db.Column(db.String(20), nullable=False, default='success')

    # Transfer type (for transfers): internal, bank, upi
    transfer_type = db.Column(db.String(20), nullable=True)

    created_at = db.Column(db.DateTime, default=utc_now, index=True)

    @staticmethod
    def generate_transaction_id():
        """Generate a unique transaction ID."""
        timestamp = utc_now().strftime('%Y%m%d%H%M%S')
        unique_suffix = uuid.uuid4().hex[:6].upper()
        return f"TXN{timestamp}{unique_suffix}"

    @property
    def is_credit(self):
        return self.transaction_type == 'credit'

    @property
    def is_debit(self):
        return self.transaction_type == 'debit'

    @property
    def formatted_amount(self):
        return f"₹{self.amount:,.2f}"

    def __repr__(self):
        return f'<Transaction {self.transaction_id}: {self.transaction_type} ₹{self.amount}>'
