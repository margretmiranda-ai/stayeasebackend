import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import current_app

logger = logging.getLogger(__name__)

RESEND_EMAIL_URL = "https://api.resend.com/emails"


def send_auth_email(user, event):
    if event == "registration":
        subject = "Welcome to StayEase"
        message = (
            f"Hi {user.name},\n\n"
            "Your StayEase account has been created successfully."
        )
    elif event == "login":
        subject = "New sign-in to your StayEase account"
        message = (
            f"Hi {user.name},\n\n"
            "A successful sign-in to your StayEase account just occurred. "
            "If this wasn't you, please secure your account."
        )
    else:
        raise ValueError(f"Unsupported authentication email event: {event}")

    api_key = current_app.config["RESEND_API_KEY"]
    from_email = current_app.config["RESEND_FROM_EMAIL"]
    if not api_key or not from_email:
        logger.warning(
            "Resend is not configured; %s email was not sent to %s",
            event,
            user.email,
        )
        return

    payload = {
        "from": from_email,
        "to": [user.email],
        "subject": subject,
        "text": message,
    }
    request = Request(
        RESEND_EMAIL_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            if response.status != 200:
                logger.error(
                    "Resend rejected %s email to %s with status %s",
                    event,
                    user.email,
                    response.status,
                )
    except (HTTPError, URLError, TimeoutError) as exc:
        logger.error(
            "Failed to send %s email to %s through Resend: %s",
            event,
            user.email,
            exc,
        )
