import click
from flask import Flask, jsonify
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException

from config import Config

from .extensions import cors, db, jwt, migrate
from .models import City, Property, Unit, User
from .routes import register_blueprints

DEFAULT_CITIES = ["Nairobi", "Mombasa", "Nakuru", "Naivasha", "Kisumu", "Eldoret", "Thika", "Nyeri"]


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    register_blueprints(app)
    register_error_handlers(app)
    register_commands(app)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    return app


def register_error_handlers(app):
    @app.errorhandler(ValidationError)
    def handle_validation(err):
        return jsonify({"error": "Validation failed", "details": err.messages}), 400

    @app.errorhandler(HTTPException)
    def handle_http(err):
        return jsonify({"error": err.description}), err.code

    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify({"error": "Authentication required", "details": reason}), 401

    @jwt.invalid_token_loader
    def bad_token(reason):
        return jsonify({"error": "Invalid token", "details": reason}), 401

    @jwt.expired_token_loader
    def expired_token(header, payload):
        return jsonify({"error": "Token has expired, please log in again"}), 401


def register_commands(app):
    @app.cli.command("seed")
    @click.option("--demo", is_flag=True, help="Also create a demo manager, customer and listings.")
    def seed(demo):
        """Create tables, default cities and the first admin account."""
        db.create_all()

        for name in DEFAULT_CITIES:
            if not City.query.filter_by(name=name).first():
                db.session.add(City(name=name))

        admin_email = app.config["ADMIN_EMAIL"].lower()
        if not User.query.filter_by(email=admin_email).first():
            admin = User(name=app.config["ADMIN_NAME"], email=admin_email, role="admin")
            admin.set_password(app.config["ADMIN_PASSWORD"])
            db.session.add(admin)
            click.echo(f"Admin created: {admin_email}")
        db.session.commit()

        if demo:
            seed_demo_data()
        click.echo("Seeding complete.")


def seed_demo_data():
    if User.query.filter_by(email="manager@rental.com").first():
        click.echo("Demo data already exists, skipping.")
        return

    manager = User(name="Demo Manager", email="manager@rental.com", phone="0700000001", role="manager")
    manager.set_password("Manager@1234")
    customer = User(name="Demo Customer", email="customer@rental.com", phone="0700000002", role="customer")
    customer.set_password("Customer@1234")
    db.session.add_all([manager, customer])
    db.session.flush()

    naivasha = City.query.filter_by(name="Naivasha").first()
    nairobi = City.query.filter_by(name="Nairobi").first()
    agunda = Property(
        manager_id=manager.id, city_id=naivasha.id, name="Agunda Apartments", area="Section 8",
        description="Quiet apartments close to the lake.", status="approved",
    )
    kilimani = Property(
        manager_id=manager.id, city_id=nairobi.id, name="Kilimani Heights", area="Kilimani",
        description="Modern apartments with parking and a gym.", status="approved",
    )
    db.session.add_all([agunda, kilimani])
    db.session.flush()

    db.session.add_all([
        Unit(property_id=agunda.id, unit_type="1_bedroom", price_per_month=12000, total_units=5, available_units=5, amenities="water,parking"),
        Unit(property_id=agunda.id, unit_type="2_bedroom", price_per_month=20000, bathrooms=2, total_units=3, available_units=3, amenities="water,parking,wifi"),
        Unit(property_id=kilimani.id, unit_type="2_bedroom", price_per_month=45000, bathrooms=2, total_units=4, available_units=4, amenities="wifi,gym,parking"),
        Unit(property_id=kilimani.id, unit_type="studio", price_per_month=25000, total_units=2, available_units=2, amenities="wifi,gym"),
    ])
    db.session.commit()
    click.echo("Demo manager (manager@rental.com / Manager@1234) and customer (customer@rental.com / Customer@1234) created.")
