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
cp .env.example .env               # then edit the secrets

flask --app run seed --demo        # creates tables, cities, the admin, and demo data
python run.py                      # http://localhost:5000
pytest                             # run the tests
```

Default admin (change it in `.env`): `admin@rental.com` / `Admin@1234`
Demo accounts (only with `--demo`): `manager@rental.com` / `Manager@1234`, `customer@rental.com` / `Customer@1234`

Using migrations instead of `create_all`: `flask --app run db init`, `db migrate`, `db upgrade`.

## Project layout

```
app/
  __init__.py        app factory, error handlers, `flask seed` command
  extensions.py      db, jwt, migrate, cors
  models.py          User, City, Property, Unit, Booking
  schemas.py         Marshmallow schemas (validation + serialization)
  utils.py           roles_required decorator, pagination, error helper
  routes/            auth, cities, properties, units, bookings, admin
tests/               pytest suite (18 tests)
config.py            settings from environment
run.py               entry point
```

## Authentication

Log in to get a token, then send it on protected routes: `Authorization: Bearer <token>`.
Managers register with `is_approved = false` and cannot create properties until an admin approves them.
Admins cannot be created through the API. They come from `flask seed`.

## Endpoints

Lists are paginated: `?page=1&per_page=10` returns `{items, page, per_page, total, pages}`.

| Method | Path | Who | What |
|---|---|---|---|
| POST | `/api/auth/register` | public | Sign up as `manager` or `customer` |
| POST | `/api/auth/login` | public | Get an access token |
| GET | `/api/auth/me` | any user | Current user |
| GET | `/api/cities` | public | List cities (for dropdowns) |
| POST / PUT / DELETE | `/api/cities`, `/api/cities/<id>` | admin | Manage cities |
| GET | `/api/properties` | public | Approved properties. Filters: `city_id`, `city`, `area`, `unit_type`, `min_price`, `max_price` |
| GET | `/api/properties/<id>` | public | One property with its units (unapproved: owner/admin only) |
| GET | `/api/properties/mine` | manager | My properties, any status |
| POST | `/api/properties` | approved manager | Register a property (`city_id` required) |
| PUT | `/api/properties/<id>` | owner | Edit |
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

## Example requests

```bash
# manager registers a property (city_id comes from GET /api/cities)
curl -X POST localhost:5000/api/properties -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Agunda Apartments", "city_id": 4, "area": "Section 8"}'

# add a 2-bedroom at KES 20,000 per month, 3 available
curl -X POST localhost:5000/api/properties/1/units -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"unit_type": "2_bedroom", "price_per_month": "20000", "total_units": 3}'

# customer compares cheapest units in Naivasha
curl "localhost:5000/api/units?city=Naivasha&sort=price_asc"
```
