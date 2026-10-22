"""
Authentication routes for NexaBank.
Handles registration, login, logout, and password reset.
"""

from datetime import date, datetime
from flask import Blueprint, current_app, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from extensions import db
from models.user import User
from models.account import Account
from models.notification import Notification
from models.kyc_document import KycDocument
from utils.validators import (
    validate_email, validate_phone, validate_password_strength,
    validate_age, validate_amount
)
from utils.kyc_storage import (
    DOCUMENT_FIELDS, new_storage_key, remove_stored, store_encrypted, validate_upload,
)
from utils.transaction_utils import (
    generate_customer_id, generate_account_number,
    create_transaction, create_notification
)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


def _registration_errors(errors, status=400):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'errors': errors}), status
    for error in errors:
        flash(error, 'danger')
    return render_template('auth/register.html', form_data=request.form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        # ── Collect form data ──
        full_name = request.form.get('full_name', '').strip()
        dob_str = request.form.get('date_of_birth', '')
        gender = request.form.get('gender', '')
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        state = request.form.get('state', '').strip()
        postal_code = request.form.get('postal_code', '').strip()
        account_type = request.form.get('account_type', 'savings')
        initial_deposit_str = request.form.get('initial_deposit', '0')
        nominee_name = request.form.get('nominee_name', '').strip()
        nominee_relationship = request.form.get('nominee_relationship', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        transaction_pin = request.form.get('transaction_pin', '')
        confirm_transaction_pin = request.form.get('confirm_transaction_pin', '')

        errors = []

        # ── Server-side validation ──
        if not full_name or len(full_name) < 2:
            errors.append('Full name must be at least 2 characters.')

        if not validate_email(email):
            errors.append('Please enter a valid email address.')

        if not validate_phone(phone):
            errors.append('Please enter a valid 10-digit phone number.')

        try:
            dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
            if not validate_age(dob):
                errors.append('You must be at least 18 years old to register.')
        except (ValueError, TypeError):
            errors.append('Please enter a valid date of birth.')
            dob = None

        pw_check = validate_password_strength(password)
        if not pw_check['valid']:
            errors.extend(pw_check['errors'])

        if password != confirm_password:
            errors.append('Passwords do not match.')

        if len(transaction_pin) != 4 or not transaction_pin.isdigit():
            errors.append('Transaction PIN must be exactly 4 digits.')
        elif transaction_pin != confirm_transaction_pin:
            errors.append('Transaction PINs do not match.')

        if request.form.get('accept_terms') != 'on':
            errors.append('Please accept the Terms and Conditions to continue.')

        document_uploads = {}
        for document_type, field_name in DOCUMENT_FIELDS.items():
            metadata, upload_error = validate_upload(
                request.files.get(field_name),
                document_type,
                required=document_type in {'identity', 'address'},
            )
            if upload_error:
                errors.append(upload_error)
            elif metadata:
                document_uploads[document_type] = metadata

        valid_amount, initial_deposit, amount_err = validate_amount(initial_deposit_str)
        if not valid_amount:
            errors.append(f'Initial deposit: {amount_err}')
        elif initial_deposit < 500:
            errors.append('Minimum initial deposit is ₹500.')

        # Check for duplicates
        if User.query.filter_by(email=email).first():
            errors.append('An account with this email already exists.')
        if User.query.filter_by(phone=phone).first():
            errors.append('An account with this phone number already exists.')

        if errors:
            return _registration_errors(errors)

        stored_keys = []
        try:
            customer_id = generate_customer_id()
            user = User(
                customer_id=customer_id,
                full_name=full_name,
                date_of_birth=dob,
                gender=gender,
                email=email,
                phone=phone,
                address=address,
                city=city,
                state=state,
                postal_code=postal_code,
                role='customer'
            )
            user.set_password(password)
            user.set_pin(transaction_pin)

            db.session.add(user)
            db.session.flush()

            account = Account(
                account_number=generate_account_number(),
                user_id=user.id,
                account_type=account_type,
                nominee_name=nominee_name,
                nominee_relationship=nominee_relationship,
                status='active'
            )
            db.session.add(account)
            db.session.flush()

            create_transaction(
                account=account,
                txn_type='credit',
                amount=initial_deposit,
                description='Account Opening Deposit',
                category='other',
                sender='NexaBank',
                receiver=full_name
            )

            for document_type, metadata in document_uploads.items():
                storage_key = new_storage_key()
                store_encrypted(storage_key, metadata['content'])
                stored_keys.append(storage_key)
                db.session.add(KycDocument(
                    user_id=user.id,
                    document_type=document_type,
                    storage_key=storage_key,
                    file_extension=metadata['file_extension'],
                    mime_type=metadata['mime_type'],
                    size_bytes=metadata['size_bytes'],
                    status='pending',
                ))

            create_notification(
                user_id=user.id,
                title='Welcome to NexaBank!',
                message=f'Your account has been created successfully. Your Customer ID is {customer_id}.',
                notification_type='success'
            )
            db.session.commit()
        except OSError:
            db.session.rollback()
            for storage_key in stored_keys:
                remove_stored(storage_key)
            current_app.logger.error('Unable to store submitted KYC documents.')
            return _registration_errors(
                ['We could not securely store your documents. Please try again.'],
                status=503,
            )
        except IntegrityError:
            db.session.rollback()
            for storage_key in stored_keys:
                remove_stored(storage_key)
            if User.query.filter_by(email=email).first() or User.query.filter_by(phone=phone).first():
                return _registration_errors([
                    'An account with this email or phone number already exists.'
                ])
            current_app.logger.error('Unable to save account registration and KYC metadata.')
            return _registration_errors(
                ['We could not complete your registration. Please try again.'],
                status=500,
            )
        except SQLAlchemyError:
            db.session.rollback()
            for storage_key in stored_keys:
                remove_stored(storage_key)
            current_app.logger.error('Unable to save account registration and KYC metadata.')
            return _registration_errors(
                ['We could not complete your registration. Please try again.'],
                status=500,
            )

        flash(
            f'Account created successfully! Your Customer ID is {customer_id}. '
            'Your documents are pending verification. Please login.',
            'success',
        )
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'redirect_url': url_for('auth.login')}), 201
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form_data={})


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'

        # Allow login with email OR customer_id
        user = User.query.filter(
            (User.email == identifier.lower()) |
            (User.customer_id == identifier)
        ).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been disabled. Please contact support.', 'danger')
                return render_template('auth/login.html')

            login_user(user, remember=remember)
            next_page = request.args.get('next')

            flash(f'Welcome back, {user.full_name.split()[0]}!', 'success')

            if user.is_admin:
                return redirect(url_for('admin.dashboard'))
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Invalid credentials. Please check your Customer ID/Email and password.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """
    Demo password reset flow — no real email is sent.
    Shows a simulated OTP screen.
    """
    if request.method == 'POST':
        step = request.form.get('step', '1')

        if step == '1':
            email = request.form.get('email', '').strip().lower()
            user = User.query.filter_by(email=email).first()
            if user:
                # Store in session for demo
                session['reset_email'] = email
                session['reset_otp'] = '123456'  # Fixed demo OTP
                flash('Password reset code: 123456. Email delivery is not configured.', 'info')
                return render_template('auth/forgot_password.html', step=2, email=email)
            else:
                flash('No account found with this email address.', 'danger')

        elif step == '2':
            otp = request.form.get('otp', '')
            email = session.get('reset_email', '')
            if otp == session.get('reset_otp'):
                return render_template('auth/forgot_password.html', step=3, email=email)
            else:
                flash('Invalid code. Use the password reset code shown on screen.', 'danger')
                return render_template('auth/forgot_password.html', step=2, email=email)

        elif step == '3':
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            email = session.get('reset_email', '')

            pw_check = validate_password_strength(new_password)
            if not pw_check['valid']:
                for err in pw_check['errors']:
                    flash(err, 'danger')
                return render_template('auth/forgot_password.html', step=3, email=email)

            if new_password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return render_template('auth/forgot_password.html', step=3, email=email)

            user = User.query.filter_by(email=email).first()
            if user:
                user.set_password(new_password)
                db.session.commit()
                session.pop('reset_email', None)
                session.pop('reset_otp', None)
                flash('Password reset successfully! Please login with your new password.', 'success')
                return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html', step=1)
