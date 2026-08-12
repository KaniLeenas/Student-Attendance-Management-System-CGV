"""Session based authentication with two roles: admin and staff."""
from __future__ import annotations

from functools import wraps

from flask import session, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash, check_password_hash

ROLES = ("admin", "staff")


def hash_password(raw):
    return generate_password_hash(raw)


def verify_password(raw, hashed):
    return check_password_hash(hashed, raw)


def current_user():
    if "user_id" in session:
        return {"id": session["user_id"],
                "username": session["username"],
                "role": session["role"],
                "full_name": session.get("full_name", session["username"])}
    return None


def login_required(view):
    @wraps(view)
    def wrapped(*a, **k):
        if not current_user():
            flash("Please log in to continue.", "error")
            return redirect(url_for("login", next=request.path))
        return view(*a, **k)
    return wrapped


def role_required(*roles):
    def deco(view):
        @wraps(view)
        def wrapped(*a, **k):
            u = current_user()
            if not u:
                flash("Please log in to continue.", "error")
                return redirect(url_for("login", next=request.path))
            if u["role"] not in roles:
                flash("You don't have permission to open that page.", "error")
                return redirect(url_for("dashboard"))
            return view(*a, **k)
        return wrapped
    return deco