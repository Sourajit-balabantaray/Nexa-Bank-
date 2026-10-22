"""
Transaction routes for NexaBank.
Handles transfer, deposit, withdrawal, history, and details.
"""

from datetime import datetime, date
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, jsonify, send_file, abort)
from flask_login import login_required, current_user
import io

from extensions import db
from models.transaction import Transaction
from models.account import Account
from utils.validators import validate_amount
from utils.transaction_utils import (
    create_transaction, check_unusual_transaction, create_notification
)
from utils.pdf_generator import generate_receipt_pdf
from config import Config

transactions_bp = Blueprint('transactions', __name__)

CATEGORIES = ['salary', 'food', 'shopping', 'bills', 'travel',
              'education', 'transfer', 'atm', 'other']
BILL_TYPES = ('Electricity', 'Water', 'Internet', 'Gas', 'Mobile')


@transactions_bp.route('/transfer', methods=['GET', 'POST'])
@login_required
def transfer():
    account = current_user.primary_account
    if not account:
        flash('No active account found.', 'danger')
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        receiver_name = request.form.get('receiver_name', '').strip()
        receiver_account = request.form.get('receiver_account', '').strip()
        confirm_account = request.form.get('confirm_account', '').strip()
        ifsc = request.form.get('ifsc', '').strip()
        amount_str = request.form.get('amount', '')
        transfer_type = request.form.get('transfer_type', 'bank')
        description = request.form.get('description', '').strip()

        errors = []

        if not receiver_name:
            errors.append('Receiver name is required.')
        if not receiver_account:
            errors.append('Receiver account number is required.')
        if receiver_account != confirm_account:
            errors.append('Account numbers do not match.')

        valid, amount, amt_err = validate_amount(amount_str)
        if not valid:
            errors.append(amt_err)
        elif amount > account.balance:
            errors.append(f'Insufficient balance. Available: ₹{account.balance:,.2f}')

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('transfer.html', account=account, form_data=request.form)

        # Check for unusual activity
        is_unusual, unusual_reason = check_unusual_transaction(account, amount)

        # Create transaction
        txn = create_transaction(
            account=account,
            txn_type='debit',
            amount=amount,
            description=description or f'Transfer to {receiver_name}',
            category='transfer',
            sender=current_user.full_name,
            receiver=receiver_name,
            transfer_type=transfer_type
        )

        if txn is None:
            flash('Transaction failed. Insufficient balance.', 'danger')
            return render_template('transfer.html', account=account, form_data=request.form)

        # Create notification
        create_notification(
            user_id=current_user.id,
            title='Transfer Successful ✓',
            message=f'₹{amount:,.2f} transferred to {receiver_name} successfully. TXN ID: {txn.transaction_id}',
            notification_type='success',
            related_txn_id=txn.transaction_id
        )

        if is_unusual:
            create_notification(
                user_id=current_user.id,
                title='⚠️ Unusual Transaction Detected',
                message=f'An unusual transfer of ₹{amount:,.2f} was detected. {unusual_reason}',
                notification_type='warning',
                related_txn_id=txn.transaction_id
            )

        db.session.commit()

        flash(f'Transfer of ₹{amount:,.2f} to {receiver_name} successful! TXN ID: {txn.transaction_id}', 'success')
        return redirect(url_for('transactions.detail', transaction_id=txn.transaction_id))

    return render_template('transfer.html', account=account, form_data={})


@transactions_bp.route('/deposit', methods=['GET', 'POST'])
@login_required
def deposit():
    account = current_user.primary_account
    if not account:
        flash('No active account found.', 'danger')
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        amount_str = request.form.get('amount', '')
        deposit_method = request.form.get('deposit_method', 'cash')
        description = request.form.get('description', '').strip()

        valid, amount, amt_err = validate_amount(amount_str)
        if not valid:
            flash(amt_err, 'danger')
            return render_template('deposit.html', account=account)

        txn = create_transaction(
            account=account,
            txn_type='credit',
            amount=amount,
            description=description or f'Deposit via {deposit_method.replace("_", " ").title()}',
            category='other',
            sender='NexaBank / ' + deposit_method.title(),
            receiver=current_user.full_name
        )

        create_notification(
            user_id=current_user.id,
            title='Deposit Successful ✓',
            message=f'₹{amount:,.2f} deposited to your account successfully.',
            notification_type='success',
            related_txn_id=txn.transaction_id
        )

        db.session.commit()
        flash(f'Deposit of ₹{amount:,.2f} successful! TXN ID: {txn.transaction_id}', 'success')
        return redirect(url_for('transactions.detail', transaction_id=txn.transaction_id))

    return render_template('deposit.html', account=account)


@transactions_bp.route('/withdraw', methods=['GET', 'POST'])
@login_required
def withdraw():
    account = current_user.primary_account
    if not account:
        flash('No active account found.', 'danger')
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        amount_str = request.form.get('amount', '')
        withdraw_method = request.form.get('withdraw_method', 'atm')
        description = request.form.get('description', '').strip()

        valid, amount, amt_err = validate_amount(amount_str)
        if not valid:
            flash(amt_err, 'danger')
            return render_template('withdraw.html', account=account)

        if int(round(amount * 100)) % 500:
            flash('Withdrawal amount must be a multiple of ₹5.', 'danger')
            return render_template('withdraw.html', account=account)

        # Max withdrawal limit check (demo)
        if amount > Config.MAX_WITHDRAWAL_LIMIT:
            flash(f'Maximum withdrawal limit is ₹{Config.MAX_WITHDRAWAL_LIMIT:,.0f} per transaction.', 'danger')
            return render_template('withdraw.html', account=account)

        if amount > account.balance:
            flash(f'Insufficient balance. Available: ₹{account.balance:,.2f}', 'danger')
            return render_template('withdraw.html', account=account)

        # Check unusual activity
        is_unusual, unusual_reason = check_unusual_transaction(account, amount)

        txn = create_transaction(
            account=account,
            txn_type='debit',
            amount=amount,
            description=description or f'Withdrawal via {withdraw_method.upper()}',
            category='atm' if withdraw_method == 'atm' else 'other',
            sender=current_user.full_name,
            receiver='Cash Withdrawal'
        )

        if txn is None:
            flash('Transaction failed. Insufficient balance.', 'danger')
            return render_template('withdraw.html', account=account)

        create_notification(
            user_id=current_user.id,
            title='Withdrawal Successful ✓',
            message=f'₹{amount:,.2f} withdrawn from your account.',
            notification_type='success',
            related_txn_id=txn.transaction_id
        )

        if is_unusual:
            create_notification(
                user_id=current_user.id,
                title='⚠️ Unusual Activity Detected',
                message=f'Large withdrawal of ₹{amount:,.2f} detected. {unusual_reason}',
                notification_type='warning',
                related_txn_id=txn.transaction_id
            )

        db.session.commit()
        flash(f'Withdrawal of ₹{amount:,.2f} successful! TXN ID: {txn.transaction_id}', 'success')
        return redirect(url_for('transactions.detail', transaction_id=txn.transaction_id))

    return render_template('withdraw.html', account=account)


@transactions_bp.route('/pay-bills', methods=['GET', 'POST'])
@login_required
def pay_bills():
    account = current_user.primary_account
    if not account:
        flash('No active account found.', 'danger')
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        bill_type = request.form.get('bill_type', '')
        biller_reference = request.form.get('biller_reference', '').strip()
        amount_str = request.form.get('amount', '')
        if bill_type not in BILL_TYPES:
            flash('Please select a valid bill type.', 'danger')
            return render_template('pay_bills.html', account=account, bill_types=BILL_TYPES)
        if not biller_reference or len(biller_reference) > 100:
            flash('Enter a valid biller or account reference.', 'danger')
            return render_template('pay_bills.html', account=account, bill_types=BILL_TYPES)

        valid, amount, amount_error = validate_amount(amount_str)
        if not valid:
            flash(amount_error, 'danger')
            return render_template('pay_bills.html', account=account, bill_types=BILL_TYPES)
        if amount > account.balance:
            flash(f'Insufficient balance. Available: ₹{account.balance:,.2f}', 'danger')
            return render_template('pay_bills.html', account=account, bill_types=BILL_TYPES)

        txn = create_transaction(
            account=account,
            txn_type='debit',
            amount=amount,
            description=f'{bill_type} bill payment',
            category='bills',
            sender=current_user.full_name,
            receiver=biller_reference,
        )
        if txn is None:
            flash('Bill payment failed. Please check your available balance.', 'danger')
            return render_template('pay_bills.html', account=account, bill_types=BILL_TYPES)

        create_notification(
            user_id=current_user.id,
            title='Bill payment successful',
            message=f'₹{amount:,.2f} {bill_type.lower()} bill payment recorded for {biller_reference}.',
            notification_type='success',
            related_txn_id=txn.transaction_id,
        )
        db.session.commit()
        flash(f'{bill_type} bill payment of ₹{amount:,.2f} recorded successfully.', 'success')
        return redirect(url_for('transactions.detail', transaction_id=txn.transaction_id))

    return render_template('pay_bills.html', account=account, bill_types=BILL_TYPES)


@transactions_bp.route('/transactions')
@login_required
def history():
    account = current_user.primary_account
    if not account:
        return render_template('transactions/list.html', transactions=[], account=None,
                               categories=CATEGORIES)

    # Build query
    query = account.transactions

    # Filters
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '')
    txn_type = request.args.get('type', '')
    status = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    sort = request.args.get('sort', 'newest')

    if search:
        query = query.filter(
            (Transaction.transaction_id.ilike(f'%{search}%')) |
            (Transaction.description.ilike(f'%{search}%')) |
            (Transaction.category.ilike(f'%{search}%'))
        )

    if category and category in CATEGORIES:
        query = query.filter(Transaction.category == category)

    if txn_type in ['credit', 'debit']:
        query = query.filter(Transaction.transaction_type == txn_type)

    if status in ['success', 'pending', 'failed']:
        query = query.filter(Transaction.status == status)

    if date_from:
        try:
            df = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Transaction.created_at >= df)
        except ValueError:
            pass

    if date_to:
        try:
            dt = datetime.strptime(date_to, '%Y-%m-%d')
            dt = dt.replace(hour=23, minute=59, second=59)
            query = query.filter(Transaction.created_at <= dt)
        except ValueError:
            pass

    if sort == 'oldest':
        query = query.order_by(Transaction.created_at.asc())
    elif sort == 'amount_high':
        query = query.order_by(Transaction.amount.desc())
    elif sort == 'amount_low':
        query = query.order_by(Transaction.amount.asc())
    else:
        query = query.order_by(Transaction.created_at.desc())

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 15
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('transactions/list.html',
                           transactions=paginated.items,
                           pagination=paginated,
                           account=account,
                           categories=CATEGORIES,
                           filters={
                               'search': search,
                               'category': category,
                               'type': txn_type,
                               'status': status,
                               'date_from': date_from,
                               'date_to': date_to,
                               'sort': sort
                           })


@transactions_bp.route('/transactions/<transaction_id>')
@login_required
def detail(transaction_id):
    account = current_user.primary_account
    if not account:
        abort(404)

    txn = Transaction.query.filter_by(
        transaction_id=transaction_id,
        account_id=account.id
    ).first_or_404()

    return render_template('transactions/detail.html', transaction=txn, account=account)


@transactions_bp.route('/transactions/<transaction_id>/download-receipt')
@login_required
def download_receipt(transaction_id):
    account = current_user.primary_account
    if not account:
        abort(404)

    txn = Transaction.query.filter_by(
        transaction_id=transaction_id,
        account_id=account.id
    ).first_or_404()

    pdf_bytes = generate_receipt_pdf(txn, account, current_user)

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'receipt_{transaction_id}.pdf'
    )
