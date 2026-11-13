from flask import g, jsonify, request

from app import app
from config import db
from helpers import error, load_or_400, paginate, roles_required
from models import City, Property, Unit
from schemas import BrowseQuerySchema, UnitListSchema, UnitSchema

unit_schema = UnitSchema()
unit_list_schema = UnitListSchema()


@app.get("/api/units")
def browse_units():
    """Public: compare prices across managers. Filter by city, type and price, sort by price."""
    f = load_or_400(BrowseQuerySchema(), request.args.to_dict())

    query = Unit.query.join(Property).filter(Property.status == "approved")
    if f.get("city_id"):
        query = query.filter(Property.city_id == f["city_id"])
    if f.get("city"):
        query = query.join(City, Property.city_id == City.id).filter(City.name.ilike(f"%{f['city']}%"))
    if f.get("area"):
        query = query.filter(Property.area.ilike(f"%{f['area']}%"))
    if f.get("unit_type"):
        query = query.filter(Unit.unit_type == f["unit_type"])
    if f.get("min_price") is not None:
        query = query.filter(Unit.price_per_month >= f["min_price"])
    if f.get("max_price") is not None:
        query = query.filter(Unit.price_per_month <= f["max_price"])

    order = {
        "price_asc": Unit.price_per_month.asc(),
        "price_desc": Unit.price_per_month.desc(),
        "newest": Unit.created_at.desc(),
    }[f["sort"]]
    query = query.order_by(order)
    return jsonify(paginate(query, unit_list_schema, f["page"], f["per_page"]))


@app.get("/api/units/<int:unit_id>")
def get_unit(unit_id):
    unit = db.get_or_404(Unit, unit_id)
    if unit.property.status != "approved":
        return error("Unit not found", 404)
    return jsonify(unit_list_schema.dump(unit))


def _own_property_or_error(property_id):
    prop = db.get_or_404(Property, property_id)
    if prop.manager_id != g.current_user.id:
        return None, error("You can only manage units in your own properties", 403)
    return prop, None


@app.post("/api/properties/<int:property_id>/units")
@roles_required("manager", approved_only=True)
def create_unit(property_id):
    prop, err = _own_property_or_error(property_id)
    if err:
        return err
    data = load_or_400(unit_schema, request.get_json(silent=True))
    data.setdefault("total_units", 1)
    data.setdefault("available_units", data["total_units"])
    if data["available_units"] > data["total_units"]:
        return error("available_units cannot exceed total_units", 400)
    unit = Unit(property_id=prop.id, **data)
    db.session.add(unit)
    db.session.commit()
    return jsonify(unit_schema.dump(unit)), 201


@app.put("/api/units/<int:unit_id>")
@roles_required("manager", approved_only=True)
def update_unit(unit_id):
    unit = db.get_or_404(Unit, unit_id)
    if unit.property.manager_id != g.current_user.id:
        return error("You can only edit units in your own properties", 403)
    data = load_or_400(unit_schema, request.get_json(silent=True), partial=True)
    for key, value in data.items():
        setattr(unit, key, value)
    if unit.available_units > unit.total_units:
        db.session.rollback()
        return error("available_units cannot exceed total_units", 400)
    db.session.commit()
    return jsonify(unit_schema.dump(unit))


@app.delete("/api/units/<int:unit_id>")
@roles_required("manager", "admin")
def delete_unit(unit_id):
    unit = db.get_or_404(Unit, unit_id)
    user = g.current_user
    if user.role == "manager" and unit.property.manager_id != user.id:
        return error("You can only delete units in your own properties", 403)
    db.session.delete(unit)
    db.session.commit()
    return "", 204
