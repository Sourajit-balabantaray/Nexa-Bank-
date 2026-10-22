"""Validation and encrypted private storage for KYC uploads."""

import hashlib
from io import BytesIO
import os
import re
import uuid
import warnings

from PIL import Image
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from flask import current_app
from pypdf import PdfReader
from pypdf.errors import PdfReadError, PdfStreamError
from werkzeug.utils import secure_filename

MAX_DOCUMENT_SIZE = 5 * 1024 * 1024
ALLOWED_MIME_TYPES = {
    '.pdf': 'application/pdf',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
}
DOCUMENT_FIELDS = {
    'identity': 'identity_proof',
    'address': 'address_proof',
    'photograph': 'photograph',
}


def _has_valid_content(extension, content):
    if extension == '.pdf':
        try:
            document = PdfReader(BytesIO(content), strict=True)
            return not document.is_encrypted and len(document.pages) > 0
        except (PdfReadError, PdfStreamError, OSError, ValueError, EOFError):
            return False

    expected_format = {
        '.jpg': 'JPEG',
        '.jpeg': 'JPEG',
        '.png': 'PNG',
    }.get(extension)
    if not expected_format:
        return False

    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as image:
                if image.format != expected_format:
                    return False
                width, height = image.size
                if width < 1 or height < 1 or width * height > 16_000_000:
                    return False
                image.verify()
            with Image.open(BytesIO(content)) as image:
                image.load()
        return True
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        SyntaxError,
        ValueError,
    ):
        return False


def validate_upload(upload, document_type, required=True):
    """Return (validated metadata, error), without persisting document contents."""
    if upload is None or not upload.filename:
        if required:
            return None, f'{document_type.title()} document is required.'
        return None, None

    safe_name = secure_filename(upload.filename)
    extension = os.path.splitext(safe_name)[1].lower()
    expected_mime = ALLOWED_MIME_TYPES.get(extension)
    if expected_mime is None:
        return None, f'{document_type.title()} document must be a PDF, JPG, JPEG, or PNG.'
    if (upload.mimetype or '').lower() != expected_mime:
        return None, f'{document_type.title()} document content type does not match its file format.'

    try:
        content = upload.stream.read(MAX_DOCUMENT_SIZE + 1)
    except OSError:
        return None, f'{document_type.title()} document could not be read. Please choose another file.'
    if len(content) > MAX_DOCUMENT_SIZE:
        return None, f'{document_type.title()} document must be 5 MB or smaller.'
    if not content or not _has_valid_content(extension, content):
        return None, f'{document_type.title()} document is empty or has invalid file content.'

    return {
        'content': content,
        'file_extension': extension,
        'mime_type': expected_mime,
        'size_bytes': len(content),
    }, None


def _cipher():
    secret = current_app.config.get('DOCUMENT_ENCRYPTION_KEY')
    if not secret:
        secret = current_app.config['SECRET_KEY']
    key = hashlib.sha256(
        b'nexabank-private-kyc-v1\0' + secret.encode('utf-8')
    ).digest()
    return AESGCM(key)


def _storage_path():
    storage_path = os.path.realpath(current_app.config['DOCUMENT_STORAGE_PATH'])
    static_path = os.path.realpath(current_app.static_folder)
    try:
        if os.path.normcase(os.path.commonpath((storage_path, static_path))) == os.path.normcase(static_path):
            raise RuntimeError('KYC document storage must be outside the public static directory.')
    except ValueError:
        return storage_path
    return storage_path


def store_encrypted(storage_key, content):
    if not re.fullmatch(r'[0-9a-f]{32}', storage_key):
        raise ValueError('Invalid document storage key.')
    storage_path = _storage_path()
    os.makedirs(storage_path, mode=0o700, exist_ok=True)
    nonce = os.urandom(12)
    ciphertext = _cipher().encrypt(nonce, content, storage_key.encode('ascii'))
    path = os.path.join(storage_path, f'{storage_key}.enc')
    created = False
    try:
        with open(path, 'xb') as document_file:
            created = True
            document_file.write(nonce + ciphertext)
    except OSError:
        if created:
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
        raise
    return path


def load_decrypted(storage_key):
    if not re.fullmatch(r'[0-9a-f]{32}', storage_key):
        raise ValueError('Invalid document storage key.')
    path = os.path.join(_storage_path(), f'{storage_key}.enc')
    with open(path, 'rb') as document_file:
        stored = document_file.read(MAX_DOCUMENT_SIZE + 64)
    nonce, ciphertext = stored[:12], stored[12:]
    return _cipher().decrypt(nonce, ciphertext, storage_key.encode('ascii'))


def remove_stored(storage_key):
    if not re.fullmatch(r'[0-9a-f]{32}', storage_key):
        raise ValueError('Invalid document storage key.')
    path = os.path.join(_storage_path(), f'{storage_key}.enc')
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def new_storage_key():
    return uuid.uuid4().hex
