# Property Rental Backend

Flask + SQLAlchemy REST API for a property renting app with three roles:

- **Manager** registers properties and the unit types inside them (1-bedroom, 2-bedroom...) with prices, and confirms bookings.
- **Customer** browses and compares prices across managers, filters by city, and books units.
- **Admin** approves managers and properties, manages cities, blocks users and sees stats.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python seed.py                     # resets all app data and loads demo data
python app.py                      # http://localhost:5555
pytest                             # run the tests
```

To enable registration and login emails, copy `.env.example` to `.env`, then set
`RESEND_API_KEY` and `RESEND_FROM_EMAIL` to your Resend API key and an allowed
sender address. Emails are sent by the backend; the API key must not be added
to a frontend application. If either setting is missing or Resend cannot
accept a message, the event is recorded in the backend logs and account
registration/login still succeeds. Resend may require a verified domain or
sender before allowing delivery to your intended recipients.

**Warning:** `python seed.py` deletes existing application data before inserting the demo data. It creates tables if needed. The admin credentials come from `.env` (defaults: `admin@rental.com` / `Admin@1234`). Demo accounts: `manager@rental.com` / `Manager@1234`, `pending@rental.com` / `Pending@1234`, `customer@rental.com` / `Customer@1234`, and `customer2@rental.com` / `Customer2@1234`.

Apply the existing database migrations with `flask --app app db upgrade`.

## Postman

Start the server with `python app.py`, then send requests to `http://127.0.0.1:5555`. Log in at `POST /api/auth/login` before calling protected endpoints; Postman will reuse the session cookie for requests to the same host.

## Project layout

```
app.py               Flask app, route imports, and error handlers
config.py            app settings and database extension
models.py            User, City, Property, Unit, Booking
schemas.py           Marshmallow validation and serialization
helpers.py           auth decorator, pagination, error helpers
routes/              direct app routes: auth, cities, properties, units, bookings, admin
tests/               pytest suite
migrations/          database schema migrations
seed.py              resets and reloads demo data
```

## Authentication

Log in at `POST /api/auth/login` to establish a Flask session. The server sends a signed session cookie; send that cookie with protected requests. In Postman, use the same host for login and later requests so its cookie jar can reuse the cookie. Browser clients calling this API from another origin must use `credentials: "include"` with `fetch`.
Successful login and `GET /api/auth/me` return only the user's `id`, `name`, and `role`.

`POST /api/auth/logout` clears the current session cookie. Flask's default session is stored in a signed cookie, not in the database, so keep only non-sensitive session data in it. For HTTPS deployments, set `SESSION_COOKIE_SECURE=true`; the default `SESSION_COOKIE_SAMESITE=Lax` can be changed when the frontend is hosted on a different site.

Managers register with `is_approved = false` and cannot create properties until an admin approves them.
Admins cannot be created through the API. The admin demo account is created by `seed.py`.

## Endpoints

Lists are paginated: `?page=1&per_page=10` returns `{items, page, per_page, total, pages}`.

| Method | Path | Who | What |
|---|---|---|---|
| POST | `/api/auth/register` | public | Sign up as `manager` or `customer` |
| POST | `/api/auth/login` | public | Start a session |
| POST | `/api/auth/logout` | any user | Clear the current session |
| GET | `/api/auth/me` | any user | Current user |
| GET | `/api/cities` | public | List cities (for dropdowns) |
| POST / PUT / DELETE | `/api/cities`, `/api/cities/<id>` | admin | Manage cities |
| GET | `/api/properties` | public | Approved properties. Filters: `city_id`, `city`, `area`, `unit_type`, `min_price`, `max_price` |
| GET | `/api/properties/<id>` | public | One property with its units (unapproved: owner/admin only) |
| GET | `/api/properties/mine` | manager | My properties, any status |
| POST | `/api/properties` | approved manager | Register a property (`city_id` required) |
| PATCH | `/api/properties/<id>` | owner | Edit |
| DELETE | `/api/properties/<id>` | owner or admin | Delete |
| GET | `/api/units` | public | Compare prices across managers. Same filters plus `sort=price_asc`, `price_desc` or `newest` |
| GET | `/api/units/<id>` | public | One unit |
| POST | `/api/properties/<id>/units` | owner | Add a unit type with price |
| PUT / DELETE | `/api/units/<id>` | owner (delete: or admin) | Edit / remove a unit |
| POST | `/api/bookings` | customer | Book a unit (`unit_id`, `start_date`, `end_date`) |
| GET | `/api/bookings/mine` | customer | My bookings |
| GET | `/api/bookings` | manager / admin | Bookings for my properties / all bookings (`?status=`) |
| GET | `/api/bookings/<id>` | owner customer, property manager, admin | One booking |
| PATCH | `/api/bookings/<id>/status` | see below | Change booking status |
| GET | `/api/admin/users` | admin | Filter by `role`, `is_approved`, `is_active` |
| PATCH | `/api/admin/users/<id>` | admin | Approve a manager / block or unblock a user |
| GET | `/api/admin/properties` | admin | All properties, `?status=pending` to review |
| PATCH | `/api/admin/properties/<id>/status` | admin | `approved` / `rejected` / `pending` |
| GET | `/api/admin/stats` | admin | Counts and revenue |

## Business rules

- A property is visible to customers only when its status is `approved`.
- Booking price = monthly price x number of months (30 days each, part of a month counts as a month).
- Booking status flow: `pending` -> `confirmed` -> `completed`, and `pending` or `confirmed` -> `cancelled`.
- Customers can only cancel their own bookings. Managers can confirm, cancel or complete bookings for their own properties.
- Confirming a booking reduces the unit's `available_units` by one. Cancelling or completing a confirmed booking gives it back.
