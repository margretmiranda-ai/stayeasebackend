from flask import Blueprint, g, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from ..extensions import db
from ..models import City, Property, Unit, User
from ..schemas import BrowseQuerySchema, PageSchema, PropertySchema
from ..utils import error, load_or_400, paginate, roles_required

properties_bp = Blueprint("properties", __name__)
property_schema = PropertySchema()


def apply_property_filters(query, f):
    """Shared filters for browsing properties (city, area, unit type, price range)."""
    if f.get("city_id"):
        query = query.filter(Property.city_id == f["city_id"])
    if f.get("city"):
        query = query.join(City).filter(City.name.ilike(f"%{f['city']}%"))
    if f.get("area"):
        query = query.filter(Property.area.ilike(f"%{f['area']}%"))

    unit_conditions = []
    if f.get("unit_type"):
        unit_conditions.append(Unit.unit_type == f["unit_type"])
    if f.get("min_price") is not None:
        unit_conditions.append(Unit.price_per_month >= f["min_price"])
    if f.get("max_price") is not None:
        unit_conditions.append(Unit.price_per_month <= f["max_price"])
    if unit_conditions:
        query = query.filter(Property.units.any(db.and_(*unit_conditions)))
    return query


@properties_bp.get("")
def browse_properties():
    """Public: approved properties with their units. Supports city/area/type/price filters."""
    f = load_or_400(BrowseQuerySchema(), request.args.to_dict())
    query = Property.query.filter(Property.status == "approved")
    query = apply_property_filters(query, f).order_by(Property.created_at.desc())
    return jsonify(paginate(query, property_schema, f["page"], f["per_page"]))


@properties_bp.get("/mine")
@roles_required("manager")
def my_properties():
    f = load_or_400(PageSchema(), request.args.to_dict())
    query = Property.query.filter_by(manager_id=g.current_user.id).order_by(Property.created_at.desc())
    return jsonify(paginate(query, property_schema, f["page"], f["per_page"]))


@properties_bp.get("/<int:property_id>")
def get_property(property_id):
    prop = db.get_or_404(Property, property_id)
    if prop.status != "approved":
        # unapproved listings are only visible to their manager or an admin
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        viewer = db.session.get(User, int(identity)) if identity else None
        allowed = viewer and (viewer.role == "admin" or viewer.id == prop.manager_id)
        if not allowed:
            return error("Property not found", 404)
    return jsonify(property_schema.dump(prop))


@properties_bp.post("")
@roles_required("manager", approved_only=True)
def create_property():
    data = load_or_400(property_schema, request.get_json(silent=True))
    if not db.session.get(City, data["city_id"]):
        return error("City does not exist", 404)
    prop = Property(manager_id=g.current_user.id, status="pending", **data)
    db.session.add(prop)
    db.session.commit()
    return jsonify(property_schema.dump(prop)), 201


@properties_bp.put("/<int:property_id>")
@roles_required("manager", approved_only=True)
def update_property(property_id):
    prop = db.get_or_404(Property, property_id)
    if prop.manager_id != g.current_user.id:
        return error("You can only edit your own properties", 403)
    data = load_or_400(property_schema, request.get_json(silent=True), partial=True)
    if "city_id" in data and not db.session.get(City, data["city_id"]):
        return error("City does not exist", 404)
    for key, value in data.items():
        setattr(prop, key, value)
    db.session.commit()
    return jsonify(property_schema.dump(prop))


@properties_bp.delete("/<int:property_id>")
@roles_required("manager", "admin")
def delete_property(property_id):
    prop = db.get_or_404(Property, property_id)
    user = g.current_user
    if user.role == "manager" and prop.manager_id != user.id:
        return error("You can only delete your own properties", 403)
    db.session.delete(prop)
    db.session.commit()
    return "", 204
