"""Authorization-checked retrieval for private KYC documents."""

from io import BytesIO

from flask import Blueprint, abort, send_file
from flask_login import current_user, login_required

from models.kyc_document import KycDocument
from utils.kyc_storage import load_decrypted

documents_bp = Blueprint('documents', __name__, url_prefix='/documents')


@documents_bp.route('/<int:document_id>')
@login_required
def download(document_id):
    document = KycDocument.query.get_or_404(document_id)
    if document.user_id != current_user.id and not current_user.is_admin:
        abort(404)

    content = load_decrypted(document.storage_key)
    response = send_file(
        BytesIO(content),
        mimetype=document.mime_type,
        as_attachment=True,
        download_name=f'{document.document_type}-document{document.file_extension}',
        max_age=0,
    )
    response.headers['Cache-Control'] = 'private, no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "sandbox; default-src 'none'"
    return response
