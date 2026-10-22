"""
Account routes for NexaBank.
Handles account details and profile settings.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.account import Account
from models.kyc_document import KycDocument
from utils.validators import validate_email, validate_phone, validate_password_strength
from utils.time import utc_now

accounts_bp = Blueprint('accounts', __name__)


@accounts_bp.route('/accounts')
@login_required
def index():
    accounts = current_user.accounts.all()
    total_balance = sum(account.balance for account in accounts)
    available_balance = sum(account.available_balance for account in accounts)
    return render_template(
        'accounts.html',
        accounts=accounts,
        total_balance=total_balance,
        available_balance=available_balance,
    )


@accounts_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_personal':
            full_name = request.form.get('full_name', '').strip()
            address = request.form.get('address', '').strip()
            city = request.form.get('city', '').strip()
            state = request.form.get('state', '').strip()
            postal_code = request.form.get('postal_code', '').strip()
            theme = request.form.get('theme', 'light')

            if not full_name or len(full_name) < 2:
                flash('Full name must be at least 2 characters.', 'danger')
                return redirect(url_for('accounts.profile'))

            if theme not in {'light', 'dark'}:
                flash('Please select a valid theme.', 'danger')
                return redirect(url_for('accounts.profile'))

            current_user.full_name = full_name
            current_user.address = address
            current_user.city = city
            current_user.state = state
            current_user.postal_code = postal_code
            current_user.theme = theme
            current_user.updated_at = utc_now()
            db.session.commit()
            flash('Personal information updated successfully.', 'success')

        elif action == 'change_password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')

            if not current_user.check_password(current_password):
                flash('Current password is incorrect.', 'danger')
                return redirect(url_for('accounts.profile'))

            pw_check = validate_password_strength(new_password)
            if not pw_check['valid']:
                for err in pw_check['errors']:
                    flash(err, 'danger')
                return redirect(url_for('accounts.profile'))

            if new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
                return redirect(url_for('accounts.profile'))

            current_user.set_password(new_password)
            db.session.commit()
            flash('Password changed successfully.', 'success')

        elif action == 'change_pin':
            # Demo PIN change
            current_pin = request.form.get('current_pin', '')
            new_pin = request.form.get('new_pin', '')
            confirm_pin = request.form.get('confirm_pin', '')

            if not current_user.check_pin(current_pin):
                flash('Current PIN is incorrect.', 'danger')
                return redirect(url_for('accounts.profile'))

            if len(new_pin) != 4 or not new_pin.isdigit():
                flash('PIN must be exactly 4 digits.', 'danger')
                return redirect(url_for('accounts.profile'))

            if new_pin != confirm_pin:
                flash('PINs do not match.', 'danger')
                return redirect(url_for('accounts.profile'))

            current_user.set_pin(new_pin)
            db.session.commit()
            flash('Transaction PIN changed successfully.', 'success')

        return redirect(url_for('accounts.profile'))

    account = current_user.primary_account
    documents = current_user.documents.order_by(
        KycDocument.created_at.desc()
    ).all()
    return render_template('profile.html', account=account, documents=documents)


@accounts_bp.route('/api/toggle-theme', methods=['POST'])
@login_required
def toggle_theme():
    """API endpoint to toggle dark/light mode."""
    data = request.get_json()
    theme = data.get('theme', 'light')
    if theme not in {'light', 'dark'}:
        return jsonify({'status': 'error', 'message': 'Invalid theme.'}), 400
    current_user.theme = theme
    db.session.commit()
    return jsonify({'status': 'ok', 'theme': theme})
