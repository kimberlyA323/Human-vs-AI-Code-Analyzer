import os
from functools import wraps

import click
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

from analyzer import analyze_test_cases, compare_results
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
    app.config["MAX_CONTENT_LENGTH"] = 100_000
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.route("/")
    def home():
        if "user_id" in session:
            recent_comparisons = db.session.scalars(
                select(Comparison)
                .where(Comparison.user_id == session["user_id"])
                .order_by(Comparison.created_at.desc())
                .limit(3)
            ).all()
            return render_template(
                "home.html", recent_comparisons=recent_comparisons
            )
        return redirect(url_for("login"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            error = validate_registration(username, email, password)

            if not error:
                username_owner = db.session.scalar(
                    select(User).where(User.username == username)
                )
                email_owner = db.session.scalar(
                    select(User).where(User.email == email)
                )
                if username_owner:
                    error = "That username is already registered."
                elif email_owner:
                    error = "That email is already registered."

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
            test_cases, test_error = read_test_cases(request.form)

            if not problem_name or not human_code.strip() or not ai_code.strip():
                test_error = "Problem name and both code samples are required."

            if test_error:
                flash(test_error, "error")
                return render_template(
                    "compare.html",
                    problem_name=problem_name,
                    human_code=human_code,
                    ai_code=ai_code,
                    test_cases=form_test_cases(request.form),
                )

            human_result = analyze_test_cases(human_code, test_cases)
            ai_result = analyze_test_cases(ai_code, test_cases)
            comparison = save_comparison(
                user_id=session["user_id"],
                problem_name=problem_name,
                test_input=format_saved_test_values(test_cases, "input"),
                expected_output=format_saved_test_values(
                    test_cases, "expected_output"
                ),
                human_code=human_code,
                ai_code=ai_code,
                human_result=human_result,
                ai_result=ai_result,
            )
            return render_template(
                "results.html",
                comparison_id=comparison.id,
                problem_name=problem_name,
                test_cases=test_cases,
                human_result=human_result,
                ai_result=ai_result,
                summary=compare_results(human_result, ai_result),
            )

        return render_template("compare.html", test_cases=form_test_cases({}))

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
        human_result = model_result_to_dictionary(samples["Human"].analysis_result)
        ai_result = model_result_to_dictionary(samples["AI"].analysis_result)
        return render_template(
            "history_detail.html",
            comparison=comparison,
            samples=samples,
            summary=compare_results(human_result, ai_result),
        )

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("error.html", error_code=404), 404

    @app.errorhandler(413)
    def request_too_large(error):
        return render_template("error.html", error_code=413), 413

    @app.cli.command("reset-password")
    @click.argument("email")
    @click.password_option(confirmation_prompt=True)
    def reset_password(email, password):
        """Reset one local account password from the command line."""

        user = db.session.scalar(
            select(User).where(User.email == email.strip().lower())
        )
        if user is None:
            raise click.ClickException("No account was found for that email.")
        if len(password) < 8:
            raise click.ClickException("Password must be at least 8 characters.")

        user.password_hash = generate_password_hash(password)
        db.session.commit()
        click.echo("Password updated successfully.")

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


def model_result_to_dictionary(result):
    """Convert a saved database result to the format used by the analyzer."""

    return {
        "tests_passed": result.tests_passed,
        "tests_failed": result.tests_failed,
        "execution_time": result.execution_time,
        "complexity_score": result.complexity_score,
    }


def validate_registration(username, email, password):
    if not username or not email or not password:
        return "All fields are required."
    if len(username) < 3:
        return "Username must be at least 3 characters."
    if len(username) > 50:
        return "Username must be 50 characters or fewer."
    if "@" not in email or "." not in email.split("@")[-1]:
        return "Enter a valid email address."
    if len(email) > 120:
        return "Email must be 120 characters or fewer."
    if len(password) < 8:
        return "Password must be at least 8 characters."
    return None


def form_test_cases(form):
    """Return three rows of values so the form can be filled again after an error."""

    return [
        {
            "input": form.get(f"test_input_{number}", form.get("test_input", ""))
            if number == 1
            else form.get(f"test_input_{number}", ""),
            "expected_output": form.get(
                f"expected_output_{number}", form.get("expected_output", "")
            )
            if number == 1
            else form.get(f"expected_output_{number}", ""),
        }
        for number in range(1, 4)
    ]


def read_test_cases(form):
    """Validate the test rows and return only the rows the user completed."""

    rows = form_test_cases(form)
    if not rows[0]["expected_output"].strip():
        return [], "The first test case needs an expected output."

    test_cases = []
    for number, row in enumerate(rows, start=1):
        has_value = row["input"].strip() or row["expected_output"].strip()
        if not has_value:
            continue
        if not row["expected_output"].strip():
            return [], f"Test case {number} needs an expected output."
        test_cases.append(row)
    return test_cases, None


def format_saved_test_values(test_cases, field_name):
    """Store all case values in the existing comparison text columns."""

    return "\n\n".join(
        f"Case {number}:\n{case[field_name]}"
        for number, case in enumerate(test_cases, start=1)
    )


if __name__ == "__main__":
    create_app().run(debug=True)
