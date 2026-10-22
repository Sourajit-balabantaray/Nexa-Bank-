"""
Analytics routes for NexaBank.
Provides Chart.js-ready data endpoints and the analytics page.
"""

from datetime import timedelta
from collections import defaultdict
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from models.transaction import Transaction
from utils.insights import generate_insights
from utils.time import utc_now

analytics_bp = Blueprint('analytics', __name__)


def get_date_range(period):
    """Return (start_date, end_date) for a given period string."""
    now = utc_now()
    period_days = {'7d': 7, '30d': 30, '6m': 180, '1y': 365}
    return now - timedelta(days=period_days.get(period, 30)), now


@analytics_bp.route('/analytics')
@login_required
def index():
    account = current_user.primary_account
    insights = generate_insights(account) if account else []

    # Unusual transactions (for fraud alert panel)
    unusual_txns = []
    if account:
        all_debits = account.transactions.filter(
            Transaction.transaction_type == 'debit'
        ).all()
        if len(all_debits) >= 3:
            avg = sum(t.amount for t in all_debits) / len(all_debits)
            unusual_txns = [t for t in all_debits if t.amount > avg * 3 and t.amount > 5000][-3:]

    return render_template('analytics.html',
                           insights=insights,
                           unusual_txns=unusual_txns,
                           account=account)


@analytics_bp.route('/api/analytics/summary')
@login_required
def api_summary():
    account = current_user.primary_account
    if not account:
        return jsonify({'error': 'No account'}), 404

    period = request.args.get('period', '30d')
    start, end = get_date_range(period)
    previous_start = start - (end - start)

    txns = account.transactions.filter(
        Transaction.created_at.between(start, end)
    ).all()
    previous_txns = account.transactions.filter(
        Transaction.created_at >= previous_start,
        Transaction.created_at < start
    ).all()

    total_income = sum(t.amount for t in txns if t.transaction_type == 'credit')
    total_expenses = sum(t.amount for t in txns if t.transaction_type == 'debit')
    savings = total_income - total_expenses
    savings_rate = (savings / total_income * 100) if total_income > 0 else 0
    previous_expenses = sum(t.amount for t in previous_txns if t.transaction_type == 'debit')
    expense_change = (
        ((total_expenses - previous_expenses) / previous_expenses * 100)
        if previous_expenses else None
    )
    days = max((end - start).days, 1)

    return jsonify({
        'total_income': round(total_income, 2),
        'total_expenses': round(total_expenses, 2),
        'savings': round(savings, 2),
        'savings_rate': round(savings_rate, 1),
        'transaction_count': len(txns),
        'average_daily_expenses': round(total_expenses / days, 2),
        'expense_change': round(expense_change, 1) if expense_change is not None else None,
    })


@analytics_bp.route('/api/analytics/income-expenses')
@login_required
def api_income_expenses():
    """Return daily or calendar-month income and expense buckets."""
    account = current_user.primary_account
    if not account:
        return jsonify({}), 404

    period = request.args.get('period', '6m')
    if period not in {'7d', '30d', '6m', '1y'}:
        period = '6m'
    labels = []
    income_data = []
    expense_data = []
    now = utc_now()

    if period in {'7d', '30d'}:
        start, end = get_date_range(period)
        days = 7 if period == '7d' else 30
        txns = account.transactions.filter(
            Transaction.created_at >= start,
            Transaction.created_at <= end
        ).all()
        buckets = defaultdict(lambda: [0.0, 0.0])
        for txn in txns:
            buckets[txn.created_at.date()][0 if txn.transaction_type == 'credit' else 1] += txn.amount
        for offset in range(days - 1, -1, -1):
            bucket_date = (now - timedelta(days=offset)).date()
            values = buckets[bucket_date]
            labels.append(bucket_date.strftime('%d %b'))
            income_data.append(round(values[0], 2))
            expense_data.append(round(values[1], 2))
    else:
        months = 6 if period == '6m' else 12
        first_month_index = now.year * 12 + now.month - 1 - months + 1
        month_start = now.replace(
            year=first_month_index // 12,
            month=first_month_index % 12 + 1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        month_end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        txns = account.transactions.filter(
            Transaction.created_at >= month_start,
            Transaction.created_at < (
                month_end.replace(year=month_end.year + 1, month=1)
                if month_end.month == 12 else month_end.replace(month=month_end.month + 1)
            )
        ).all()
        buckets = defaultdict(lambda: [0.0, 0.0])
        for txn in txns:
            buckets[(txn.created_at.year, txn.created_at.month)][
                0 if txn.transaction_type == 'credit' else 1
            ] += txn.amount
        for offset in range(months - 1, -1, -1):
            month_index = now.year * 12 + now.month - 1 - offset
            year, month = divmod(month_index, 12)
            month += 1
            values = buckets[(year, month)]
            labels.append(now.replace(year=year, month=month, day=1).strftime('%b %Y'))
            income_data.append(round(values[0], 2))
            expense_data.append(round(values[1], 2))

    return jsonify({'labels': labels, 'income': income_data, 'expenses': expense_data})


@analytics_bp.route('/api/analytics/categories')
@login_required
def api_categories():
    """Expense by category doughnut chart."""
    account = current_user.primary_account
    if not account:
        return jsonify({}), 404

    period = request.args.get('period', '30d')
    start, end = get_date_range(period)

    txns = account.transactions.filter(
        Transaction.created_at.between(start, end),
        Transaction.transaction_type == 'debit'
    ).all()

    cat_totals = defaultdict(float)
    for t in txns:
        cat_totals[(t.category or 'other').lower()] += t.amount

    categories = sorted(cat_totals.items(), key=lambda item: item[1], reverse=True)
    labels = [category.title() for category, _ in categories]
    data = [round(amount, 2) for _, amount in categories]

    return jsonify({'labels': labels, 'data': data})


@analytics_bp.route('/api/analytics/balance-history')
@login_required
def api_balance_history():
    """Balance over time for line chart."""
    account = current_user.primary_account
    if not account:
        return jsonify({}), 404

    period = request.args.get('period', '30d')
    start, end = get_date_range(period)

    txns = account.transactions.filter(
        Transaction.created_at.between(start, end)
    ).order_by(Transaction.created_at.asc(), Transaction.id.asc()).all()

    daily_balances = {}
    for txn in txns:
        daily_balances[txn.created_at.date()] = txn.balance_after or 0
    labels = [day.strftime('%d %b') for day in daily_balances]
    balances = list(daily_balances.values())

    return jsonify({'labels': labels, 'balances': balances})


@analytics_bp.route('/api/analytics/monthly-spending')
@login_required
def api_monthly_spending():
    """Last 6 months spending bar chart."""
    return api_income_expenses()
