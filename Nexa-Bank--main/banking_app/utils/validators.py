"""
Validators for NexaBank.
Server-side validation functions for all form inputs.
"""

import re
from datetime import date


def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """Validate Indian phone number (10 digits)."""
    pattern = r'^[6-9]\d{9}$'
    cleaned = phone.replace('+91', '').replace(' ', '').replace('-', '')
    return bool(re.match(pattern, cleaned))


def validate_password_strength(password: str) -> dict:
    """
    Returns a dict with:
    - valid: bool
    - score: int (0-4)
    - errors: list of failure messages
    """
    errors = []
    score = 0

    if len(password) >= 8:
        score += 1
    else:
        errors.append("Password must be at least 8 characters long.")

    if re.search(r'[A-Z]', password):
        score += 1
    else:
        errors.append("Password must contain at least one uppercase letter.")

    if re.search(r'[a-z]', password):
        score += 1
    else:
        errors.append("Password must contain at least one lowercase letter.")

    if re.search(r'\d', password):
        score += 1
    else:
        errors.append("Password must contain at least one number.")

    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 1

    return {
        'valid': len(errors) == 0,
        'score': score,
        'errors': errors
    }


def validate_age(dob: date, min_age: int = 18) -> bool:
    """Validate user meets minimum age requirement."""
    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return age >= min_age


def validate_amount(amount_str: str) -> tuple:
    """
    Validate a monetary amount.
    Returns (is_valid: bool, value: float, error: str)
    """
    try:
        amount = float(amount_str)
        if amount <= 0:
            return False, 0.0, "Amount must be greater than zero."
        if amount > 10000000:  # 1 crore limit for demo
            return False, 0.0, "Amount exceeds maximum allowed limit."
        return True, round(amount, 2), ""
    except (ValueError, TypeError):
        return False, 0.0, "Invalid amount entered."


def validate_account_number(account_number: str) -> bool:
    """Validate account number format (12-16 digits)."""
    cleaned = account_number.replace(' ', '')
    return cleaned.isdigit() and 12 <= len(cleaned) <= 16


def validate_postal_code(postal: str) -> bool:
    """Validate Indian PIN code (6 digits)."""
    return bool(re.match(r'^\d{6}$', postal.strip()))
