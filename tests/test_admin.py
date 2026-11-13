def test_admin_block_user_and_stats(client, admin_h, manager_h, customer_h):
    users = client.get("/api/admin/users?role=customer", headers=admin_h).get_json()["items"]
    customer_id = users[0]["id"]
    client.patch(f"/api/admin/users/{customer_id}", headers=admin_h, json={"is_active": False})
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
