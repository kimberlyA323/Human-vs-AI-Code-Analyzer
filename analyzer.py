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
                [sys.executable, "-I", "-X", "utf8", str(program_path)],
                input=test_input.encode("utf-8"),
                capture_output=True,
                cwd=temporary_directory,
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

    try:
        output = completed.stdout.decode("utf-8")
        invalid_output = False
    except UnicodeDecodeError:
        output = completed.stdout.decode("utf-8", errors="backslashreplace")
        invalid_output = True

    output = normalize_output(output)
    error_text = ""
    if completed.returncode != 0:
        error_text = (
            completed.stderr.decode("utf-8", errors="backslashreplace").strip()
            or "The program could not run."
        )
    elif invalid_output:
        error_text = "The program produced output that is not valid UTF-8 text."

    if error_text:
        return make_result(
            False,
            output=output,
            error=error_text,
            tests_failed=1,
            execution_time=execution_time,
            complexity_score=complexity_score,
        )

    if expected_output:
        passed = output == normalize_output(expected_output)
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


def analyze_test_cases(source_code, test_cases):
    """Run the same program once for every supplied input and expected output."""

    case_results = []
    analysis_results = []
    for case_number, test_case in enumerate(test_cases, start=1):
        result = analyze_code(
            source_code,
            test_case["input"],
            test_case["expected_output"],
        )
        analysis_results.append(result)
        case_results.append(
            {
                "number": test_case.get("number", case_number),
                "input": test_case["input"],
                "expected_output": test_case["expected_output"],
                "output": result["output"],
                "passed": result["tests_passed"] == 1,
                "error": result["error"],
            }
        )

    if not case_results:
        return {
            **make_result(False, error="No test cases were provided."),
            "test_details": [],
        }

    tests_passed = sum(case["passed"] for case in case_results)
    tests_failed = len(case_results) - tests_passed
    errors = [
        f"Case {case['number']}: {case['error']}"
        for case in case_results
        if case["error"]
    ]
    outputs = [
        f"Case {case['number']}: {case['output'] or 'No output'}"
        for case in case_results
    ]

    return {
        "success": not errors,
        "output": "\n".join(outputs),
        "error": "\n".join(errors),
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "execution_time": sum(
            result["execution_time"] for result in analysis_results
        ),
        "complexity_score": analysis_results[0]["complexity_score"],
        "test_details": case_results,
    }


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


def normalize_output(output):
    return output.replace("\r\n", "\n").replace("\r", "\n").strip()


def compare_results(human_result, ai_result):
    """Turn the two sets of measurements into a plain-language summary."""

    human_passed = human_result["tests_passed"]
    ai_passed = ai_result["tests_passed"]

    details = [
        f"Human-written code passed {human_passed} of "
        f"{human_passed + human_result['tests_failed']} cases.",
        f"AI-generated code passed {ai_passed} of "
        f"{ai_passed + ai_result['tests_failed']} cases.",
    ]
    if human_passed > ai_passed:
        verdict = "Human-written code was better on these tests"
        verdict_class = "human"
    elif ai_passed > human_passed:
        verdict = "AI-generated code was better on these tests"
        verdict_class = "ai"
    elif human_passed == 0:
        verdict = "Neither solution passed a test case"
        verdict_class = "none"
    elif human_result["tests_failed"] or ai_result["tests_failed"]:
        verdict = "Both solutions passed the same number of cases"
        verdict_class = "tie"
    else:
        verdict = "Both solutions were equally correct"
        verdict_class = "tie"

    human_time = human_result["execution_time"]
    ai_time = ai_result["execution_time"]
    if all(result.get("success", True) for result in (human_result, ai_result)):
        difference_ms = abs(human_time - ai_time) * 1000
        if difference_ms < 1:
            details.append("Their measured times differed by less than 1 ms.")
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
    if human_complexity and ai_complexity:
        if human_complexity < ai_complexity:
            details.append("Human-written code had the lower complexity score.")
        elif ai_complexity < human_complexity:
            details.append("AI-generated code had the lower complexity score.")
        else:
            details.append("Both programs had the same complexity score.")

        both_passed_all = (
            human_passed == ai_passed
            and human_passed > 0
            and not (human_result["tests_failed"] or ai_result["tests_failed"])
        )
        if both_passed_all and human_complexity < ai_complexity:
            verdict = "Human-written code passed all tests with lower complexity"
            verdict_class = "human"
        elif both_passed_all and ai_complexity < human_complexity:
            verdict = "AI-generated code passed all tests with lower complexity"
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
        "output": output.replace("\x00", r"\x00"),
        "error": error.replace("\x00", r"\x00"),
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "execution_time": execution_time,
        "complexity_score": complexity_score,
    }
