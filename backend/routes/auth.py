from flask import Blueprint, session, request, jsonify
from models import db, User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/auth/register", methods=["POST"])
def register():
    data = request.json or {}
    username = data.get("username")
    password = data.get("password")
    name     = data.get("name", username)

    if not username or not password:
        return jsonify({"error": "Thiếu username hoặc password"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username đã tồn tại"}), 400

    user = User(username=username, name=name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Đăng ký thành công", "user": username})


@auth_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.json or {}
    username = data.get("username")
    password = data.get("password")

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Username hoặc password sai"}), 401

    session["user_id"]   = user.id
    session["user_name"] = user.username
    
    return jsonify({
        "message": "Đăng nhập thành công",
        "id":      user.id,
        "name":    user.name,
        "username": user.username
    })


@auth_bp.route("/auth/logout")
def logout():
    session.clear()
    return jsonify({"message": "Đã đăng xuất"})


@auth_bp.route("/auth/me")
def me():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user = User.query.get(session["user_id"])
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        "id":       user.id,
        "name":     user.name,
        "username": user.username,
    })