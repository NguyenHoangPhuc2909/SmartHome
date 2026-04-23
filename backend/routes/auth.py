from flask import Blueprint, session, redirect, url_for, jsonify
from flask_dance.contrib.google import google
from models import db, User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/auth/after_login")
def after_login():
    if not google.authorized:
        return redirect(url_for("google.login"))
    info = google.get("/oauth2/v2/userinfo").json()
    user = User.query.filter_by(google_id=info["id"]).first()
    if not user:
        user = User(
            google_id = info["id"],
            name      = info.get("name", ""),
            email     = info.get("email", ""),
            avatar    = info.get("picture", ""),
        )
        db.session.add(user)
        db.session.commit()
    session["user_id"]   = user.id
    session["user_name"] = user.name
    session["avatar"]    = user.avatar
    # redirect sang React frontend
    return redirect("http://localhost:5173/dashboard")


@auth_bp.route("/auth/logout")
def logout():
    session.clear()
    return redirect("http://localhost:5173/login")


@auth_bp.route("/auth/me")
def me():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user = User.query.get(session["user_id"])
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        "id":     user.id,
        "name":   user.name,
        "email":  user.email,
        "avatar": user.avatar,
    })