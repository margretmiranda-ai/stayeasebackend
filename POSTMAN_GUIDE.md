# Postman API Testing Guide

## Setup

Set a Postman environment variable:

| Variable | Local value |
|---|---|
| `base_url` | `http://127.0.0.1:5555` |

Use `{{base_url}}` at the start of each URL below. For requests with JSON bodies, select **Body → raw → JSON**. Postman should set `Content-Type: application/json`.

Log in with `POST /api/auth/login` before using a protected endpoint. Postman stores the session cookie; keep using the same host and port so it sends the cookie with later requests. Log in separately as a customer, manager, or admin to test each role.

The demo accounts created by `python seed.py` are documented in the project [README](./README.md). Managers must be approved by an admin before they can create or edit properties and units.

## Basic checks

| Method and path | Access | Body |
|---|---|---|
| `GET /` | Public | No body. |
| `GET /api/health` | Public | No body. |

## Authentication

| Method and path | Access | Body |
|---|---|---|
| `POST /api/auth/register` | Public | Required: `name`, `email`, `password`, `role`. Optional: `phone`. `role` is `manager` or `customer`. Password must be at least 8 characters. |
| `POST /api/auth/login` | Public | Required: `email`, `password`. |
| `POST /api/auth/logout` | Logged-in user | No body. Clears the session cookie. |
| `GET /api/auth/me` | Logged-in user | No body. |

Registration example:

```json
{
  "name": "Mary Manager",
  "email": "mary@example.com",
  "password": "Password1!",
  "role": "manager",
  "phone": "0700000001"
}
```

Login example:

```json
{
  "email": "mary@example.com",
  "password": "Password1!"
}
```

Both login and `/api/auth/me` return only the user's `id`, `name`, and `role`.

## Cities

| Method and path | Access | Body |
|---|---|---|
| `GET /api/cities` | Public | No body. |
| `POST /api/cities` | Admin | Required: `name` (2–100 characters). |
| `PUT /api/cities/{city_id}` | Admin | Required: `name` (2–100 characters). |
| `DELETE /api/cities/{city_id}` | Admin | No body. A city with properties cannot be deleted. |

Example:

```json
{
  "name": "Nairobi"
}
```

## Properties

| Method and path | Access | Body or query parameters |
|---|---|---|
| `GET /api/properties` | Public | Optional query filters: `city_id`, `city`, `area`, `unit_type`, `min_price`, `max_price`, `page`, `per_page`. |
| `GET /api/properties/{property_id}` | Public for approved properties; owner or admin for unapproved properties | No body. |
| `GET /api/properties/mine` | Manager | Optional query parameters: `page`, `per_page`. |
| `POST /api/properties` | Approved manager | Required: `city_id`, `name`. Optional: `description`, `area`, `address`, `image_url`. |
| `PATCH /api/properties/{property_id}` | Approved owner-manager | Any editable property fields may be sent; all are optional for this partial update. |
| `DELETE /api/properties/{property_id}` | Owner-manager or admin | No body. |

Create example:

```json
{
  "city_id": 1,
  "name": "Kimpartments",
  "description": "Apartments near the city centre",
  "area": "Westlands",
  "address": "Example Street",
  "image_url": "https://example.com/property.jpg"
}
```

`manager_id` is assigned from the logged-in manager's session. Do not send `manager_id`, `status`, `id`, or `created_at`; those are server-controlled/output fields. Get a valid `city_id` from `GET /api/cities`.

## Units

| Method and path | Access | Body or query parameters |
|---|---|---|
| `GET /api/units` | Public | Optional query filters: `city_id`, `city`, `area`, `unit_type`, `min_price`, `max_price`, `sort`, `page`, `per_page`. |
| `GET /api/units/{unit_id}` | Public for units in approved properties | No body. |
| `POST /api/properties/{property_id}/units` | Approved manager who owns the property | Required: `unit_type`, `price_per_month`. Optional: `bathrooms`, `amenities`, `image_url`, `total_units`, `available_units`. |
| `PUT /api/units/{unit_id}` | Approved owner-manager | Any editable unit fields may be sent; all are optional for this update. |
| `DELETE /api/units/{unit_id}` | Owner-manager or admin | No body. |

Create example:

```json
{
  "unit_type": "2_bedroom",
  "price_per_month": "20000",
  "total_units": 3,
  "available_units": 3,
  "bathrooms": 1,
  "amenities": "Parking, water",
  "image_url": "https://example.com/unit.jpg"
}
```

Allowed `unit_type` values: `bedsitter`, `studio`, `1_bedroom`, `2_bedroom`, `3_bedroom`, `4_bedroom`. If omitted, `total_units` defaults to `1`, and `available_units` defaults to `total_units`. Availability cannot exceed the total number of units. Do not send `id`, `property_id`, or `created_at`; the path and server determine those values.

For `GET /api/units`, `sort` may be `newest`, `price_asc`, or `price_desc`; it defaults to `newest`.

## Bookings

| Method and path | Access | Body or query parameters |
|---|---|---|
| `POST /api/bookings` | Customer | Required: `unit_id`, `start_date`, `end_date`. Dates use `YYYY-MM-DD`; `end_date` must be after `start_date`. |
| `GET /api/bookings/mine` | Customer | Optional query parameters: `status`, `page`, `per_page`. |
| `GET /api/bookings` | Manager or admin | Optional query parameters: `status`, `page`, `per_page`. Managers only see bookings for their own properties. |
| `GET /api/bookings/{booking_id}` | Booking's customer, property's manager, or admin | No body. |
| `PATCH /api/bookings/{booking_id}/status` | Authorized booking customer, property's manager, or admin | Required: `status`. |

Create example:

```json
{
  "unit_id": 1,
  "start_date": "2026-12-01",
  "end_date": "2027-01-01"
}
```

Allowed booking statuses are `pending`, `confirmed`, `cancelled`, and `completed`, but transitions are restricted:

- `pending` → `confirmed` or `cancelled`
- `confirmed` → `cancelled` or `completed`
- Customers can only change their own bookings to `cancelled`.

Booking status example:

```json
{
  "status": "confirmed"
}
```

The customer ID, initial status, and total price are assigned by the server. Do not include them in the booking request.

## Admin

| Method and path | Access | Body or query parameters |
|---|---|---|
| `GET /api/admin/users` | Admin | Optional query filters: `role`, `is_approved`, `is_active`, `page`, `per_page`. |
| `PATCH /api/admin/users/{user_id}` | Admin | Send `is_approved` and/or `is_active` as booleans. |
| `GET /api/admin/properties` | Admin | Optional query filters: `status`, `page`, `per_page`. |
| `PATCH /api/admin/properties/{property_id}/status` | Admin | Required: `status` (`pending`, `approved`, or `rejected`). |
| `GET /api/admin/stats` | Admin | No body. |

Approve a manager:

```json
{
  "is_approved": true
}
```

Block a user:

```json
{
  "is_active": false
}
```

Set a property's status:

```json
{
  "status": "approved"
}
```

## Pagination and common notes

- Paginated endpoints accept `page` (defaults to `1`) and `per_page` (defaults to `10`, maximum `50`).
- Query parameters go in Postman's **Params** tab, not in the JSON body.
- Use IDs returned by the API, such as a `city_id` from `GET /api/cities` or a `unit_id` from `GET /api/units`.
- Do not send fields marked output-only in request bodies, such as IDs, timestamps, ownership IDs, or calculated prices. The API sets those from the session, URL, or server logic. Status fields are accepted only on the documented status-update endpoints.
