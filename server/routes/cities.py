from flask import jsonify, request

from app import app
from config import db
from helpers import error, load_or_400, roles_required
from models import City
from schemas import CitySchema

city_schema = CitySchema()


@app.get("/api/cities")
def list_cities():
    """Public: used to fill city dropdowns."""
    cities = City.query.order_by(City.name).all()
    return jsonify(city_schema.dump(cities, many=True))


@app.post("/api/cities")
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


@app.put("/api/cities/<int:city_id>")
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


@app.delete("/api/cities/<int:city_id>")
@roles_required("admin")
def delete_city(city_id):
    city = db.get_or_404(City, city_id)
    if city.properties:
        return error("Cannot delete a city that still has properties", 409)
    db.session.delete(city)
    db.session.commit()
    return "", 204
