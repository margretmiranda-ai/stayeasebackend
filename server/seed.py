from datetime import date, timedelta
from decimal import Decimal

from flask import current_app

from app import app
from config import db
from models import Booking, City, Property, Unit, User


def seed_database():
    db.create_all()

    for model in (Booking, Unit, Property, User, City):
        db.session.execute(db.delete(model))

    cities = {
        name: City(name=name)
        for name in ("Nairobi", "Naivasha", "Mombasa", "Kisumu")
    }
    users = {
        "admin": User(
            name=current_app.config["ADMIN_NAME"],
            email=current_app.config["ADMIN_EMAIL"].lower(),
            role="admin",
            is_approved=True,
        ),
        "manager": User(
            name="Mary Manager",
            email="manager@rental.com",
            phone="0700000001",
            role="manager",
            is_approved=True,
        ),
        "pending_manager": User(
            name="Pat Pending",
            email="pending@rental.com",
            phone="0700000003",
            role="manager",
            is_approved=False,
        ),
        "customer": User(
            name="Carl Customer",
            email="customer@rental.com",
            phone="0700000002",
            role="customer",
            is_approved=True,
        ),
        "customer_two": User(
            name="Dana Customer",
            email="customer2@rental.com",
            phone="0700000004",
            role="customer",
            is_approved=True,
        ),
    }

    users["admin"].set_password(current_app.config["ADMIN_PASSWORD"])
    users["manager"].set_password("Manager@1234")
    users["pending_manager"].set_password("Pending@1234")
    users["customer"].set_password("Customer@1234")
    users["customer_two"].set_password("Customer2@1234")
    db.session.add_all([*cities.values(), *users.values()])
    db.session.flush()

    properties = {
        "agunda": Property(
            manager=users["manager"],
            city=cities["Naivasha"],
            name="Agunda Apartments",
            area="Section 8",
            description="Quiet apartments close to the lake.",
            status="approved",
        ),
        "kilimani": Property(
            manager=users["manager"],
            city=cities["Nairobi"],
            name="Kilimani Heights",
            area="Kilimani",
            description="Modern apartments with parking and a gym.",
            status="approved",
        ),
        "coast": Property(
            manager=users["manager"],
            city=cities["Mombasa"],
            name="Coast View",
            area="Nyali",
            description="A listing waiting for admin review.",
            status="pending",
        ),
        "lake": Property(
            manager=users["manager"],
            city=cities["Kisumu"],
            name="Lakeview Residences",
            area="Milimani",
            description="A rejected listing for admin testing.",
            status="rejected",
        ),
    }
    db.session.add_all(properties.values())
    db.session.flush()

    units = {
        "agunda_two_bedroom": Unit(
            property=properties["agunda"],
            unit_type="2_bedroom",
            price_per_month=Decimal("20000.00"),
            bathrooms=2,
            amenities="water,parking,wifi",
            total_units=3,
            available_units=2,
        ),
        "agunda_one_bedroom": Unit(
            property=properties["agunda"],
            unit_type="1_bedroom",
            price_per_month=Decimal("12000.00"),
            amenities="water,parking",
            total_units=5,
            available_units=5,
        ),
        "kilimani_studio": Unit(
            property=properties["kilimani"],
            unit_type="studio",
            price_per_month=Decimal("25000.00"),
            amenities="wifi,gym",
            total_units=2,
            available_units=2,
        ),
        "coast_studio": Unit(
            property=properties["coast"],
            unit_type="studio",
            price_per_month=Decimal("18000.00"),
            amenities="water,parking",
            total_units=4,
            available_units=4,
        ),
        "lake_two_bedroom": Unit(
            property=properties["lake"],
            unit_type="2_bedroom",
            price_per_month=Decimal("22000.00"),
            bathrooms=2,
            amenities="water,parking",
            total_units=2,
            available_units=2,
        ),
    }
    db.session.add_all(units.values())
    db.session.flush()

    today = date.today()
    bookings = [
        Booking(
            customer=users["customer"],
            unit=units["agunda_two_bedroom"],
            start_date=today + timedelta(days=14),
            end_date=today + timedelta(days=74),
            total_price=Decimal("40000.00"),
            status="pending",
        ),
        Booking(
            customer=users["customer"],
            unit=units["agunda_two_bedroom"],
            start_date=today + timedelta(days=90),
            end_date=today + timedelta(days=150),
            total_price=Decimal("40000.00"),
            status="confirmed",
        ),
        Booking(
            customer=users["customer_two"],
            unit=units["kilimani_studio"],
            start_date=today + timedelta(days=30),
            end_date=today + timedelta(days=60),
            total_price=Decimal("25000.00"),
            status="cancelled",
        ),
        Booking(
            customer=users["customer_two"],
            unit=units["agunda_one_bedroom"],
            start_date=today - timedelta(days=60),
            end_date=today - timedelta(days=30),
            total_price=Decimal("12000.00"),
            status="completed",
        ),
    ]
    db.session.add_all(bookings)
    db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        seed_database()
    print("Database reset and demo data seeded.")
