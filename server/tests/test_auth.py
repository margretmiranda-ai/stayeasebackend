from .conftest import login, register


def test_register_login_me(client):
    res = register(client, "Carl", "carl@test.com", "customer")
    assert res.status_code == 201
    assert "password" not in res.get_json()["user"]
    assert register(client, "Carl", "carl@test.com", "customer").status_code == 409
    h = login(client, "carl@test.com")
    user = client.get("/api/auth/me", headers=h).get_json()
    assert set(user) == {"id", "name", "role"}
    assert user["name"] == "Carl"
    assert user["role"] == "customer"


def test_registration_sends_welcome_email(client, monkeypatch):
    sent = []
    monkeypatch.setattr(
        "server.routes.auth.send_auth_email",
        lambda user, event: sent.append((user.email, event)),
    )

    response = register(client, "Carl", "carl@test.com", "customer")

    assert response.status_code == 201
    assert sent == [("carl@test.com", "registration")]


def test_successful_login_sends_notification(client, monkeypatch):
    register(client, "Carl", "carl@test.com", "customer")
    sent = []
    monkeypatch.setattr(
        "server.routes.auth.send_auth_email",
        lambda user, event: sent.append((user.email, event)),
    )

    response = client.post(
        "/api/auth/login",
        json={"email": "carl@test.com", "password": "Password1!"},
    )

    assert response.status_code == 200
    assert sent == [("carl@test.com", "login")]


def test_cannot_register_as_admin(client):
    assert register(client, "Evil", "evil@test.com", "admin").status_code == 400


def test_bad_login(client):
    assert client.post("/api/auth/login", json={"email": "x@test.com", "password": "nope12345"}).status_code == 401


def test_login_returns_minimal_user(client):
    register(client, "Carl", "carl@test.com", "customer")
    response = client.post(
        "/api/auth/login",
        json={"email": "carl@test.com", "password": "Password1!"},
    )

    assert response.status_code == 200
    user = response.get_json()["user"]
    assert set(user) == {"id", "name", "role"}
    assert user["id"] > 0
    assert user["name"] == "Carl"
    assert user["role"] == "customer"


def test_protected_route_needs_session(client):
    assert client.get("/api/auth/me").status_code == 401


def test_logout_clears_session(client):
    register(client, "Carl", "carl@test.com", "customer")
    response = client.post(
        "/api/auth/login",
        json={"email": "carl@test.com", "password": "Password1!"},
    )

    assert response.status_code == 200
    assert "access_token" not in response.get_json()
    cookie = response.headers["Set-Cookie"].split(";", 1)[0]
    assert client.get("/api/auth/me", headers={"Cookie": cookie}).status_code == 200

    response = client.post("/api/auth/logout", headers={"Cookie": cookie})

    assert response.status_code == 200
    assert response.headers["Set-Cookie"].startswith("session=;")
    assert client.get("/api/auth/me").status_code == 401
