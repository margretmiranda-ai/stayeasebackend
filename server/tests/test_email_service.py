import json
from types import SimpleNamespace

from server.email_service import RESEND_EMAIL_URL, send_auth_email


def test_sends_registration_email_through_resend(app, monkeypatch):
    app.config["RESEND_API_KEY"] = "test-api-key"
    app.config["RESEND_FROM_EMAIL"] = "StayEase <onboarding@resend.dev>"
    captured = {}

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr("server.email_service.urlopen", fake_urlopen)
    user = SimpleNamespace(name="Carl", email="carl@test.com")

    with app.app_context():
        send_auth_email(user, "registration")

    request = captured["request"]
    payload = json.loads(request.data)
    assert request.full_url == RESEND_EMAIL_URL
    assert request.get_header("Authorization") == "Bearer test-api-key"
    assert captured["timeout"] == 10
    assert payload["from"] == "StayEase <onboarding@resend.dev>"
    assert payload["to"] == ["carl@test.com"]
    assert payload["subject"] == "Welcome to StayEase"
    assert "account has been created successfully" in payload["text"]
