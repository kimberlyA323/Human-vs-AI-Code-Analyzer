import ast
import subprocess
import sys
import tempfile
from pathlib import Path


MAX_CODE_LENGTH = 20_000
RUN_TIMEOUT_SECONDS = 3


def analyze_code(source_code, test_input=""):
    """Validate and run one Python program, then return a simple result."""

    if not source_code.strip():
        return make_result(False, error="No code was provided.")
    if len(source_code) > MAX_CODE_LENGTH:
        return make_result(False, error="Code is too long to analyze.")

    try:
        ast.parse(source_code)
    except SyntaxError as error:
        message = f"Syntax error on line {error.lineno}: {error.msg}"
        return make_result(False, error=message)

    # Each program runs in a temporary folder that is removed afterward.
    with tempfile.TemporaryDirectory() as temporary_directory:
        program_path = Path(temporary_directory) / "submitted_code.py"
        program_path.write_text(source_code, encoding="utf-8")

        try:
            completed = subprocess.run(
                [sys.executable, "-I", str(program_path)],
                input=test_input,
                capture_output=True,
                cwd=temporary_directory,
                text=True,
                timeout=RUN_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return make_result(False, error="The program exceeded the 3-second limit.")

    if completed.returncode != 0:
        error_text = completed.stderr.strip() or "The program could not run."
        return make_result(False, output=completed.stdout.strip(), error=error_text)

    return make_result(True, output=completed.stdout.strip())


def make_result(success, output="", error=""):
    return {"success": success, "output": output, "error": error}
