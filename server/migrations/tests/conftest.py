import os

import pytest

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app import app as flask_app
from config import TestConfig, db
from models import City, User


@pytest.fixture()
def app():
    flask_app.config.from_object(TestConfig)
    with flask_app.app_context():
        db.create_all()
        db.session.add_all([City(name="Naivasha"), City(name="Nairobi")])
        admin = User(name="Admin", email="admin@test.com", role="admin")
        admin.set_password("Admin@1234")
        db.session.add(admin)
        db.session.commit()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client(use_cookies=False)


def register(client, name, email, role):
    return client.post("/api/auth/register", json={
        "name": name, "email": email, "password": "Password1!", "role": role,
    })


def login(client, email, password="Password1!"):
    auth_client = client.application.test_client()
    res = auth_client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.get_json()
    cookie = res.headers.get("Set-Cookie")
    assert cookie is not None
    return {"Cookie": cookie.split(";", 1)[0]}


def make_listing(client, manager_h, admin_h, approve=True, price="20000.00", city="Naivasha"):
    city_id = [c for c in client.get("/api/cities").get_json() if c["name"] == city][0]["id"]
    prop = client.post("/api/properties", headers=manager_h, json={
        "name": "Agunda Apartments", "city_id": city_id, "area": "Section 8",
    }).get_json()
    unit = client.post(f"/api/properties/{prop['id']}/units", headers=manager_h, json={
        "unit_type": "2_bedroom", "price_per_month": price, "total_units": 2,
    }).get_json()
    if approve:
        client.patch(f"/api/admin/properties/{prop['id']}/status", headers=admin_h, json={"status": "approved"})
    return prop, unit


def book(client, customer_h, unit_id, start="2026-12-01", end="2027-03-01"):
    return client.post("/api/bookings", headers=customer_h, json={
        "unit_id": unit_id, "start_date": start, "end_date": end,
    })


@pytest.fixture()
def admin_h(client):
    return login(client, "admin@test.com", "Admin@1234")


@pytest.fixture()
def manager_h(client, admin_h):
    """An approved manager."""
    res = register(client, "Mary Manager", "mary@test.com", "manager")
    uid = res.get_json()["user"]["id"]
    client.patch(f"/api/admin/users/{uid}", json={"is_approved": True}, headers=admin_h)
    return login(client, "mary@test.com")


@pytest.fixture()
def customer_h(client):
    register(client, "Carl Customer", "carl@test.com", "customer")
    return login(client, "carl@test.com")
