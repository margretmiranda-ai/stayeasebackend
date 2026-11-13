from flask import g, jsonify, request, session

from server.app import app
from server.config import db
from server.email_service import send_auth_email
from server.helpers import error, load_or_400, roles_required
from server.models import User
from server.schemas import LoginSchema, RegisterSchema, UserSchema

user_schema = UserSchema()
session_user_schema = UserSchema(only=("id", "name", "role"))


@app.post("/api/auth/register")
def register():
    data = load_or_400(RegisterSchema(), request.get_json(silent=True))
    email = data["email"].lower()
    if User.query.filter_by(email=email).first():
        return error("Email already registered", 409)

    user = User(
        name=data["name"],
        email=email,
        phone=data.get("phone"),
        role=data["role"],
        # managers wait for admin approval, customers can use the app straight away
        is_approved=(data["role"] != "manager"),
    )
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()
    send_auth_email(user, "registration")

    message = "Registered successfully"
    if user.role == "manager":
        message += ". An admin must approve your account before you can list properties"
    return jsonify({"message": message, "user": user_schema.dump(user)}), 201


@app.post("/api/auth/login")
def login():
    data = load_or_400(LoginSchema(), request.get_json(silent=True))
    user = User.query.filter_by(email=data["email"].lower()).first()
    if not user or not user.check_password(data["password"]):
        return error("Invalid email or password", 401)
    if not user.is_active:
        return error("This account has been blocked", 403)

    session.clear()
    session["user_id"] = user.id
    send_auth_email(user, "login")
    return jsonify({"user": session_user_schema.dump(user)})


@app.post("/api/auth/logout")
@roles_required()
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"})


@app.get("/api/auth/me")
@roles_required()
def me():
    return jsonify(session_user_schema.dump(g.current_user))
