from server.config import db
from server.models import Booking, City, Property, Unit, User
from server.seed import seed_database


def test_seed_resets_and_populates_all_tables(app):
    with app.app_context():
        seed_database()

        assert City.query.count() == 4
        assert User.query.count() == 5
        assert Property.query.count() == 4
        assert Unit.query.count() == 5
        assert Booking.query.count() == 4
        assert {booking.status for booking in Booking.query.all()} == {
            "pending",
            "confirmed",
            "cancelled",
            "completed",
        }
        assert User.query.filter_by(email="admin@test.com").first() is None

        seed_database()

        assert City.query.count() == 4
        assert User.query.count() == 5
        assert Property.query.count() == 4
        assert Unit.query.count() == 5
        assert Booking.query.count() == 4
        assert db.session.query(Booking).join(Unit).join(Property).join(City).count() == 4
