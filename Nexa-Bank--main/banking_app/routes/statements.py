"""
Bank Statement routes for NexaBank.
"""

from datetime import datetime, timedelta
import io
from flask import Blueprint, render_template, request, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from models.transaction import Transaction
from utils.pdf_generator import generate_statement_pdf
from utils.time import utc_now

statements_bp = Blueprint('statements', __name__)


@statements_bp.route('/statements', methods=['GET', 'POST'])
@login_required
def index():
    account = current_user.primary_account
    if not account:
        flash('No active account found.', 'danger')
        return redirect(url_for('dashboard.index'))

    # Default to last 30 days
    end_date = utc_now()
    start_date = end_date - timedelta(days=30)
    transactions = []

    if request.method == 'POST' or request.args.get('start_date'):
        start_str = request.form.get('start_date') or request.args.get('start_date', '')
        end_str = request.form.get('end_date') or request.args.get('end_date', '')

        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d')
        except ValueError:
            start_date = end_date - timedelta(days=30)

        try:
            end_date = datetime.strptime(end_str, '%Y-%m-%d').replace(
                hour=23, minute=59, second=59
            )
        except ValueError:
            end_date = utc_now()

    transactions = account.transactions.filter(
        Transaction.created_at >= start_date,
        Transaction.created_at <= end_date
    ).order_by(Transaction.created_at.desc()).all()

    return render_template('statements.html',
                           account=account,
                           transactions=transactions,
                           start_date=start_date,
                           end_date=end_date)


@statements_bp.route('/statements/download')
@login_required
def download():
    account = current_user.primary_account
    if not account:
        flash('No active account found.', 'danger')
        return redirect(url_for('dashboard.index'))

    start_str = request.args.get('start_date', '')
    end_str = request.args.get('end_date', '')

    end_date = utc_now()
    start_date = end_date - timedelta(days=30)

    try:
        start_date = datetime.strptime(start_str, '%Y-%m-%d')
    except ValueError:
        pass

    try:
        end_date = datetime.strptime(end_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    except ValueError:
        pass

    transactions = account.transactions.filter(
        Transaction.created_at >= start_date,
        Transaction.created_at <= end_date
    ).order_by(Transaction.created_at.asc()).all()

    pdf_bytes = generate_statement_pdf(transactions, account, current_user, start_date, end_date)

    filename = f"statement_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )
