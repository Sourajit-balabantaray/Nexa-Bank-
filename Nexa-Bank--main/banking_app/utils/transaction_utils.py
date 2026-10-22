"""
Transaction utilities for NexaBank.
Handles transaction creation, balance updates, and ID generation.
"""

from extensions import db
from models.transaction import Transaction
from models.notification import Notification
from utils.time import utc_now


def create_transaction(account, txn_type, amount, description, category='other',
                       sender=None, receiver=None, transfer_type=None):
    """
    Create a transaction and update the account balance.

    Args:
        account: Account model instance
        txn_type: 'credit' or 'debit'
        amount: float amount
        description: transaction description
        category: transaction category
        sender: sender name/account
        receiver: receiver name/account
        transfer_type: 'internal', 'bank', 'upi', etc.

    Returns:
        Transaction instance or None on failure
    """
    if txn_type == 'debit':
        if account.balance < amount:
            return None  # Insufficient balance

    # Update balance
    if txn_type == 'credit':
        account.balance = round(account.balance + amount, 2)
    else:
        account.balance = round(account.balance - amount, 2)

    account.updated_at = utc_now()

    # Create transaction record
    txn = Transaction(
        transaction_id=Transaction.generate_transaction_id(),
        account_id=account.id,
        transaction_type=txn_type,
        category=category,
        amount=amount,
        description=description,
        sender=sender or account.user.full_name,
        receiver=receiver or account.user.full_name,
        balance_after=account.balance,
        status='success',
        transfer_type=transfer_type
    )

    db.session.add(txn)
    return txn


def check_unusual_transaction(account, amount):
    """
    Simple rule-based unusual activity detection (educational/demo).
    Returns (is_unusual: bool, reason: str)
    """
    # Get recent transaction amounts for this account
    recent_txns = account.transactions.filter(
        Transaction.transaction_type == 'debit'
    ).order_by(Transaction.created_at.desc()).limit(10).all()

    if len(recent_txns) < 3:
        return False, ""

    avg_amount = sum(t.amount for t in recent_txns) / len(recent_txns)

    # Flag if new transaction is 3x the average
    if amount > avg_amount * 3 and amount > 5000:
        return True, f"This transaction (₹{amount:,.2f}) is significantly larger than your average debit of ₹{avg_amount:,.2f}."

    return False, ""


def create_notification(user_id, title, message, notification_type='info', related_txn_id=None):
    """Create a notification for a user."""
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        related_transaction_id=related_txn_id
    )
    db.session.add(notif)
    return notif


def generate_customer_id():
    """Generate a unique customer ID like NXB20240001."""
    from models.user import User
    year = utc_now().strftime('%Y')
    count = User.query.count() + 1
    return f"NXB{year}{count:04d}"


def generate_account_number():
    """Generate a unique 12-digit account number."""
    from models.account import Account
    import random
    while True:
        number = ''.join([str(random.randint(0, 9)) for _ in range(12)])
        if not Account.query.filter_by(account_number=number).first():
            return number
