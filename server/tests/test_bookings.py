from .conftest import book, login, make_listing, register


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
    _, unit = make_listing(client, manager_h, admin_h)
    assert book(client, customer_h, unit["id"], start="2026-12-10", end="2026-12-01").status_code == 400
    assert book(client, manager_h, unit["id"]).status_code == 403

    booking = book(client, customer_h, unit["id"]).get_json()
    res = client.patch(f"/api/bookings/{booking['id']}/status", headers=customer_h, json={"status": "confirmed"})
    assert res.status_code == 403

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
        client.patch(f"/api/bookings/{booking_id}/status", headers=manager_h, json={"status": "confirmed"}).status_code
        for booking_id in ids
    ]
    assert codes == [200, 200, 409]
    assert book(client, customer_h, unit["id"]).status_code == 409
