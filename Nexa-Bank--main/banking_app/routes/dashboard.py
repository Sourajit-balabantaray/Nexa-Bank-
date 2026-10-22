"""
Dashboard routes for NexaBank.
"""

from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from models.account import Account
from models.transaction import Transaction
from utils.time import utc_now

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@login_required
def index():
    accounts = current_user.accounts.all()
    account = current_user.primary_account

    if not account:
        return render_template('dashboard.html',
                               account=None,
                               recent_transactions=[],
                               stats={
                                   'total_balance': 0,
                                   'available_balance': 0,
                                   'monthly_income': 0,
                                   'monthly_expenses': 0,
                                   'savings_balance': 0,
                               },
                               greeting='Welcome',
                               unusual_txns=[])

    user_transactions = Transaction.query.join(Account).filter(
        Account.user_id == current_user.id
    )
    recent_transactions = user_transactions.order_by(
        Transaction.created_at.desc()
    ).limit(10).all()

    month_start = utc_now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_txns = user_transactions.filter(
        Transaction.created_at >= month_start
    ).all()

    monthly_income = sum(t.amount for t in monthly_txns if t.transaction_type == 'credit')
    monthly_expenses = sum(t.amount for t in monthly_txns if t.transaction_type == 'debit')

    # Unusual transactions alert
    unusual_txns = []
    recent_debits = user_transactions.filter(
        Transaction.transaction_type == 'debit',
        Transaction.created_at >= utc_now() - timedelta(days=7)
    ).all()
    if recent_debits:
        all_debits = user_transactions.filter(
            Transaction.transaction_type == 'debit'
        ).all()
        if len(all_debits) >= 3:
            avg = sum(t.amount for t in all_debits) / len(all_debits)
            unusual_txns = [t for t in recent_debits if t.amount > avg * 3 and t.amount > 5000]

    stats = {
        'total_balance': sum(item.balance for item in accounts),
        'available_balance': sum(item.available_balance for item in accounts),
        'monthly_income': monthly_income,
        'monthly_expenses': monthly_expenses,
        'savings_balance': sum(
            item.balance for item in accounts if item.account_type == 'savings'
        ),
    }

    # Greeting by time of day
    hour = datetime.now().hour
    if 5 <= hour < 12:
        greeting = "Good morning"
    elif 12 <= hour < 17:
        greeting = "Good afternoon"
    elif 17 <= hour < 21:
        greeting = "Good evening"
    else:
        greeting = "Good night"

    return render_template('dashboard.html',
                           account=account,
                           recent_transactions=recent_transactions,
                           stats=stats,
                           greeting=greeting,
                           unusual_txns=unusual_txns)
