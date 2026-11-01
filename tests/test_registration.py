from app import User, create_app, db


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
