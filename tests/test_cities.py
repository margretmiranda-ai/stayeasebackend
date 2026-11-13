from .conftest import make_listing


def test_only_admin_manages_cities(client, admin_h, manager_h):
    assert client.post("/api/cities", headers=manager_h, json={"name": "Kisumu"}).status_code == 403
    assert client.post("/api/cities", headers=admin_h, json={"name": "kisumu"}).status_code == 201
    assert client.post("/api/cities", headers=admin_h, json={"name": "Kisumu"}).status_code == 409


def test_cannot_delete_city_with_properties(client, admin_h, manager_h):
    prop, _ = make_listing(client, manager_h, admin_h)
    city_id = client.get(f"/api/properties/{prop['id']}").get_json()["city"]["id"]
    assert client.delete(f"/api/cities/{city_id}", headers=admin_h).status_code == 409
