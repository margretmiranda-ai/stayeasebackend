from .admin import admin_bp
from .auth import auth_bp
from .bookings import bookings_bp
from .cities import cities_bp
from .properties import properties_bp
from .units import units_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(cities_bp, url_prefix="/api/cities")
    app.register_blueprint(properties_bp, url_prefix="/api/properties")
    app.register_blueprint(units_bp, url_prefix="/api")
    app.register_blueprint(bookings_bp, url_prefix="/api/bookings")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
