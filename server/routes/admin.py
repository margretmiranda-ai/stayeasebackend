from decimal import Decimal

from flask import g, jsonify, request
from sqlalchemy import func

from app import app
from config import db
from helpers import error, load_or_400, paginate, roles_required
from models import Booking, City, Property, Unit, User
from schemas import (
    AdminUserUpdateSchema,
    PropertySchema,
    PropertyStatusSchema,
    StatusFilterSchema,
    UserFilterSchema,
    UserSchema,
)

user_schema = UserSchema()
property_schema = PropertySchema()


@app.get("/api/admin/users")
@roles_required("admin")
def list_users():
    f = load_or_400(UserFilterSchema(), request.args.to_dict())
    query = User.query
    for field in ("role", "is_approved", "is_active"):
        if field in f:
            query = query.filter(getattr(User, field) == f[field])
    query = query.order_by(User.created_at.desc())
    return jsonify(paginate(query, user_schema, f["page"], f["per_page"]))


@app.patch("/api/admin/users/<int:user_id>")
@roles_required("admin")
def update_user(user_id):
    user = db.get_or_404(User, user_id)
    data = load_or_400(AdminUserUpdateSchema(), request.get_json(silent=True))
    if user.id == g.current_user.id and data.get("is_active") is False:
        return error("You cannot block your own account", 400)
    for key, value in data.items():
        setattr(user, key, value)
    db.session.commit()
    return jsonify(user_schema.dump(user))


@app.get("/api/admin/properties")
@roles_required("admin")
def list_all_properties():
    """All properties in every status. Use ?status=pending to see those waiting for review."""
    f = load_or_400(StatusFilterSchema(), request.args.to_dict())
    query = Property.query
    if f.get("status"):
        query = query.filter(Property.status == f["status"])
    query = query.order_by(Property.created_at.desc())
    return jsonify(paginate(query, property_schema, f["page"], f["per_page"]))


@app.patch("/api/admin/properties/<int:property_id>/status")
@roles_required("admin")
def set_property_status(property_id):
    prop = db.get_or_404(Property, property_id)
    prop.status = load_or_400(PropertyStatusSchema(), request.get_json(silent=True))["status"]
    db.session.commit()
    return jsonify(property_schema.dump(prop))


@app.get("/api/admin/stats")
@roles_required("admin")
def stats():
    revenue = (
        db.session.query(func.coalesce(func.sum(Booking.total_price), 0))
        .filter(Booking.status.in_(("confirmed", "completed")))
        .scalar()
    )
    return jsonify(
        {
            "users": {
                "managers": User.query.filter_by(role="manager").count(),
                "pending_managers": User.query.filter_by(role="manager", is_approved=False).count(),
                "customers": User.query.filter_by(role="customer").count(),
            },
            "cities": City.query.count(),
            "properties": {
                "total": Property.query.count(),
                "pending": Property.query.filter_by(status="pending").count(),
                "approved": Property.query.filter_by(status="approved").count(),
                "rejected": Property.query.filter_by(status="rejected").count(),
            },
            "units": Unit.query.count(),
            "bookings": {
                "total": Booking.query.count(),
                "pending": Booking.query.filter_by(status="pending").count(),
                "confirmed": Booking.query.filter_by(status="confirmed").count(),
                "cancelled": Booking.query.filter_by(status="cancelled").count(),
                "completed": Booking.query.filter_by(status="completed").count(),
            },
            "revenue": str(Decimal(revenue).quantize(Decimal("0.01"))),
        }
    )
