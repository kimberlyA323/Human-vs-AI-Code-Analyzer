import os
from functools import wraps

from dotenv import load_dotenv
from flask import (
    abort,
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import select
from werkzeug.security import check_password_hash, generate_password_hash

from analyzer import analyze_code
from models import AnalysisResult, CodeSample, Comparison, User, db


load_dotenv()


def login_required(view):
    """Send visitors to the login page when a page requires an account."""

    @wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view(**kwargs)

    return wrapped_view


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
        if "user_id" in session:
            return render_template("home.html")
        return redirect(url_for("login"))

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
            return redirect(url_for("login"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = db.session.scalar(select(User).where(User.email == email))

            if user is None or not check_password_hash(user.password_hash, password):
                flash("Email or password is incorrect.", "error")
                return render_template("login.html", email=email)

            # Only the database ID is stored in the browser session.
            session.clear()
            session["user_id"] = user.id
            session["username"] = user.username
            flash("You are now logged in.", "success")
            return redirect(url_for("home"))

        return render_template("login.html")

    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        flash("You have been logged out.", "success")
        return redirect(url_for("login"))

    @app.route("/compare", methods=["GET", "POST"])
    @login_required
    def compare():
        if request.method == "POST":
            problem_name = request.form.get("problem_name", "").strip()
            human_code = request.form.get("human_code", "")
            ai_code = request.form.get("ai_code", "")
            test_input = request.form.get("test_input", "")
            expected_output = request.form.get("expected_output", "").strip()

            if not problem_name or not human_code.strip() or not ai_code.strip():
                flash("Problem name and both code samples are required.", "error")
                return render_template(
                    "compare.html",
                    problem_name=problem_name,
                    human_code=human_code,
                    ai_code=ai_code,
                    test_input=test_input,
                    expected_output=expected_output,
                )

            human_result = analyze_code(human_code, test_input, expected_output)
            ai_result = analyze_code(ai_code, test_input, expected_output)
            comparison = save_comparison(
                user_id=session["user_id"],
                problem_name=problem_name,
                test_input=test_input,
                expected_output=expected_output,
                human_code=human_code,
                ai_code=ai_code,
                human_result=human_result,
                ai_result=ai_result,
            )
            return render_template(
                "results.html",
                comparison_id=comparison.id,
                problem_name=problem_name,
                expected_output=expected_output,
                human_result=human_result,
                ai_result=ai_result,
            )

        return render_template("compare.html")

    @app.route("/history")
    @login_required
    def history():
        comparisons = db.session.scalars(
            select(Comparison)
            .where(Comparison.user_id == session["user_id"])
            .order_by(Comparison.created_at.desc())
        ).all()
        return render_template("history.html", comparisons=comparisons)

    @app.route("/history/<int:comparison_id>")
    @login_required
    def history_detail(comparison_id):
        # Filtering by user ID prevents one user from viewing another user's work.
        comparison = db.session.scalar(
            select(Comparison).where(
                Comparison.id == comparison_id,
                Comparison.user_id == session["user_id"],
            )
        )
        if comparison is None:
            abort(404)

        samples = {sample.code_type: sample for sample in comparison.code_samples}
        return render_template(
            "history_detail.html", comparison=comparison, samples=samples
        )

    return app


def save_comparison(
    user_id,
    problem_name,
    test_input,
    expected_output,
    human_code,
    ai_code,
    human_result,
    ai_result,
):
    """Save one comparison and its two code samples as a single database unit."""

    comparison = Comparison(
        user_id=user_id,
        problem_name=problem_name,
        test_input=test_input,
        expected_output=expected_output,
    )
    comparison.code_samples.extend(
        [
            make_code_sample("Human", human_code, human_result),
            make_code_sample("AI", ai_code, ai_result),
        ]
    )
    db.session.add(comparison)
    db.session.commit()
    return comparison


def make_code_sample(code_type, source_code, result):
    sample = CodeSample(code_type=code_type, source_code=source_code)
    sample.analysis_result = AnalysisResult(
        tests_passed=result["tests_passed"],
        tests_failed=result["tests_failed"],
        execution_time=result["execution_time"],
        complexity_score=result["complexity_score"],
        error_count=1 if result["error"] else 0,
        output=result["output"],
        error_message=result["error"],
    )
    return sample


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
