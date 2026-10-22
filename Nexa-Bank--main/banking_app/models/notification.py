"""
Notification model for NexaBank.
"""

from extensions import db
from utils.time import utc_now


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Notification type: success, warning, info, danger
    notification_type = db.Column(db.String(20), nullable=False, default='info')

    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)

    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utc_now, index=True)

    # Optional link to related transaction
    related_transaction_id = db.Column(db.String(30), nullable=True)

    def __repr__(self):
        return f'<Notification {self.id}: {self.title}>'
