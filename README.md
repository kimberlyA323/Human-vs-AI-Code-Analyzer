# Human vs. AI Code Analyzer

A Flask web application that compares human-written and AI-generated Python
programs. Both programs receive the same input, and the application compares
their output, execution time, errors, and cyclomatic complexity.

## Features

- Account registration with hashed passwords
- Login and logout using Flask sessions
- Separate human and AI code inputs
- Python syntax validation and a three-second execution limit
- Passed and failed test results
- Execution-time and complexity measurements
- Side-by-side results
- PostgreSQL storage for users, code samples, and analysis results
- Private comparison history for each user

## Technology

- Python and Flask
- Flask-SQLAlchemy
- PostgreSQL
- HTML and CSS
- Pytest

## Run the project

1. Install PostgreSQL and create a database named `code_analyzer`.
2. Create and activate a Python virtual environment.

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env`. Update the PostgreSQL username and password,
   and choose a local secret key.

   ```bash
   cp .env.example .env
   ```

5. Start the application:

   ```bash
   python -m flask --app app run --debug
   ```

6. Open `http://127.0.0.1:5000/register`.

The application creates its database tables the first time it starts.

## How to compare programs

Both programs should be complete Python scripts that read from standard input
with `input()` and print their answer with `print()`. For example:

```python
number = int(input())
print(number * 2)
```

For this program, a test input of `4` and expected output of `8` will pass.
Whitespace at the beginning and end of the output is ignored.

## Project structure

- `app.py` contains the Flask routes and form handling.
- `models.py` contains the database classes from the class diagram.
- `analyzer.py` validates and analyzes submitted Python programs.
- `templates/` contains the HTML pages.
- `static/` contains the shared stylesheet.
- `tests/` contains the automated tests.
- `uml-diagrams/` contains the use-case, sequence, and class diagrams.

## Run the tests

```bash
pytest
```

## Reset a local password

If a local account password is forgotten, activate the virtual environment and
run the command below. The password prompt does not display the typed password.

```bash
python -m flask --app app reset-password student@example.com
```

## Safety note

This is a local classroom project, not a production code-execution service.
Submitted programs run in a temporary directory with isolated Python mode and a
three-second timeout, but they are not placed inside a full operating-system
sandbox. Only run code that you trust.
