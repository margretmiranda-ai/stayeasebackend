from .conftest import login, register


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


# ---------- auth ----------
def test_register_login_me(client):
    res = register(client, "Carl", "carl@test.com", "customer")
    assert res.status_code == 201
    assert "password" not in res.get_json()["user"]
    assert register(client, "Carl", "carl@test.com", "customer").status_code == 409
    h = login(client, "carl@test.com")
    assert client.get("/api/auth/me", headers=h).get_json()["role"] == "customer"


def test_cannot_register_as_admin(client):
    assert register(client, "Evil", "evil@test.com", "admin").status_code == 400


def test_bad_login(client):
    assert client.post("/api/auth/login", json={"email": "x@test.com", "password": "nope12345"}).status_code == 401


def test_protected_route_needs_token(client):
    assert client.get("/api/auth/me").status_code == 401


# ---------- manager approval ----------
def test_unapproved_manager_cannot_create_property(client, admin_h):
    res = register(client, "New Manager", "new@test.com", "manager")
    assert res.get_json()["user"]["is_approved"] is False
    h = login(client, "new@test.com")
    city_id = client.get("/api/cities").get_json()[0]["id"]
    res = client.post("/api/properties", headers=h, json={"name": "Blocked", "city_id": city_id})
    assert res.status_code == 403


# ---------- cities ----------
def test_only_admin_manages_cities(client, admin_h, manager_h):
    assert client.post("/api/cities", headers=manager_h, json={"name": "Kisumu"}).status_code == 403
    assert client.post("/api/cities", headers=admin_h, json={"name": "kisumu"}).status_code == 201
    assert client.post("/api/cities", headers=admin_h, json={"name": "Kisumu"}).status_code == 409


def test_cannot_delete_city_with_properties(client, admin_h, manager_h):
    prop, _ = make_listing(client, manager_h, admin_h)
    city_id = client.get(f"/api/properties/{prop['id']}").get_json()["city"]["id"]
    assert client.delete(f"/api/cities/{city_id}", headers=admin_h).status_code == 409


# ---------- properties & browsing ----------
def test_property_hidden_until_approved(client, manager_h, admin_h, customer_h):
    prop, _ = make_listing(client, manager_h, admin_h, approve=False)
    assert client.get("/api/properties").get_json()["total"] == 0
    assert client.get(f"/api/properties/{prop['id']}").status_code == 404
    assert client.get(f"/api/properties/{prop['id']}", headers=manager_h).status_code == 200

    client.patch(f"/api/admin/properties/{prop['id']}/status", headers=admin_h, json={"status": "approved"})
    assert client.get("/api/properties").get_json()["total"] == 1
    assert client.get(f"/api/properties/{prop['id']}").status_code == 200


def test_browse_by_city_and_price(client, manager_h, admin_h):
    make_listing(client, manager_h, admin_h, price="20000.00")
    nairobi = [c for c in client.get("/api/cities").get_json() if c["name"] == "Nairobi"][0]
    naivasha = [c for c in client.get("/api/cities").get_json() if c["name"] == "Naivasha"][0]

    assert client.get(f"/api/properties?city_id={naivasha['id']}").get_json()["total"] == 1
    assert client.get(f"/api/properties?city_id={nairobi['id']}").get_json()["total"] == 0
    assert client.get("/api/properties?city=naiva").get_json()["total"] == 1
    assert client.get("/api/properties?max_price=10000").get_json()["total"] == 0
    assert client.get("/api/properties?min_price=15000&unit_type=2_bedroom").get_json()["total"] == 1

    units = client.get("/api/units?city=Naivasha&sort=price_asc").get_json()
    assert units["total"] == 1
    assert units["items"][0]["property"]["city"]["name"] == "Naivasha"
    assert client.get("/api/units?unit_type=banana").status_code == 400


def test_manager_cannot_edit_others_property(client, manager_h, admin_h):
    prop, _ = make_listing(client, manager_h, admin_h)
    register(client, "Other", "other@test.com", "manager")
    uid = client.get("/api/admin/users?role=manager", headers=admin_h).get_json()["items"]
    other_id = [u for u in uid if u["email"] == "other@test.com"][0]["id"]
    client.patch(f"/api/admin/users/{other_id}", headers=admin_h, json={"is_approved": True})
    other_h = login(client, "other@test.com")
    assert client.put(f"/api/properties/{prop['id']}", headers=other_h, json={"name": "Hacked"}).status_code == 403
    assert client.delete(f"/api/properties/{prop['id']}", headers=other_h).status_code == 403


def test_unit_validation(client, manager_h, admin_h):
    prop, _ = make_listing(client, manager_h, admin_h)
    res = client.post(f"/api/properties/{prop['id']}/units", headers=manager_h, json={
        "unit_type": "2_bedroom", "price_per_month": "100", "total_units": 1, "available_units": 5,
    })
    assert res.status_code == 400
    res = client.post(f"/api/properties/{prop['id']}/units", headers=manager_h, json={
        "unit_type": "castle", "price_per_month": "100",
    })
    assert res.status_code == 400


# ---------- bookings ----------
def book(client, customer_h, unit_id, start="2026-12-01", end="2027-03-01"):
    return client.post("/api/bookings", headers=customer_h, json={
        "unit_id": unit_id, "start_date": start, "end_date": end,
    })


def test_booking_flow_and_availability(client, manager_h, admin_h, customer_h):
    _, unit = make_listing(client, manager_h, admin_h, price="20000.00")

    res = book(client, customer_h, unit["id"])
    assert res.status_code == 201
    booking = res.get_json()
    assert booking["status"] == "pending"
    assert booking["total_price"] == "60000.00"  # 90 days -> 3 months

    # manager sees it, confirms it, availability drops
    assert client.get("/api/bookings", headers=manager_h).get_json()["total"] == 1
    res = client.patch(f"/api/bookings/{booking['id']}/status", headers=manager_h, json={"status": "confirmed"})
    assert res.status_code == 200
    assert client.get(f"/api/units/{unit['id']}").get_json()["available_units"] == 1

    # customer cancels -> unit becomes available again
    res = client.patch(f"/api/bookings/{booking['id']}/status", headers=customer_h, json={"status": "cancelled"})
    assert res.status_code == 200
    assert client.get(f"/api/units/{unit['id']}").get_json()["available_units"] == 2

    # cancelled bookings cannot be re-confirmed
    res = client.patch(f"/api/bookings/{booking['id']}/status", headers=manager_h, json={"status": "confirmed"})
    assert res.status_code == 409


def test_booking_rules(client, manager_h, admin_h, customer_h):
    prop, unit = make_listing(client, manager_h, admin_h)
    assert book(client, customer_h, unit["id"], start="2026-12-10", end="2026-12-01").status_code == 400
    assert book(client, manager_h, unit["id"]).status_code == 403  # only customers book

    booking = book(client, customer_h, unit["id"]).get_json()
    res = client.patch(f"/api/bookings/{booking['id']}/status", headers=customer_h, json={"status": "confirmed"})
    assert res.status_code == 403  # customers can only cancel

    register(client, "Dan", "dan@test.com", "customer")
    dan_h = login(client, "dan@test.com")
    assert client.get(f"/api/bookings/{booking['id']}", headers=dan_h).status_code == 404
    assert client.get("/api/bookings/mine", headers=dan_h).get_json()["total"] == 0


def test_cannot_book_unapproved_property(client, manager_h, admin_h, customer_h):
    _, unit = make_listing(client, manager_h, admin_h, approve=False)
    assert book(client, customer_h, unit["id"]).status_code == 404


def test_cannot_confirm_when_sold_out(client, manager_h, admin_h, customer_h):
    _, unit = make_listing(client, manager_h, admin_h)  # total_units = 2
    ids = [book(client, customer_h, unit["id"]).get_json()["id"] for _ in range(3)]
    codes = [
        client.patch(f"/api/bookings/{i}/status", headers=manager_h, json={"status": "confirmed"}).status_code
        for i in ids
    ]
    assert codes == [200, 200, 409]
    assert book(client, customer_h, unit["id"]).status_code == 409


# ---------- admin ----------
def test_admin_block_user_and_stats(client, admin_h, manager_h, customer_h):
    users = client.get("/api/admin/users?role=customer", headers=admin_h).get_json()["items"]
    cid = users[0]["id"]
    client.patch(f"/api/admin/users/{cid}", headers=admin_h, json={"is_active": False})
    assert client.get("/api/auth/me", headers=customer_h).status_code == 403
    assert client.post("/api/auth/login", json={"email": "carl@test.com", "password": "Password1!"}).status_code == 403

    stats = client.get("/api/admin/stats", headers=admin_h).get_json()
    assert stats["users"]["customers"] == 1 and stats["revenue"] == "0.00"


def test_admin_cannot_block_self(client, admin_h):
    me = client.get("/api/auth/me", headers=admin_h).get_json()
    assert client.patch(f"/api/admin/users/{me['id']}", headers=admin_h, json={"is_active": False}).status_code == 400


def test_non_admin_cannot_use_admin_routes(client, manager_h, customer_h):
    assert client.get("/api/admin/users", headers=manager_h).status_code == 403
    assert client.get("/api/admin/stats", headers=customer_h).status_code == 403
