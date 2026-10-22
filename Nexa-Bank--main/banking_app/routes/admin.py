"""
Admin routes for NexaBank.
Role-based admin dashboard with user and transaction management.
"""

from datetime import timedelta
from functools import wraps
from flask import Blueprint, current_app, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from extensions import db
from models.user import User
from models.account import Account
from models.transaction import Transaction
from models.kyc_document import KycDocument
from models.notification import Notification
from utils.kyc_storage import remove_stored
from utils.time import utc_now

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    # Summary stats
    total_customers = User.query.filter_by(role='customer').count()
    total_accounts = Account.query.count()
    total_transactions = Transaction.query.count()

    all_txns = Transaction.query.all()
    total_deposits = sum(t.amount for t in all_txns if t.transaction_type == 'credit')
    total_withdrawals = sum(t.amount for t in all_txns if t.transaction_type == 'debit')

    # Recent customers
    recent_customers = User.query.filter_by(role='customer').order_by(
        User.created_at.desc()
    ).limit(5).all()

    # Recent transactions
    recent_txns = Transaction.query.order_by(Transaction.created_at.desc()).limit(10).all()

    # Daily transaction counts for chart (last 7 days)
    daily_data = []
    labels = []
    for i in range(6, -1, -1):
        day = utc_now() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59)
        count = Transaction.query.filter(
            Transaction.created_at.between(day_start, day_end)
        ).count()
        daily_data.append(count)
        labels.append(day.strftime('%a'))

    return render_template('admin/dashboard.html',
                           total_customers=total_customers,
                           total_accounts=total_accounts,
                           total_transactions=total_transactions,
                           total_deposits=total_deposits,
                           total_withdrawals=total_withdrawals,
                           recent_customers=recent_customers,
                           recent_txns=recent_txns,
                           chart_labels=labels,
                           chart_data=daily_data)


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)

    query = User.query.filter_by(role='customer')

    if search:
        query = query.filter(
            (User.customer_id.ilike(f'%{search}%')) |
            (User.full_name.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%')) |
            (User.phone.ilike(f'%{search}%'))
        )

    paginated = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    return render_template('admin/users.html',
                           users=paginated.items,
                           pagination=paginated,
                           search=search)


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        return jsonify({'error': 'Cannot disable admin accounts'}), 400

    user.is_active = not user.is_active
    db.session.commit()
    status = 'enabled' if user.is_active else 'disabled'
    return jsonify({'status': 'ok', 'active': user.is_active, 'message': f'Account {status}'})


@admin_bp.route('/transactions')
@login_required
@admin_required
def transactions():
    search = request.args.get('search', '').strip()
    txn_type = request.args.get('type', '')
    category = request.args.get('category', '')
    page = request.args.get('page', 1, type=int)

    query = Transaction.query

    if search:
        query = query.filter(
            (Transaction.transaction_id.ilike(f'%{search}%')) |
            (Transaction.description.ilike(f'%{search}%'))
        )

    if txn_type in ['credit', 'debit']:
        query = query.filter(Transaction.transaction_type == txn_type)

    if category:
        query = query.filter(Transaction.category == category)

    paginated = query.order_by(Transaction.created_at.desc()).paginate(
        page=page, per_page=25, error_out=False
    )

    return render_template('admin/transactions.html',
                           transactions=paginated.items,
                           pagination=paginated,
                           search=search,
                           filters={'type': txn_type, 'category': category})


@admin_bp.route('/kyc')
@login_required
@admin_required
def kyc_review():
    documents = KycDocument.query.join(User).order_by(
        KycDocument.created_at.desc()
    ).all()
    return render_template('admin/kyc.html', documents=documents)


@admin_bp.route('/kyc/<int:document_id>/review', methods=['POST'])
@login_required
@admin_required
def review_kyc(document_id):
    document = KycDocument.query.get_or_404(document_id)
    decision = request.form.get('decision')
    rejection_reason = request.form.get('rejection_reason', '').strip()

    if decision == 'reject':
        if not rejection_reason:
            flash('Provide a rejection reason before rejecting a document.', 'danger')
            return redirect(url_for('admin.kyc_review'))
        document.status = 'rejected'
        document.rejection_reason = rejection_reason[:500]
    elif decision == 'verify':
        document.status = 'verified'
        document.rejection_reason = None
    else:
        flash('Choose a valid document review action.', 'danger')
        return redirect(url_for('admin.kyc_review'))

    document.reviewed_at = utc_now()
    db.session.add(Notification(
        user_id=document.user_id,
        notification_type='success' if decision == 'verify' else 'warning',
        title='KYC document reviewed',
        message=(
            f'Your {document.document_type} document has been verified.'
            if decision == 'verify'
            else f'Your {document.document_type} document was rejected: {document.rejection_reason}'
        ),
    ))
    db.session.commit()
    flash('Document review saved.', 'success')
    return redirect(url_for('admin.kyc_review'))


@admin_bp.route('/kyc/<int:document_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_kyc_document(document_id):
    document = KycDocument.query.get_or_404(document_id)
    storage_key = document.storage_key
    db.session.delete(document)
    db.session.commit()
    try:
        remove_stored(storage_key)
    except OSError:
        current_app.logger.error('KYC metadata was deleted but encrypted file cleanup failed.')
        flash('The document record was removed, but encrypted file cleanup needs administrator attention.', 'danger')
        return redirect(url_for('admin.kyc_review'))
    flash('KYC document and encrypted file deleted.', 'success')
    return redirect(url_for('admin.kyc_review'))
