from .conftest import login, make_listing, register


def test_unapproved_manager_cannot_create_property(client, admin_h):
    res = register(client, "New Manager", "new@test.com", "manager")
    assert res.get_json()["user"]["is_approved"] is False
    h = login(client, "new@test.com")
    city_id = client.get("/api/cities").get_json()[0]["id"]
    res = client.post("/api/properties", headers=h, json={"name": "Blocked", "city_id": city_id})
    assert res.status_code == 403


def test_property_hidden_until_approved(client, manager_h, admin_h):
    prop, _ = make_listing(client, manager_h, admin_h, approve=False)
    assert client.get("/api/properties").get_json()["total"] == 0
    assert client.get(f"/api/properties/{prop['id']}").status_code == 404
    assert client.get(f"/api/properties/{prop['id']}", headers=manager_h).status_code == 200

    client.patch(f"/api/admin/properties/{prop['id']}/status", headers=admin_h, json={"status": "approved"})
    assert client.get("/api/properties").get_json()["total"] == 1
    assert client.get(f"/api/properties/{prop['id']}").status_code == 200


def test_property_filters_by_city_and_price(client, manager_h, admin_h):
    make_listing(client, manager_h, admin_h, price="20000.00")
    cities = client.get("/api/cities").get_json()
    nairobi = [city for city in cities if city["name"] == "Nairobi"][0]
    naivasha = [city for city in cities if city["name"] == "Naivasha"][0]

    assert client.get(f"/api/properties?city_id={naivasha['id']}").get_json()["total"] == 1
    assert client.get(f"/api/properties?city_id={nairobi['id']}").get_json()["total"] == 0
    assert client.get("/api/properties?city=naiva").get_json()["total"] == 1
    assert client.get("/api/properties?max_price=10000").get_json()["total"] == 0
    assert client.get("/api/properties?min_price=15000&unit_type=2_bedroom").get_json()["total"] == 1


def test_manager_cannot_edit_others_property(client, manager_h, admin_h):
    prop, _ = make_listing(client, manager_h, admin_h)
    register(client, "Other", "other@test.com", "manager")
    users = client.get("/api/admin/users?role=manager", headers=admin_h).get_json()["items"]
    other_id = [user for user in users if user["email"] == "other@test.com"][0]["id"]
    client.patch(f"/api/admin/users/{other_id}", headers=admin_h, json={"is_approved": True})
    other_h = login(client, "other@test.com")
    assert client.patch(f"/api/properties/{prop['id']}", headers=other_h, json={"name": "Hacked"}).status_code == 403
    assert client.delete(f"/api/properties/{prop['id']}", headers=other_h).status_code == 403
