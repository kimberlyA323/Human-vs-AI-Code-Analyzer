import ast
import subprocess
import sys
import tempfile
import time
from pathlib import Path


MAX_CODE_LENGTH = 20_000
RUN_TIMEOUT_SECONDS = 3


def analyze_code(source_code, test_input="", expected_output=""):
    """Validate and run one Python program, then return a simple result."""

    if not source_code.strip():
        return make_result(False, error="No code was provided.", tests_failed=1)
    if len(source_code) > MAX_CODE_LENGTH:
        return make_result(False, error="Code is too long to analyze.", tests_failed=1)

    try:
        syntax_tree = ast.parse(source_code)
    except SyntaxError as error:
        message = f"Syntax error on line {error.lineno}: {error.msg}"
        return make_result(False, error=message, tests_failed=1)

    complexity_score = calculate_complexity(syntax_tree)

    # Each program runs in a temporary folder that is removed afterward.
    with tempfile.TemporaryDirectory() as temporary_directory:
        program_path = Path(temporary_directory) / "submitted_code.py"
        program_path.write_text(source_code, encoding="utf-8")

        try:
            start_time = time.perf_counter()
            completed = subprocess.run(
                [sys.executable, "-I", str(program_path)],
                input=test_input,
                capture_output=True,
                cwd=temporary_directory,
                text=True,
                timeout=RUN_TIMEOUT_SECONDS,
                check=False,
            )
            execution_time = time.perf_counter() - start_time
        except subprocess.TimeoutExpired:
            return make_result(
                False,
                error="The program exceeded the 3-second limit.",
                tests_failed=1,
                execution_time=RUN_TIMEOUT_SECONDS,
                complexity_score=complexity_score,
            )

    if completed.returncode != 0:
        error_text = completed.stderr.strip() or "The program could not run."
        return make_result(
            False,
            output=completed.stdout.strip(),
            error=error_text,
            tests_failed=1,
            execution_time=execution_time,
            complexity_score=complexity_score,
        )

    output = completed.stdout.strip()
    if expected_output:
        passed = output == expected_output.strip()
        return make_result(
            True,
            output=output,
            tests_passed=1 if passed else 0,
            tests_failed=0 if passed else 1,
            execution_time=execution_time,
            complexity_score=complexity_score,
        )

    # A program that runs without an expected answer counts as one passed run.
    return make_result(
        True,
        output=output,
        tests_passed=1,
        execution_time=execution_time,
        complexity_score=complexity_score,
    )


def calculate_complexity(syntax_tree):
    """Estimate cyclomatic complexity by counting decision points."""

    score = 1
    decision_nodes = (ast.If, ast.For, ast.While, ast.AsyncFor, ast.IfExp)

    for node in ast.walk(syntax_tree):
        if isinstance(node, decision_nodes):
            score += 1
        elif isinstance(node, ast.BoolOp):
            # A statement such as "a and b and c" adds two decisions.
            score += max(1, len(node.values) - 1)
        elif isinstance(node, ast.Try):
            score += len(node.handlers)
        elif isinstance(node, ast.comprehension):
            score += 1 + len(node.ifs)

    return score


def compare_results(human_result, ai_result):
    """Turn the two sets of measurements into a plain-language summary."""

    human_score = (
        human_result["tests_passed"],
        -human_result["tests_failed"],
    )
    ai_score = (ai_result["tests_passed"], -ai_result["tests_failed"])

    details = []
    if human_score > ai_score:
        verdict = "Human-written code was better for this test"
        verdict_class = "human"
        details.append(
            "Correctness decided the result: human-written code produced the expected output."
        )
    elif ai_score > human_score:
        verdict = "AI-generated code was better for this test"
        verdict_class = "ai"
        details.append(
            "Correctness decided the result: AI-generated code produced the expected output."
        )
    elif human_result["tests_passed"] == 0:
        verdict = "Neither solution was better because both failed"
        verdict_class = "none"
        details.append("Neither program produced the expected output.")
    else:
        verdict = "Both solutions were equally correct"
        verdict_class = "tie"
        details.append("Both programs produced the expected output.")

    human_time = human_result["execution_time"]
    ai_time = ai_result["execution_time"]
    difference_ms = abs(human_time - ai_time) * 1000
    if difference_ms < 1:
        details.append("Their execution times were nearly the same.")
    elif human_time < ai_time:
        details.append(
            f"Human-written code ran {difference_ms:.3f} ms faster on this run."
        )
    else:
        details.append(
            f"AI-generated code ran {difference_ms:.3f} ms faster on this run."
        )

    human_complexity = human_result["complexity_score"]
    ai_complexity = ai_result["complexity_score"]
    if human_complexity < ai_complexity:
        details.append("Human-written code had the lower complexity score.")
    elif ai_complexity < human_complexity:
        details.append("AI-generated code had the lower complexity score.")
    else:
        details.append("Both programs had the same complexity score.")

    # When correctness is tied, use simplicity first and speed second to give a
    # useful overall verdict. Correctness always takes priority when it differs.
    if human_score == ai_score and human_result["tests_passed"] > 0:
        if human_complexity < ai_complexity:
            verdict = "Human-written code was better overall"
            verdict_class = "human"
        elif ai_complexity < human_complexity:
            verdict = "AI-generated code was better overall"
            verdict_class = "ai"
        elif difference_ms >= 1 and human_time < ai_time:
            verdict = "Human-written code performed better on this run"
            verdict_class = "human"
        elif difference_ms >= 1 and ai_time < human_time:
            verdict = "AI-generated code performed better on this run"
            verdict_class = "ai"

    return {
        "verdict": verdict,
        "verdict_class": verdict_class,
        "details": details,
    }


def make_result(
    success,
    output="",
    error="",
    tests_passed=0,
    tests_failed=0,
    execution_time=0.0,
    complexity_score=0,
):
    return {
        "success": success,
        "output": output,
        "error": error,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "execution_time": execution_time,
        "complexity_score": complexity_score,
    }
