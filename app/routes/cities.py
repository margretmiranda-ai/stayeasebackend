from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import City
from ..schemas import CitySchema
from ..utils import error, load_or_400, roles_required

cities_bp = Blueprint("cities", __name__)
city_schema = CitySchema()


@cities_bp.get("")
def list_cities():
    """Public: used to fill city dropdowns."""
    cities = City.query.order_by(City.name).all()
    return jsonify(city_schema.dump(cities, many=True))


@cities_bp.post("")
@roles_required("admin")
def create_city():
    data = load_or_400(city_schema, request.get_json(silent=True))
    name = data["name"].strip().title()
    if City.query.filter(db.func.lower(City.name) == name.lower()).first():
        return error("City already exists", 409)
    city = City(name=name)
    db.session.add(city)
    db.session.commit()
    return jsonify(city_schema.dump(city)), 201


@cities_bp.put("/<int:city_id>")
@roles_required("admin")
def update_city(city_id):
    city = db.get_or_404(City, city_id)
    data = load_or_400(city_schema, request.get_json(silent=True))
    name = data["name"].strip().title()
    clash = City.query.filter(db.func.lower(City.name) == name.lower(), City.id != city_id).first()
    if clash:
        return error("Another city already has that name", 409)
    city.name = name
    db.session.commit()
    return jsonify(city_schema.dump(city))


@cities_bp.delete("/<int:city_id>")
@roles_required("admin")
def delete_city(city_id):
    city = db.get_or_404(City, city_id)
    if city.properties:
        return error("Cannot delete a city that still has properties", 409)
    db.session.delete(city)
    db.session.commit()
    return "", 204
