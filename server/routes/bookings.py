from decimal import Decimal
from math import ceil

from flask import g, jsonify, request

from server.app import app
from server.config import db
from server.helpers import error, load_or_400, paginate, roles_required
from server.models import Booking, Property, Unit
from server.schemas import BookingSchema, BookingStatusSchema, PageSchema, StatusFilterSchema

booking_schema = BookingSchema()

# current status -> statuses it may move to
TRANSITIONS = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"cancelled", "completed"},
}


def months_between(start, end):
    """Rent is charged per month; part of a month counts as a full month."""
    return max(1, ceil((end - start).days / 30))


def can_view(user, booking):
    if user.role == "admin":
        return True
    if user.role == "customer":
        return booking.customer_id == user.id
    return booking.unit.property.manager_id == user.id


@app.post("/api/bookings")
@roles_required("customer")
def create_booking():
    data = load_or_400(booking_schema, request.get_json(silent=True))
    unit = db.session.get(Unit, data["unit_id"])
    if not unit or unit.property.status != "approved":
        return error("Unit not found", 404)
    if unit.available_units < 1:
        return error("No units of this type are currently available", 409)

    months = months_between(data["start_date"], data["end_date"])
    booking = Booking(
        customer_id=g.current_user.id,
        unit_id=unit.id,
        start_date=data["start_date"],
        end_date=data["end_date"],
        total_price=Decimal(unit.price_per_month) * months,
        status="pending",
    )
    db.session.add(booking)
    db.session.commit()
    return jsonify(booking_schema.dump(booking)), 201


@app.get("/api/bookings/mine")
@roles_required("customer")
def my_bookings():
    f = load_or_400(StatusFilterSchema(), request.args.to_dict())
    query = Booking.query.filter_by(customer_id=g.current_user.id)
    if f.get("status"):
        query = query.filter(Booking.status == f["status"])
    query = query.order_by(Booking.created_at.desc())
    return jsonify(paginate(query, booking_schema, f["page"], f["per_page"]))


@app.get("/api/bookings")
@roles_required("manager", "admin")
def list_bookings():
    """Managers see bookings for their own properties; admins see everything."""
    f = load_or_400(StatusFilterSchema(), request.args.to_dict())
    query = Booking.query
    if g.current_user.role == "manager":
        query = (
            query.join(Unit, Booking.unit_id == Unit.id)
            .join(Property, Unit.property_id == Property.id)
            .filter(Property.manager_id == g.current_user.id)
        )
    if f.get("status"):
        query = query.filter(Booking.status == f["status"])
    query = query.order_by(Booking.created_at.desc())
    return jsonify(paginate(query, booking_schema, f["page"], f["per_page"]))


@app.get("/api/bookings/<int:booking_id>")
@roles_required()
def get_booking(booking_id):
    booking = db.get_or_404(Booking, booking_id)
    if not can_view(g.current_user, booking):
        return error("Booking not found", 404)
    return jsonify(booking_schema.dump(booking))


@app.patch("/api/bookings/<int:booking_id>/status")
@roles_required()
def update_booking_status(booking_id):
    booking = db.get_or_404(Booking, booking_id)
    user = g.current_user
    if not can_view(user, booking):
        return error("Booking not found", 404)

    new_status = load_or_400(BookingStatusSchema(), request.get_json(silent=True))["status"]

    # customers may only cancel their own bookings
    if user.role == "customer" and new_status != "cancelled":
        return error("Customers can only cancel their bookings", 403)
    if new_status not in TRANSITIONS.get(booking.status, set()):
        return error(f"Cannot change a {booking.status} booking to {new_status}", 409)

    unit = booking.unit
    if new_status == "confirmed":
        if unit.available_units < 1:
            return error("No units of this type are available to confirm", 409)
        unit.available_units -= 1
    elif booking.status == "confirmed" and new_status in ("cancelled", "completed"):
        unit.available_units = min(unit.total_units, unit.available_units + 1)

    booking.status = new_status
    db.session.commit()
    return jsonify(booking_schema.dump(booking))
