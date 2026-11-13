import sys

from flask import Flask, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException

from config import Config, db

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
migrate = Migrate(app, db)
CORS(
    app,
    resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
    supports_credentials=True,
)


@app.get("/")
def index():
    return jsonify({"message": "StayEase API"})


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.errorhandler(ValidationError)
def handle_validation(err):
    return jsonify({"error": "Validation failed", "details": err.messages}), 400


@app.errorhandler(HTTPException)
def handle_http(err):
    return jsonify({"error": err.description}), err.code


if __name__ == "__main__":
    sys.modules["app"] = sys.modules[__name__]


from routes import admin, auth, bookings, cities, properties, units


if __name__ == "__main__":
    app.run(debug=True, port=5555)
