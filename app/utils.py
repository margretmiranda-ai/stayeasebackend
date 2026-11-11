from functools import wraps

from flask import g, jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from marshmallow import ValidationError

from .extensions import db
from .models import User


def error(message, status=400, details=None):
    body = {"error": message}
    if details:
        body["details"] = details
    return jsonify(body), status


def load_or_400(schema, data, **kwargs):
    """Validate input with a Marshmallow schema; raises ValidationError (handled globally)."""
    return schema.load(data or {}, **kwargs)


def paginate(query, schema, page, per_page):
    """Paginate a Flask-SQLAlchemy query and serialize the page."""
    result = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        "items": schema.dump(result.items, many=True),
        "page": result.page,
        "per_page": result.per_page,
        "total": result.total,
        "pages": result.pages,
    }


def roles_required(*roles, approved_only=False):
    """Protect a route: valid JWT + active user + one of the given roles.
    With approved_only=True, managers must also have been approved by an admin."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = db.session.get(User, int(get_jwt_identity()))
            if not user or not user.is_active:
                return error("Account not found or blocked", 403)
            if roles and user.role not in roles:
                return error("You do not have permission to do this", 403)
            if approved_only and user.role == "manager" and not user.is_approved:
                return error("Your manager account is waiting for admin approval", 403)
            g.current_user = user
            return fn(*args, **kwargs)

        return wrapper

    return decorator
