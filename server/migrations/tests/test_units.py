from .conftest import make_listing


def test_unit_filters_by_city_and_price(client, manager_h, admin_h):
    make_listing(client, manager_h, admin_h, price="20000.00")

    units = client.get("/api/units?city=Naivasha&sort=price_asc").get_json()
    assert units["total"] == 1
    assert units["items"][0]["property"]["city"]["name"] == "Naivasha"
    assert client.get("/api/units?unit_type=banana").status_code == 400


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
