# Human-vs-AI-Code-Analyzer
A web application that compares human-written code and AI-generated code based on test results, execution time, errors, and code complexity.

## Current feature

The first user story adds user registration. A new user can enter a username,
email address, and password. Passwords are hashed before they are stored in the
PostgreSQL database.

## Run the project

1. Install PostgreSQL and create a database named `code_analyzer`.
2. Create and activate a Python virtual environment.
3. Install the packages:

   ```bash
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and update the database password.
5. Start the application:

   ```bash
   flask --app 'app:create_app()' run --debug
   ```

6. Open `http://127.0.0.1:5000/register`.

The application creates the `users` table the first time it starts.

## Run the tests

```bash
pytest
```
