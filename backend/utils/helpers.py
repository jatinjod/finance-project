# backend/utils/helpers.py
# Shared utility functions used across routes

import re
from datetime import date


def is_valid_email(email):
    """Validate email format."""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email)) if email else False


def is_positive_number(value):
    """Check if value is a positive number."""
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def get_first_of_month(year, month):
    """Return the first day of a given month."""
    try:
        return date(int(year), int(month), 1)
    except (ValueError, TypeError):
        return None


def safe_float(value, default=0.0):
    """Safely convert to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def success_response(data=None, message=None, code=200):
    """Standard success response format."""
    resp = {"status": "success"}
    if message:
        resp["message"] = message
    if data is not None:
        resp["data"] = data
    return resp, code


def error_response(message, code=400):
    """Standard error response format."""
    return {"error": message}, code


def paginate_list(items, page, per_page):
    """Manually paginate a Python list."""
    import math
    page     = max(1, page)
    per_page = max(1, per_page)
    total    = len(items)
    pages    = math.ceil(total / per_page) if per_page > 0 else 1
    start    = (page - 1) * per_page
    end      = start + per_page

    return {
        "items": items[start:end],
        "pagination": {
            "total":        total,
            "pages":        pages,
            "current_page": page,
            "per_page":     per_page
        }
    }