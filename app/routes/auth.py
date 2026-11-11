from flask import Blueprint, g, jsonify, request
from flask_jwt_extended import create_access_token

from ..extensions import db
from ..models import User
from ..schemas import LoginSchema, RegisterSchema, UserSchema
from ..utils import error, load_or_400, roles_required

auth_bp = Blueprint("auth", __name__)
user_schema = UserSchema()


@auth_bp.post("/register")
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

    message = "Registered successfully"
    if user.role == "manager":
        message += ". An admin must approve your account before you can list properties"
    return jsonify({"message": message, "user": user_schema.dump(user)}), 201


@auth_bp.post("/login")
def login():
    data = load_or_400(LoginSchema(), request.get_json(silent=True))
    user = User.query.filter_by(email=data["email"].lower()).first()
    if not user or not user.check_password(data["password"]):
        return error("Invalid email or password", 401)
    if not user.is_active:
        return error("This account has been blocked", 403)

    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return jsonify({"access_token": token, "user": user_schema.dump(user)})


@auth_bp.get("/me")
@roles_required()
def me():
    return jsonify(user_schema.dump(g.current_user))
