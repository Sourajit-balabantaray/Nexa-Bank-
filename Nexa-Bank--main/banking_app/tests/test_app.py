import os
import io
import tempfile
import unittest
from datetime import date
from unittest.mock import patch

from PIL import Image
from reportlab.pdfgen import canvas

os.environ['DATABASE_URL'] = 'sqlite://'
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

from sqlalchemy import inspect

from app import app, create_app, db
from config import ProductionConfig
from models.account import Account
from models.kyc_document import KycDocument
from models.notification import Notification
from models.transaction import Transaction
from models.user import User
from utils.kyc_storage import store_encrypted


class BankingAppTests(unittest.TestCase):
    def setUp(self):
        self.document_storage = tempfile.TemporaryDirectory()
        app.config.update(
            TESTING=True,
            WTF_CSRF_ENABLED=False,
            DOCUMENT_STORAGE_PATH=self.document_storage.name,
            DOCUMENT_ENCRYPTION_KEY='test-document-encryption-key',
        )
        self.client = app.test_client()
        with app.app_context():
            db.drop_all()
            db.create_all()
            self.user = User(
                customer_id='NXBTEST0001',
                full_name='Test Customer',
                date_of_birth=date(1990, 1, 1),
                gender='other',
                email='customer@example.com',
                phone='9876543210',
                role='customer',
            )
            self.user.set_password('StrongPass123')
            self.user.set_pin('1234')
            db.session.add(self.user)
            db.session.flush()
            self.user_id = self.user.id
            self.account = Account(
                account_number='123456789012',
                user_id=self.user.id,
                balance=1200.0,
            )
            db.session.add(self.account)
            db.session.commit()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.document_storage.cleanup()

    def login(self, client=None, email='customer@example.com', password='StrongPass123'):
        client = client or self.client
        return client.post(
            '/auth/login',
            data={'identifier': email, 'password': password},
        )

    def test_startup_creates_all_model_tables(self):
        with app.app_context():
            self.assertEqual(
                set(inspect(db.engine).get_table_names()),
            {'accounts', 'kyc_documents', 'notifications', 'transactions', 'users'},
            )

    def test_unknown_configuration_is_reported(self):
        with self.assertRaisesRegex(ValueError, "Unknown configuration 'missing'"):
            create_app('missing')

    def test_production_configuration_requires_secret_key(self):
        with patch.object(ProductionConfig, 'SECRET_KEY', None):
            with self.assertRaisesRegex(RuntimeError, 'SECRET_KEY must be set'):
                create_app('production')

    def test_production_configuration_requires_document_encryption_key(self):
        with patch.object(ProductionConfig, 'DOCUMENT_ENCRYPTION_KEY', None):
            with self.assertRaisesRegex(RuntimeError, 'DOCUMENT_ENCRYPTION_KEY must be set'):
                create_app('production')

    def test_production_configuration_uses_secure_cookies(self):
        self.assertTrue(ProductionConfig.SESSION_COOKIE_SECURE)
        self.assertFalse(ProductionConfig.DEBUG)

    def test_public_pages_render(self):
        for path in ('/', '/auth/login', '/auth/register', '/auth/forgot-password'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                page = response.get_data(as_text=True)
                if not path.startswith('/api/'):
                    self.assertIn('id="supportChatLauncher"', page)
                    self.assertIn('nexabank-rag-v3', page)
                    self.assertIn('knowledge/nexabank-help.md', page)
                if path == '/':
                    self.assertIn('data-theme="light"', page)
                    self.assertIn('Never share passwords, PINs, or identity numbers here.', page)
                    self.assertIn('Loading local help guide', page)
                    self.assertIn('Simulation only', page)
                    self.assertNotIn('Demo Banking Application', page)
                    self.assertIn('Illustrative interface preview', page)
                    self.assertIn('Smart Banking,', page)
                elif path == '/auth/login':
                    page = response.get_data(as_text=True)
                    self.assertIn('Sign in to your account', page)
                    self.assertIn('NexaBank is a banking simulation', page)
                    self.assertIn('Remember me', page)
                elif path == '/auth/register':
                    page = response.get_data(as_text=True)
                    self.assertIn('Create your account', page)
                    self.assertIn('register-field-grid', page)
                    self.assertIn('transaction_pin', page)
                    self.assertIn('accept_terms', page)

    def test_chatbot_knowledge_document_contains_article_metadata(self):
        knowledge_path = os.path.join(
            app.static_folder,
            'knowledge',
            'nexabank-help.md',
        )
        with open(knowledge_path, encoding='utf-8') as knowledge_file:
            knowledge = knowledge_file.read()

        for required_article in (
            '## Transfer money',
            '## Withdraw money',
            '## Identity verification documents',
        ):
            with self.subTest(article=required_article):
                self.assertIn(required_article, knowledge)

        article_count = knowledge.count('\nAnswer:')
        self.assertGreaterEqual(article_count, 10)
        for field in ('Keywords', 'Details', 'Link', 'Link label'):
            with self.subTest(field=field):
                self.assertEqual(article_count, knowledge.count(f'\n{field}:'))

    def test_customer_pages_and_apis_render(self):
        self.login()
        self.assertEqual(self.client.get('/admin/').status_code, 403)
        paths = (
            '/dashboard',
            '/accounts',
            '/profile',
            '/transfer',
            '/deposit',
            '/withdraw',
            '/pay-bills',
            '/transactions',
            '/analytics',
            '/statements',
            '/notifications',
            '/api/analytics/summary',
            '/api/analytics/income-expenses',
            '/api/analytics/categories',
            '/api/analytics/balance-history',
        )
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                page = response.get_data(as_text=True)
                if not path.startswith('/api/'):
                    self.assertIn('id="supportChatLauncher"', page)
                    self.assertIn('nexabank-rag-v3', page)
                    self.assertIn('knowledge/nexabank-help.md', page)
                if path == '/profile':
                    self.assertIn('Profile &amp; appearance', page)
                    self.assertIn('id="supportChatPanel"', page)
                    self.assertIn('class="settings-form-grid"', page)
                    self.assertIn('class="settings-field-grid"', page)
                    self.assertIn('href="#password-settings"', page)
                    self.assertIn('href="#security-settings"', page)
                    self.assertIn('href="#privacy-settings"', page)
                    self.assertIn('nexabank-ui-v14', page)
                if path == '/pay-bills':
                    page = response.get_data(as_text=True)
                    self.assertIn('Record bill payment', page)
                    self.assertIn('No external provider is contacted', page)
                if path == '/dashboard':
                    self.assertNotIn('Demo App', response.get_data(as_text=True))
                if path == '/analytics':
                    page = response.get_data(as_text=True)
                    self.assertIn('Financial overview', page)
                    self.assertIn('Where your money goes', page)
                    self.assertIn('data-period="7d"', page)
                    self.assertIn('nexabank-ui-v14', page)

    def test_notifications_are_private_and_can_be_marked_read(self):
        self.login()
        with app.app_context():
            notification = Notification(
                user_id=self.user_id,
                notification_type='success',
                title='Test notification',
                message='A private account update.',
            )
            db.session.add(notification)
            db.session.commit()
            notification_id = notification.id

        response = self.client.get('/notifications')
        self.assertEqual(response.status_code, 200)
        self.assertIn('A private account update.', response.get_data(as_text=True))
        response = self.client.post(f'/notifications/{notification_id}/read')
        self.assertEqual(response.status_code, 302)
        with app.app_context():
            self.assertTrue(db.session.get(Notification, notification_id).is_read)

        page = self.client.get('/dashboard').get_data(as_text=True)
        self.assertIn('Notifications', page)
        self.assertEqual(self.client.get('/api/notifications/unread-count').status_code, 404)

    def test_accounts_page_shows_balances_and_only_masked_account_number(self):
        self.login()
        response = self.client.get('/accounts')
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn('Total balance', page)
        self.assertIn('₹1,200.00', page)
        self.assertIn('Available balance', page)
        self.assertIn('XXXX XXXX 9012', page)
        self.assertIn('NXAB0001234', page)
        self.assertNotIn('123456789012', page)

    def test_dashboard_aggregates_multiple_accounts(self):
        self.login()
        with app.app_context():
            db.session.add(Account(
                account_number='998877665544',
                user_id=self.user_id,
                account_type='current',
                balance=300.0,
            ))
            db.session.commit()

        page = self.client.get('/dashboard').get_data(as_text=True)
        self.assertIn('₹1,500.00', page)
        self.assertIn('₹1,200.00', page)

    def test_analytics_summarizes_transactions_and_returns_period_buckets(self):
        self.login()
        self.client.post('/deposit', data={'amount': '100', 'deposit_method': 'cash'})
        self.client.post('/withdraw', data={'amount': '20', 'withdraw_method': 'atm'})

        summary = self.client.get('/api/analytics/summary?period=7d').get_json()
        self.assertEqual(summary['total_income'], 100.0)
        self.assertEqual(summary['total_expenses'], 20.0)
        self.assertEqual(summary['savings'], 80.0)
        self.assertEqual(summary['transaction_count'], 2)
        self.assertEqual(summary['savings_rate'], 80.0)

        daily = self.client.get('/api/analytics/income-expenses?period=7d').get_json()
        self.assertEqual(len(daily['labels']), 7)
        self.assertEqual(sum(daily['income']), 100.0)
        self.assertEqual(sum(daily['expenses']), 20.0)

        monthly = self.client.get('/api/analytics/income-expenses?period=6m').get_json()
        self.assertEqual(len(monthly['labels']), 6)
        self.assertEqual(sum(monthly['income']), 100.0)
        self.assertEqual(sum(monthly['expenses']), 20.0)

    def registration_data(self, **updates):
        data = {
            'full_name': 'New Customer',
            'date_of_birth': '1992-03-04',
            'gender': 'other',
            'email': 'new-customer@example.com',
            'phone': '9876543212',
            'account_type': 'savings',
            'initial_deposit': '500',
            'password': 'StrongPass123',
            'confirm_password': 'StrongPass123',
            'transaction_pin': '4826',
            'confirm_transaction_pin': '4826',
            'accept_terms': 'on',
        }
        data.update(updates)
        return data

    def registration_files(self):
        pdf_buffer = io.BytesIO()
        pdf = canvas.Canvas(pdf_buffer)
        pdf.drawString(30, 750, 'Synthetic KYC test file')
        pdf.save()
        jpeg_buffer = io.BytesIO()
        Image.new('RGB', (1, 1), color='white').save(jpeg_buffer, format='JPEG')
        png_buffer = io.BytesIO()
        Image.new('RGB', (1, 1), color='blue').save(png_buffer, format='PNG')
        return {
            'identity_proof': (io.BytesIO(pdf_buffer.getvalue()), 'identity.pdf', 'application/pdf'),
            'address_proof': (io.BytesIO(jpeg_buffer.getvalue()), 'address.jpg', 'image/jpeg'),
            'photograph': (io.BytesIO(png_buffer.getvalue()), 'photo.png', 'image/png'),
        }

    def registration_submission(self, **updates):
        return {**self.registration_data(**updates), **self.registration_files()}

    def test_registration_creates_user_account_and_opening_transaction(self):
        response = self.client.post(
            '/auth/register',
            data=self.registration_submission(),
            content_type='multipart/form-data',
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login', response.headers['Location'])
        self.assertEqual(self.client.get('/dashboard').status_code, 302)
        self.assertEqual(self.client.get('/documents/1').status_code, 302)
        with app.app_context():
            user = User.query.filter_by(email='new-customer@example.com').one()
            account = user.accounts.one()
            self.assertEqual(account.balance, 500.0)
            self.assertEqual(account.transactions.count(), 1)
            self.assertEqual(user.theme, 'light')
            self.assertTrue(user.check_pin('4826'))
            self.assertNotEqual(user.pin_hash, '4826')
            documents = user.documents.order_by(KycDocument.document_type).all()
            self.assertEqual([document.status for document in documents], ['pending', 'pending', 'pending'])
            document = next(document for document in documents if document.document_type == 'identity')
            stored_path = os.path.join(
                self.document_storage.name,
                f'{document.storage_key}.enc',
            )
            with open(stored_path, 'rb') as stored_file:
                self.assertNotIn(b'%PDF-', stored_file.read())
            document_id = document.id
            storage_path = os.path.normcase(os.path.realpath(self.document_storage.name))
            static_path = os.path.normcase(os.path.realpath(os.path.join(app.root_path, 'static')))
            self.assertFalse(storage_path == static_path or storage_path.startswith(static_path + os.sep))

        self.login(email='new-customer@example.com', password='StrongPass123')
        download = self.client.get(f'/documents/{document_id}')
        self.assertEqual(download.status_code, 200)
        self.assertTrue(download.data.startswith(b'%PDF-'))
        self.assertEqual(download.headers['Cache-Control'], 'private, no-store')

        other_client = app.test_client()
        with app.app_context():
            other = User(
                customer_id='NXBOTHER0001',
                full_name='Other Customer',
                date_of_birth=date(1990, 1, 1),
                gender='other',
                email='other@example.com',
                phone='9876543211',
                role='customer',
            )
            other.set_password('StrongPass123')
            db.session.add(other)
            db.session.commit()
        self.login(other_client, email='other@example.com')
        self.assertEqual(other_client.get(f'/documents/{document_id}').status_code, 404)

    def test_registration_rejects_invalid_email_missing_fields_and_password_mismatch(self):
        response = self.client.post(
            '/auth/register',
            data=self.registration_submission(email='not-an-email'),
            content_type='multipart/form-data',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('Please enter a valid email address.', response.get_data(as_text=True))

        response = self.client.post(
            '/auth/register',
            data=self.registration_submission(phone='12345'),
            content_type='multipart/form-data',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('Please enter a valid 10-digit phone number.', response.get_data(as_text=True))

        response = self.client.post(
            '/auth/register',
            data=self.registration_submission(full_name=''),
            content_type='multipart/form-data',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('Full name must be at least 2 characters.', response.get_data(as_text=True))

        response = self.client.post(
            '/auth/register',
            data=self.registration_submission(confirm_password='DifferentPass123'),
            content_type='multipart/form-data',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('Passwords do not match.', response.get_data(as_text=True))

    def test_duplicate_registration_does_not_create_another_user(self):
        first = self.client.post(
            '/auth/register',
            data=self.registration_submission(),
            content_type='multipart/form-data',
        )
        self.assertEqual(first.status_code, 302)
        data = self.registration_submission()
        response = self.client.post(
            '/auth/register',
            data=data,
            content_type='multipart/form-data',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('An account with this email already exists.', response.get_data(as_text=True))
        with app.app_context():
            self.assertEqual(User.query.filter_by(email='new-customer@example.com').count(), 1)
            self.assertEqual(KycDocument.query.join(User).filter(
                User.email == 'new-customer@example.com'
            ).count(), 3)

    def test_registration_requires_csrf_token(self):
        app.config['WTF_CSRF_ENABLED'] = True
        try:
            response = app.test_client().post(
                '/auth/register',
                data=self.registration_data(),
            )
            self.assertEqual(response.status_code, 400)
        finally:
            app.config['WTF_CSRF_ENABLED'] = False

    def test_kyc_rejects_missing_invalid_and_oversized_documents(self):
        missing = self.client.post('/auth/register', data=self.registration_data())
        self.assertEqual(missing.status_code, 200)
        self.assertIn('Identity document is required.', missing.get_data(as_text=True))

        invalid = self.registration_submission()
        invalid['identity_proof'] = (io.BytesIO(b'not a PDF'), 'identity.exe', 'application/octet-stream')
        response = self.client.post(
            '/auth/register',
            data=invalid,
            content_type='multipart/form-data',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('Identity document must be a PDF', response.get_data(as_text=True))

        wrong_mime = self.registration_submission()
        wrong_mime['identity_proof'] = (
            io.BytesIO(b'%PDF-1.4\n%%EOF'),
            'identity.pdf',
            'image/jpeg',
        )
        response = self.client.post(
            '/auth/register',
            data=wrong_mime,
            content_type='multipart/form-data',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('content type does not match', response.get_data(as_text=True))

        invalid_content = self.registration_submission()
        invalid_content['identity_proof'] = (
            io.BytesIO(b'not an actual PDF'),
            'identity.pdf',
            'application/pdf',
        )
        response = self.client.post(
            '/auth/register',
            data=invalid_content,
            content_type='multipart/form-data',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('invalid file content', response.get_data(as_text=True))

        oversized = self.registration_submission()
        oversized['identity_proof'] = (
            io.BytesIO(b'%PDF-1.4\n' + b'a' * (5 * 1024 * 1024) + b'\n%%EOF'),
            'identity.pdf',
            'application/pdf',
        )
        response = self.client.post(
            '/auth/register',
            data=oversized,
            content_type='multipart/form-data',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('must be 5 MB or smaller', response.get_data(as_text=True))
        with app.app_context():
            self.assertEqual(User.query.filter_by(email='new-customer@example.com').count(), 0)

    def test_kyc_upload_failure_does_not_create_account(self):
        with patch('routes.auth.store_encrypted', side_effect=OSError('storage unavailable')):
            response = self.client.post(
                '/auth/register',
                data=self.registration_submission(),
                content_type='multipart/form-data',
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn('could not securely store your documents', response.get_data(as_text=True))
        with app.app_context():
            self.assertEqual(User.query.filter_by(email='new-customer@example.com').count(), 0)

    def test_storage_key_collision_preserves_existing_encrypted_file(self):
        storage_key = 'a' * 32
        stored_path = os.path.join(self.document_storage.name, f'{storage_key}.enc')
        with open(stored_path, 'wb') as existing_file:
            existing_file.write(b'existing encrypted data')

        with app.app_context():
            with self.assertRaises(FileExistsError):
                store_encrypted(storage_key, b'new data')

        with open(stored_path, 'rb') as existing_file:
            self.assertEqual(existing_file.read(), b'existing encrypted data')

    def test_customer_cannot_review_or_delete_kyc_documents(self):
        self.client.post(
            '/auth/register',
            data=self.registration_submission(),
            content_type='multipart/form-data',
        )
        with app.app_context():
            document_id = KycDocument.query.order_by(KycDocument.id).first().id
        self.login()
        self.assertEqual(self.client.get('/admin/kyc').status_code, 403)
        self.assertEqual(
            self.client.post(f'/admin/kyc/{document_id}/review', data={'decision': 'verify'}).status_code,
            403,
        )

    def test_admin_can_review_and_delete_kyc_documents(self):
        self.client.post(
            '/auth/register',
            data=self.registration_submission(),
            content_type='multipart/form-data',
        )
        with app.app_context():
            documents = KycDocument.query.order_by(KycDocument.document_type).all()
            verify_id = next(document.id for document in documents if document.document_type == 'identity')
            reject_id = next(document.id for document in documents if document.document_type == 'address')
            delete_id = next(document.id for document in documents if document.document_type == 'photograph')
            delete_key = db.session.get(KycDocument, delete_id).storage_key
            admin = User(
                customer_id='NXBADMIN0002',
                full_name='KYC Admin',
                date_of_birth=date(1980, 1, 1),
                gender='other',
                email='kyc-admin@example.com',
                phone='9876543213',
                role='admin',
            )
            admin.set_password('AdminPass123')
            db.session.add(admin)
            db.session.commit()

        self.login(email='kyc-admin@example.com', password='AdminPass123')
        self.assertEqual(
            self.client.post(
                f'/admin/kyc/{verify_id}/review',
                data={'decision': 'verify'},
            ).status_code,
            302,
        )
        self.assertEqual(
            self.client.post(
                f'/admin/kyc/{reject_id}/review',
                data={'decision': 'reject', 'rejection_reason': 'Image is not readable.'},
            ).status_code,
            302,
        )
        with app.app_context():
            self.assertEqual(db.session.get(KycDocument, verify_id).status, 'verified')
            rejected = db.session.get(KycDocument, reject_id)
            self.assertEqual(rejected.status, 'rejected')
            self.assertEqual(rejected.rejection_reason, 'Image is not readable.')
            delete_path = os.path.join(self.document_storage.name, f'{delete_key}.enc')
            self.assertTrue(os.path.exists(delete_path))

        self.assertEqual(self.client.post(f'/admin/kyc/{delete_id}/delete').status_code, 302)
        self.assertFalse(os.path.exists(delete_path))

    def test_login_invalid_credentials_and_logout_flow(self):
        response = self.client.post(
            '/auth/login',
            data={'identifier': 'customer@example.com', 'password': 'wrong-password'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('Invalid credentials.', response.get_data(as_text=True))

        response = self.login()
        self.assertEqual(response.status_code, 302)
        self.assertIn('/dashboard', response.headers['Location'])
        self.assertEqual(self.client.get('/dashboard').status_code, 200)

        response = self.client.get('/auth/logout')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login', response.headers['Location'])
        self.assertEqual(self.client.get('/dashboard').status_code, 302)
        self.assertEqual(self.client.get('/profile').status_code, 302)
        login_page = self.client.get('/auth/login')
        self.assertEqual(login_page.status_code, 200)
        self.assertIn('You have been logged out successfully.', login_page.get_data(as_text=True))
        self.assertIn('id="supportChatLauncher"', login_page.get_data(as_text=True))

    def test_theme_toggle_saves_supported_theme(self):
        self.login()
        response = self.client.post('/api/toggle-theme', json={'theme': 'dark'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': 'ok', 'theme': 'dark'})

        response = self.client.post('/api/toggle-theme', json={'theme': 'invalid'})
        self.assertEqual(response.status_code, 400)

    def test_transaction_workflow_and_pdf_downloads(self):
        self.login()
        response = self.client.post(
            '/deposit',
            data={'amount': '100', 'deposit_method': 'cash'},
        )
        self.assertEqual(response.status_code, 302)
        response = self.client.post(
            '/withdraw',
            data={'amount': '50', 'withdraw_method': 'atm'},
        )
        self.assertEqual(response.status_code, 302)
        response = self.client.post(
            '/transfer',
            data={
                'receiver_name': 'Recipient',
                'receiver_account': '111122223333',
                'confirm_account': '111122223333',
                'amount': '25',
                'transfer_type': 'bank',
            },
        )
        self.assertEqual(response.status_code, 302)
        with app.app_context():
            account = Account.query.filter_by(account_number='123456789012').one()
            self.assertEqual(account.balance, 1225.0)
            transaction = account.transactions.order_by(Transaction.id.desc()).first()
            transaction_id = transaction.transaction_id

        receipt = self.client.get(f'/transactions/{transaction_id}/download-receipt')
        statement = self.client.get('/statements/download')
        self.assertEqual(receipt.status_code, 200)
        self.assertEqual(receipt.mimetype, 'application/pdf')
        self.assertEqual(statement.status_code, 200)
        self.assertEqual(statement.mimetype, 'application/pdf')

    def test_withdrawal_requires_amount_in_multiples_of_five(self):
        self.login()
        with app.app_context():
            account = Account.query.filter_by(account_number='123456789012').one()
            account_id = account.id
            starting_balance = account.balance
            starting_transactions = Transaction.query.count()

        response = self.client.post(
            '/withdraw',
            data={'amount': '12.50', 'withdraw_method': 'atm'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('Withdrawal amount must be a multiple of ₹5.', response.get_data(as_text=True))
        with app.app_context():
            self.assertEqual(db.session.get(Account, account_id).balance, starting_balance)
            self.assertEqual(Transaction.query.count(), starting_transactions)

        response = self.client.post(
            '/withdraw',
            data={'amount': '15', 'withdraw_method': 'atm'},
        )
        self.assertEqual(response.status_code, 302)
        with app.app_context():
            self.assertEqual(db.session.get(Account, account_id).balance, starting_balance - 15)

    def test_bill_payment_debits_balance_and_records_transaction(self):
        self.login()
        response = self.client.post(
            '/pay-bills',
            data={
                'bill_type': 'Electricity',
                'biller_reference': 'METER-42',
                'amount': '250',
            },
        )
        self.assertEqual(response.status_code, 302)
        with app.app_context():
            account = Account.query.filter_by(account_number='123456789012').one()
            transaction = account.transactions.filter_by(category='bills').one()
            self.assertEqual(account.balance, 950.0)
            self.assertEqual(transaction.transaction_type, 'debit')
            self.assertEqual(transaction.receiver, 'METER-42')
            self.assertEqual(transaction.description, 'Electricity bill payment')

    def test_bill_payment_rejects_invalid_type_and_insufficient_balance(self):
        self.login()
        for payment in (
            {'bill_type': 'Unknown', 'biller_reference': 'REF-1', 'amount': '100'},
            {'bill_type': 'Water', 'biller_reference': 'REF-1', 'amount': '5000'},
        ):
            with self.subTest(payment=payment):
                response = self.client.post('/pay-bills', data=payment)
                self.assertEqual(response.status_code, 200)
        with app.app_context():
            account = Account.query.filter_by(account_number='123456789012').one()
            self.assertEqual(account.balance, 1200.0)
            self.assertEqual(account.transactions.filter_by(category='bills').count(), 0)

    def test_dashboard_without_account_and_not_found_page(self):
        with app.app_context():
            user = User(
                customer_id='NXBTEST0002',
                full_name='No Account',
                date_of_birth=date(1990, 1, 1),
                gender='other',
                email='no-account@example.com',
                phone='9876543211',
                role='customer',
            )
            user.set_password('StrongPass123')
            db.session.add(user)
            db.session.commit()

        client = app.test_client()
        self.login(client, email='no-account@example.com')
        self.assertEqual(client.get('/dashboard').status_code, 200)
        self.assertEqual(client.get('/missing-page').status_code, 404)

    def test_admin_pages_render(self):
        with app.app_context():
            admin = User(
                customer_id='NXBADMIN0001',
                full_name='Test Admin',
                date_of_birth=date(1980, 1, 1),
                gender='other',
                email='admin@example.com',
                phone='9876543211',
                role='admin',
            )
            admin.set_password('AdminPass123')
            db.session.add(admin)
            db.session.commit()

        client = app.test_client()
        self.login(client, email='admin@example.com', password='AdminPass123')
        for path in ('/admin/', '/admin/users', '/admin/transactions', '/admin/kyc'):
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 200)


if __name__ == '__main__':
    unittest.main()
