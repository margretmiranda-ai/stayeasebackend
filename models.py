from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from config import db

# Allowed values (validated in the schemas)
ROLES = ("admin", "manager", "customer")
UNIT_TYPES = ("bedsitter", "studio", "1_bedroom", "2_bedroom", "3_bedroom", "4_bedroom")
PROPERTY_STATUSES = ("pending", "approved", "rejected")
BOOKING_STATUSES = ("pending", "confirmed", "cancelled", "completed")


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    """One table for all three roles: admin, manager, customer."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="customer")
    # Managers must be approved by an admin before they can list properties
    is_approved = db.Column(db.Boolean, default=True, nullable=False)
    # Admin can block a user
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    properties = db.relationship(
        "Property", back_populates="manager", cascade="all, delete-orphan"
    )
    bookings = db.relationship(
        "Booking", back_populates="customer", cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class City(db.Model):
    """Cities managed by the admin. Managers pick one when registering a property."""
    __tablename__ = "cities"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)

    properties = db.relationship("Property", back_populates="city")

    def __repr__(self):
        return f"<City {self.name}>"


class Property(db.Model):
    """A building / apartment complex registered by a manager."""
    __tablename__ = "properties"

    id = db.Column(db.Integer, primary_key=True)
    manager_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey("cities.id"), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    area = db.Column(db.String(100))  # estate / neighbourhood within the city
    address = db.Column(db.String(255))
    image_url = db.Column(db.String(500))
    # Admin approves or rejects (or deletes fake listings)
    status = db.Column(db.String(20), default="pending", nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    manager = db.relationship("User", back_populates="properties")
    city = db.relationship("City", back_populates="properties")
    units = db.relationship(
        "Unit", back_populates="property", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Property {self.name}>"


class Unit(db.Model):
    """A rentable type inside a property, e.g. '2 bedroom at KES 25,000/month'."""
    __tablename__ = "units"

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), nullable=False)
    unit_type = db.Column(db.String(30), nullable=False)  # see UNIT_TYPES
    price_per_month = db.Column(db.Numeric(10, 2), nullable=False)
    bathrooms = db.Column(db.Integer, default=1)
    amenities = db.Column(db.String(500))  # comma separated: "wifi,parking,water"
    image_url = db.Column(db.String(500))
    total_units = db.Column(db.Integer, default=1, nullable=False)
    available_units = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    property = db.relationship("Property", back_populates="units")
    bookings = db.relationship("Booking", back_populates="unit", cascade="all, delete-orphan")

    __table_args__ = (
        db.CheckConstraint("price_per_month >= 0", name="ck_unit_price_positive"),
        db.CheckConstraint("available_units <= total_units", name="ck_unit_availability"),
    )

    def __repr__(self):
        return f"<Unit {self.unit_type} @ {self.price_per_month}>"


class Booking(db.Model):
    """A customer's booking of a unit."""
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey("units.id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_price = db.Column(db.Numeric(10, 2))
    status = db.Column(db.String(20), default="pending", nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    customer = db.relationship("User", back_populates="bookings")
    unit = db.relationship("Unit", back_populates="bookings")

    def __repr__(self):
        return f"<Booking {self.id} {self.status}>"
