import os

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select
from werkzeug.security import generate_password_hash


load_dotenv()
db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)


def create_app(test_config=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "development-key")
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:password@localhost:5432/code_analyzer",
    )
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://", "postgresql+psycopg://", 1
        )
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.route("/")
    def home():
        return redirect(url_for("register"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            error = validate_registration(username, email, password)

            if not error:
                existing_user = db.session.scalar(
                    select(User).where(
                        (User.username == username) | (User.email == email)
                    )
                )
                if existing_user:
                    error = "That username or email is already registered."

            if error:
                flash(error, "error")
                return render_template(
                    "register.html", username=username, email=email
                )

            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
            )
            db.session.add(user)
            db.session.commit()

            flash("Account created successfully. You can now log in.", "success")
            return redirect(url_for("register"))

        return render_template("register.html")

    return app


def validate_registration(username, email, password):
    if not username or not email or not password:
        return "All fields are required."
    if len(username) < 3:
        return "Username must be at least 3 characters."
    if "@" not in email or "." not in email.split("@")[-1]:
        return "Enter a valid email address."
    if len(password) < 8:
        return "Password must be at least 8 characters."
    return None


if __name__ == "__main__":
    create_app().run(debug=True)
