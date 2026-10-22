"""Private KYC document metadata."""

from sqlalchemy import UniqueConstraint

from extensions import db
from utils.time import utc_now


class KycDocument(db.Model):
    __tablename__ = 'kyc_documents'
    __table_args__ = (
        UniqueConstraint('user_id', 'document_type', name='uq_kyc_user_document_type'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    document_type = db.Column(db.String(20), nullable=False)
    storage_key = db.Column(db.String(32), nullable=False, unique=True)
    file_extension = db.Column(db.String(5), nullable=False)
    mime_type = db.Column(db.String(40), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    rejection_reason = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', back_populates='documents')
