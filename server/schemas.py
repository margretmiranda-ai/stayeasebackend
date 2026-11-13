from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from models import BOOKING_STATUSES, PROPERTY_STATUSES, UNIT_TYPES


# ---------- Users / Auth ----------
class RegisterSchema(Schema):
    """Input for sign-up. Admins are NOT created through this route
    (use `seed.py` to create the first admin)."""
    name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    email = fields.Email(required=True)
    phone = fields.Str(validate=validate.Length(max=20))
    password = fields.Str(required=True, load_only=True, validate=validate.Length(min=8))
    role = fields.Str(required=True, validate=validate.OneOf(["manager", "customer"]))


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)


class UserSchema(Schema):
    """Output only. Never exposes the password hash."""
    id = fields.Int(dump_only=True)
    name = fields.Str()
    email = fields.Email()
    phone = fields.Str()
    role = fields.Str()
    is_approved = fields.Bool()
    is_active = fields.Bool()
    created_at = fields.DateTime(dump_only=True)


class AdminUserUpdateSchema(Schema):
    """Admin: approve a manager or block/unblock a user."""
    is_approved = fields.Bool()
    is_active = fields.Bool()


# ---------- Cities ----------
class CitySchema(Schema):
    """Admin creates/edits cities; everyone can read the list."""
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=2, max=100))


# ---------- Units ----------
class UnitSchema(Schema):
    id = fields.Int(dump_only=True)
    property_id = fields.Int(dump_only=True)
    unit_type = fields.Str(required=True, validate=validate.OneOf(UNIT_TYPES))
    price_per_month = fields.Decimal(
        required=True, as_string=True, places=2, validate=validate.Range(min=0)
    )
    bathrooms = fields.Int(validate=validate.Range(min=0))
    amenities = fields.Str(validate=validate.Length(max=500))
    image_url = fields.Url()
    total_units = fields.Int(validate=validate.Range(min=1))
    available_units = fields.Int(validate=validate.Range(min=0))
    created_at = fields.DateTime(dump_only=True)

    @validates_schema
    def check_availability(self, data, **kwargs):
        total = data.get("total_units")
        available = data.get("available_units")
        if total is not None and available is not None and available > total:
            raise ValidationError(
                "available_units cannot exceed total_units", "available_units"
            )


class UnitListSchema(UnitSchema):
    """Unit plus a short summary of its property (used when browsing prices)."""
    property = fields.Nested(
        "PropertySchema",
        only=("id", "name", "area", "city", "manager"),
        dump_only=True,
    )


# ---------- Properties ----------
class PropertySchema(Schema):
    """Used by managers to create/update, and by everyone to read."""
    id = fields.Int(dump_only=True)
    manager_id = fields.Int(dump_only=True)
    city_id = fields.Int(required=True, load_only=True)
    city = fields.Nested(CitySchema, dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=2, max=150))
    description = fields.Str()
    area = fields.Str(validate=validate.Length(max=100))
    address = fields.Str(validate=validate.Length(max=255))
    image_url = fields.Url()
    status = fields.Str(dump_only=True)  # only admin changes this
    created_at = fields.DateTime(dump_only=True)

    units = fields.List(fields.Nested(UnitSchema), dump_only=True)
    manager = fields.Nested(UserSchema, only=("id", "name", "phone"), dump_only=True)


class PropertyStatusSchema(Schema):
    """Admin: approve / reject a property."""
    status = fields.Str(required=True, validate=validate.OneOf(PROPERTY_STATUSES))


# ---------- Bookings ----------
class BookingSchema(Schema):
    id = fields.Int(dump_only=True)
    customer_id = fields.Int(dump_only=True)
    unit_id = fields.Int(required=True)
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    total_price = fields.Decimal(as_string=True, places=2, dump_only=True)
    status = fields.Str(dump_only=True)
    created_at = fields.DateTime(dump_only=True)

    unit = fields.Nested(UnitListSchema, dump_only=True)
    customer = fields.Nested(UserSchema, only=("id", "name", "phone"), dump_only=True)

    @validates_schema
    def check_dates(self, data, **kwargs):
        if data["end_date"] <= data["start_date"]:
            raise ValidationError("end_date must be after start_date", "end_date")


class BookingStatusSchema(Schema):
    """Manager confirms / cancels / completes, customer cancels."""
    status = fields.Str(required=True, validate=validate.OneOf(BOOKING_STATUSES))


# ---------- Query strings ----------
class PageSchema(Schema):
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(load_default=10, validate=validate.Range(min=1, max=50))


class BrowseQuerySchema(PageSchema):
    """Filters for GET /api/properties and GET /api/units."""
    city_id = fields.Int()
    city = fields.Str()  # alternative: search by city name
    area = fields.Str()
    unit_type = fields.Str(validate=validate.OneOf(UNIT_TYPES))
    min_price = fields.Decimal(validate=validate.Range(min=0))
    max_price = fields.Decimal(validate=validate.Range(min=0))
    sort = fields.Str(load_default="newest", validate=validate.OneOf(["newest", "price_asc", "price_desc"]))


class UserFilterSchema(PageSchema):
    role = fields.Str(validate=validate.OneOf(["manager", "customer", "admin"]))
    is_approved = fields.Bool()
    is_active = fields.Bool()


class StatusFilterSchema(PageSchema):
    status = fields.Str()
