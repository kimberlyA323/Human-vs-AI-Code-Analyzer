import re

from app import User, create_app, db
from models import AnalysisResult, CodeSample, Comparison


def make_test_app():
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-key",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )


def submit_form(client, path, data=None, **kwargs):
    form = client.get("/" if path == "/logout" else path)
    token = re.search(rb'name="_csrf_token" value="([a-f0-9]+)"', form.data)
    assert token is not None
    return client.post(
        path, data={"_csrf_token": token[1].decode(), **(data or {})}, **kwargs
    )


def test_registration_page_loads():
    app = make_test_app()
    client = app.test_client()

    response = client.get("/register")

    assert response.status_code == 200
    assert b"Create an Account" in response.data


def test_user_can_register():
    app = make_test_app()
    client = app.test_client()

    response = submit_form(
        client,
        "/register",
        data={
            "username": "student1",
            "email": "student@example.com",
            "password": "password123",
        },
        follow_redirects=True,
    )

    assert b"Account created successfully" in response.data
    assert b"Log In" in response.data

    with app.app_context():
        user = db.session.execute(db.select(User)).scalar_one()
        assert user.username == "student1"
        assert user.password_hash != "password123"


def test_duplicate_username_is_rejected():
    app = make_test_app()
    client = app.test_client()
    form_data = {
        "username": "student1",
        "email": "student@example.com",
        "password": "password123",
    }

    submit_form(client, "/register", data=form_data)
    form_data["email"] = "different@example.com"
    response = submit_form(client, "/register", data=form_data)

    assert b"username is already registered" in response.data


def test_duplicate_email_is_rejected():
    app = make_test_app()
    client = app.test_client()
    register_test_user(client)

    response = submit_form(
        client,
        "/register",
        data={
            "username": "different-user",
            "email": "student@example.com",
            "password": "password123",
        },
    )

    assert b"email is already registered" in response.data


def test_short_password_is_rejected():
    app = make_test_app()
    client = app.test_client()

    response = submit_form(
        client,
        "/register",
        data={
            "username": "student1",
            "email": "student@example.com",
            "password": "short",
        },
    )

    assert b"at least 8 characters" in response.data


def register_test_user(client):
    submit_form(
        client,
        "/register",
        data={
            "username": "student1",
            "email": "student@example.com",
            "password": "password123",
        },
    )


def login_test_user(client):
    register_test_user(client)
    submit_form(
        client,
        "/login",
        data={"email": "student@example.com", "password": "password123"},
    )


def test_user_can_log_in_and_log_out():
    app = make_test_app()
    client = app.test_client()
    register_test_user(client)

    login_response = submit_form(
        client,
        "/login",
        data={"email": "student@example.com", "password": "password123"},
        follow_redirects=True,
    )
    assert b"Welcome, student1" in login_response.data

    logout_response = submit_form(client, "/logout", follow_redirects=True)
    assert b"You have been logged out" in logout_response.data


def test_wrong_password_is_rejected():
    app = make_test_app()
    client = app.test_client()
    register_test_user(client)

    response = submit_form(
        client,
        "/login",
        data={"email": "student@example.com", "password": "wrong-password"},
    )

    assert b"Email or password is incorrect" in response.data


def test_comparison_page_requires_login():
    app = make_test_app()
    client = app.test_client()

    response = client.get("/compare", follow_redirects=True)

    assert b"Please log in to continue" in response.data


def test_logged_in_user_sees_human_code_field():
    app = make_test_app()
    client = app.test_client()
    login_test_user(client)

    response = client.get("/compare")

    assert response.status_code == 200
    assert b"Human-written Python code" in response.data


def test_logged_in_user_sees_ai_code_field():
    app = make_test_app()
    client = app.test_client()
    login_test_user(client)

    response = client.get("/compare")

    assert b"AI-generated Python code" in response.data
    assert b"Run Comparison" in response.data


def test_user_can_run_a_code_comparison():
    app = make_test_app()
    client = app.test_client()
    login_test_user(client)

    response = submit_form(
        client,
        "/compare",
        data={
            "problem_name": "Greeting",
            "human_code": "name = input()\nprint('Hello', name)",
            "ai_code": "value = input()\nprint(f'Hello {value}')",
            "test_input": "Kim\n",
            "expected_output": "Hello Kim",
        },
    )

    assert response.status_code == 200
    assert b"Comparison Results" in response.data
    assert response.data.count(b"Hello Kim") >= 2
    assert response.data.count(b"Tests passed") == 2
    assert response.data.count(b"Execution time") >= 2
    assert response.data.count(b"Complexity") == 2
    assert b"better" in response.data or b"equally correct" in response.data


def test_user_can_run_three_test_cases():
    app = make_test_app()
    client = app.test_client()
    login_test_user(client)

    response = submit_form(
        client,
        "/compare",
        data={
            "problem_name": "Double numbers",
            "human_code": "number = int(input())\nprint(number * 2)",
            "ai_code": "value = int(input())\nprint(2 * value)",
            "test_input_1": "2",
            "expected_output_1": "4",
            "test_input_2": "5",
            "expected_output_2": "10",
            "test_input_3": "0",
            "expected_output_3": "0",
        },
    )

    assert response.status_code == 200
    assert b"Test cases run:</strong> 3" in response.data
    assert response.data.count(b"Tests passed") == 2
    assert response.data.count(b"Case 3: Passed") == 2


def test_first_test_case_requires_an_expected_output():
    app = make_test_app()
    client = app.test_client()
    login_test_user(client)

    response = submit_form(
        client,
        "/compare",
        data={
            "problem_name": "Missing answer",
            "human_code": "print(1)",
            "ai_code": "print(1)",
            "test_input_1": "1",
            "expected_output_1": "",
        },
    )

    assert b"first test case needs an expected output" in response.data


def test_comparison_preserves_case_numbers_and_marks_wrong_answers_failed():
    app = make_test_app()
    client = app.test_client()
    login_test_user(client)
    response = submit_form(
        client,
        "/compare",
        data={
            "problem_name": "Check result styling",
            "human_code": "print(1)",
            "ai_code": "print(2)",
            "expected_output_1": "1",
            "expected_output_3": "2",
        },
    )

    assert b"Case 3: Passed" in response.data
    assert b"Case 3: Failed" in response.data
    assert response.data.count(b'class="status failed"') == 2
    assert b"Case 3:" in client.get("/history/1").data


def test_overlong_problem_name_is_rejected_before_saving():
    app = make_test_app()
    client = app.test_client()
    login_test_user(client)
    response = submit_form(
        client,
        "/compare",
        data={
            "problem_name": "x" * 121,
            "human_code": "print(1)",
            "ai_code": "print(1)",
            "expected_output_1": "1",
        },
    )

    assert b"Problem name must be 120 characters or fewer" in response.data
    with app.app_context():
        assert db.session.execute(db.select(Comparison)).scalar_one_or_none() is None


def test_post_without_valid_form_token_is_rejected():
    app = make_test_app()
    client = app.test_client()
    login_test_user(client)
    client.get("/compare")

    assert client.post("/logout").status_code == 400
    assert client.post("/compare", data={"_csrf_token": "wrong"}).status_code == 400
    assert client.get("/compare").status_code == 200


def test_comparison_is_saved_with_two_results():
    app = make_test_app()
    client = app.test_client()
    login_test_user(client)

    submit_form(
        client,
        "/compare",
        data={
            "problem_name": "Add numbers",
            "human_code": "print(2 + 2)",
            "ai_code": "answer = 4\nprint(answer)",
            "test_input": "",
            "expected_output": "4",
        },
    )

    with app.app_context():
        comparison = db.session.execute(db.select(Comparison)).scalar_one()
        samples = db.session.execute(db.select(CodeSample)).scalars().all()
        results = db.session.execute(db.select(AnalysisResult)).scalars().all()

        assert comparison.problem_name == "Add numbers"
        assert len(samples) == 2
        assert len(results) == 2


def test_user_can_view_saved_comparison_history():
    app = make_test_app()
    client = app.test_client()
    login_test_user(client)
    submit_form(
        client,
        "/compare",
        data={
            "problem_name": "Saved problem",
            "human_code": "print('done')",
            "ai_code": "print('done')",
            "test_input": "",
            "expected_output": "done",
        },
    )

    history_response = client.get("/history")
    detail_response = client.get("/history/1")

    assert b"Saved problem" in history_response.data
    assert b"Human Code" in detail_response.data
    assert b"AI Code" in detail_response.data


def test_user_cannot_view_another_users_comparison():
    app = make_test_app()
    first_client = app.test_client()
    login_test_user(first_client)
    submit_form(
        first_client,
        "/compare",
        data={
            "problem_name": "Private problem",
            "human_code": "print(1)",
            "ai_code": "print(1)",
            "expected_output": "1",
        },
    )

    second_client = app.test_client()
    submit_form(
        second_client,
        "/register",
        data={
            "username": "student2",
            "email": "student2@example.com",
            "password": "password123",
        },
    )
    submit_form(
        second_client,
        "/login",
        data={"email": "student2@example.com", "password": "password123"},
    )

    assert second_client.get("/history/1").status_code == 404


def test_home_page_shows_recent_comparison():
    app = make_test_app()
    client = app.test_client()
    login_test_user(client)
    submit_form(
        client,
        "/compare",
        data={
            "problem_name": "Recent problem",
            "human_code": "print(2)",
            "ai_code": "print(2)",
            "expected_output": "2",
        },
    )

    response = client.get("/")

    assert b"Recent Comparisons" in response.data
    assert b"Recent problem" in response.data


def test_unknown_page_uses_helpful_error_page():
    app = make_test_app()
    client = app.test_client()

    response = client.get("/not-a-real-page")

    assert response.status_code == 404
    assert b"Page Not Found" in response.data


def test_password_can_be_reset_from_command_line():
    app = make_test_app()
    client = app.test_client()
    register_test_user(client)
    runner = app.test_cli_runner()

    result = runner.invoke(
        args=["reset-password", "student@example.com"],
        input="new-password-123\nnew-password-123\n",
    )

    assert result.exit_code == 0
    assert "Password updated successfully" in result.output

    login_response = submit_form(
        client,
        "/login",
        data={
            "email": "student@example.com",
            "password": "new-password-123",
        },
    )
    assert login_response.status_code == 302
