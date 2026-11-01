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


def test_registration_page_loads():
    app = make_test_app()
    client = app.test_client()

    response = client.get("/register")

    assert response.status_code == 200
    assert b"Create an Account" in response.data


def test_user_can_register():
    app = make_test_app()
    client = app.test_client()

    response = client.post(
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


def test_duplicate_user_is_rejected():
    app = make_test_app()
    client = app.test_client()
    form_data = {
        "username": "student1",
        "email": "student@example.com",
        "password": "password123",
    }

    client.post("/register", data=form_data)
    response = client.post("/register", data=form_data)

    assert b"already registered" in response.data


def test_short_password_is_rejected():
    app = make_test_app()
    client = app.test_client()

    response = client.post(
        "/register",
        data={
            "username": "student1",
            "email": "student@example.com",
            "password": "short",
        },
    )

    assert b"at least 8 characters" in response.data


def register_test_user(client):
    client.post(
        "/register",
        data={
            "username": "student1",
            "email": "student@example.com",
            "password": "password123",
        },
    )


def login_test_user(client):
    register_test_user(client)
    client.post(
        "/login",
        data={"email": "student@example.com", "password": "password123"},
    )


def test_user_can_log_in_and_log_out():
    app = make_test_app()
    client = app.test_client()
    register_test_user(client)

    login_response = client.post(
        "/login",
        data={"email": "student@example.com", "password": "password123"},
        follow_redirects=True,
    )
    assert b"Welcome to the Code Analyzer" in login_response.data

    logout_response = client.post("/logout", follow_redirects=True)
    assert b"You have been logged out" in logout_response.data


def test_wrong_password_is_rejected():
    app = make_test_app()
    client = app.test_client()
    register_test_user(client)

    response = client.post(
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
    assert b"Compare Code" in response.data


def test_user_can_run_a_code_comparison():
    app = make_test_app()
    client = app.test_client()
    login_test_user(client)

    response = client.post(
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
    assert response.data.count(b"Execution time") == 2
    assert response.data.count(b"Complexity") == 2


def test_comparison_is_saved_with_two_results():
    app = make_test_app()
    client = app.test_client()
    login_test_user(client)

    client.post(
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
    client.post(
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
    first_client.post(
        "/compare",
        data={
            "problem_name": "Private problem",
            "human_code": "print(1)",
            "ai_code": "print(1)",
            "expected_output": "1",
        },
    )

    second_client = app.test_client()
    second_client.post(
        "/register",
        data={
            "username": "student2",
            "email": "student2@example.com",
            "password": "password123",
        },
    )
    second_client.post(
        "/login",
        data={"email": "student2@example.com", "password": "password123"},
    )

    assert second_client.get("/history/1").status_code == 404
