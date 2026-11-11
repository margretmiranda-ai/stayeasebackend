import pytest

from app import create_app
from app.extensions import db
from app.models import City, User
from config import TestConfig


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        db.session.add_all([City(name="Naivasha"), City(name="Nairobi")])
        admin = User(name="Admin", email="admin@test.com", role="admin")
        admin.set_password("Admin@1234")
        db.session.add(admin)
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def register(client, name, email, role):
    return client.post("/api/auth/register", json={
        "name": name, "email": email, "password": "Password1!", "role": role,
    })


def login(client, email, password="Password1!"):
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.get_json()
    return {"Authorization": f"Bearer {res.get_json()['access_token']}"}


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
