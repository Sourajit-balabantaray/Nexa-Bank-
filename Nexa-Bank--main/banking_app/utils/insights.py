"""
Smart Banking Insights Engine for NexaBank.
Rule-based insights from transaction data — educational demo only.
NOT financial advice.
"""

from datetime import timedelta
from collections import defaultdict
from models.transaction import Transaction
from utils.time import utc_now


def generate_insights(account):
    """
    Analyze transaction data and return a list of insight dicts.
    Each insight has: title, message, type (info/warning/success/tip), icon
    """
    insights = []

    now = utc_now()
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago = now - timedelta(days=60)
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)

    # Get transactions
    all_txns = account.transactions.all()
    this_month_txns = account.transactions.filter(Transaction.created_at >= this_month_start).all()
    last_month_txns = account.transactions.filter(
        Transaction.created_at >= last_month_start,
        Transaction.created_at < this_month_start
    ).all()
    recent_30 = account.transactions.filter(Transaction.created_at >= thirty_days_ago).all()
    prev_30 = account.transactions.filter(
        Transaction.created_at >= sixty_days_ago,
        Transaction.created_at < thirty_days_ago
    ).all()

    if not all_txns:
        return [{
            'title': 'No Data Yet',
            'message': 'Start making transactions to see personalized insights here.',
            'type': 'info',
            'icon': 'fa-info-circle'
        }]

    # ── Insight 1: Monthly savings projection ──
    this_month_credits = sum(t.amount for t in this_month_txns if t.transaction_type == 'credit')
    this_month_debits = sum(t.amount for t in this_month_txns if t.transaction_type == 'debit')
    monthly_savings = this_month_credits - this_month_debits

    if monthly_savings > 0:
        annual_projection = monthly_savings * 12
        insights.append({
            'title': '📈 Savings Projection',
            'message': f'If your current savings pattern continues, you could save ₹{annual_projection:,.0f} this year.',
            'type': 'success',
            'icon': 'fa-chart-line'
        })

    # ── Insight 2: Spending category analysis ──
    category_spend = defaultdict(float)
    for t in this_month_txns:
        if t.transaction_type == 'debit':
            category_spend[t.category] += t.amount

    if category_spend:
        top_category = max(category_spend, key=category_spend.get)
        top_amount = category_spend[top_category]
        insights.append({
            'title': '🏆 Top Spending Category',
            'message': f'Your largest spending category this month is {top_category.title()} at ₹{top_amount:,.2f}.',
            'type': 'info',
            'icon': 'fa-tag'
        })

    # ── Insight 3: Compare spending to last month ──
    if recent_30 and prev_30:
        recent_spend = sum(t.amount for t in recent_30 if t.transaction_type == 'debit')
        prev_spend = sum(t.amount for t in prev_30 if t.transaction_type == 'debit')
        if prev_spend > 0:
            change_pct = ((recent_spend - prev_spend) / prev_spend) * 100
            if change_pct > 20:
                insights.append({
                    'title': '⚠️ Spending Increased',
                    'message': f'You spent {change_pct:.0f}% more in the last 30 days compared to the previous period.',
                    'type': 'warning',
                    'icon': 'fa-arrow-trend-up'
                })
            elif change_pct < -10:
                insights.append({
                    'title': '✅ Great Job Saving!',
                    'message': f'You reduced your spending by {abs(change_pct):.0f}% compared to last month. Keep it up!',
                    'type': 'success',
                    'icon': 'fa-piggy-bank'
                })

    # ── Insight 4: Positive balance streak ──
    positive_months = 0
    for m in range(3):
        month_start = (now.replace(day=1) - timedelta(days=m * 30)).replace(day=1)
        month_end = month_start.replace(day=28) + timedelta(days=4)
        credits = sum(t.amount for t in all_txns
                     if t.transaction_type == 'credit' and month_start <= t.created_at < month_end)
        debits = sum(t.amount for t in all_txns
                    if t.transaction_type == 'debit' and month_start <= t.created_at < month_end)
        if credits >= debits:
            positive_months += 1

    if positive_months == 3:
        insights.append({
            'title': '🎯 Positive Balance Streak',
            'message': f'You have maintained a positive cash flow for {positive_months} consecutive months. Excellent financial discipline!',
            'type': 'success',
            'icon': 'fa-trophy'
        })

    # ── Insight 5: Discretionary spending advice ──
    discretionary_categories = ['shopping', 'food', 'travel', 'other']
    discretionary_spend = sum(
        t.amount for t in this_month_txns
        if t.transaction_type == 'debit' and t.category in discretionary_categories
    )
    total_spend = sum(t.amount for t in this_month_txns if t.transaction_type == 'debit')
    if total_spend > 0 and discretionary_spend / total_spend > 0.6:
        insights.append({
            'title': '💡 Spending Tip',
            'message': f'{(discretionary_spend/total_spend*100):.0f}% of your spending this month is discretionary. Consider reducing it to increase savings.',
            'type': 'info',
            'icon': 'fa-lightbulb'
        })

    # ── Insight 6: Low balance warning ──
    if account.balance < 5000:
        insights.append({
            'title': '⚠️ Low Balance Alert',
            'message': f'Your account balance (₹{account.balance:,.2f}) is below ₹5,000. Consider topping up.',
            'type': 'warning',
            'icon': 'fa-exclamation-triangle'
        })

    return insights[:6]  # Return top 6 insights
