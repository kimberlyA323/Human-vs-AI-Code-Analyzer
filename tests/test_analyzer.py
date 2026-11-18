import ast

from analyzer import (
    analyze_code,
    analyze_test_cases,
    calculate_complexity,
    compare_results,
)


def test_valid_code_runs():
    result = analyze_code("name = input()\nprint('Hello', name)", "Kim\n")

    assert result["success"] is True
    assert result["output"] == "Hello Kim"
    assert result["execution_time"] > 0


def test_syntax_error_is_returned():
    result = analyze_code("print('missing parenthesis'")

    assert result["success"] is False
    assert "Syntax error" in result["error"]


def test_output_is_counted_as_passed():
    result = analyze_code("print(4)", expected_output="4")

    assert result["tests_passed"] == 1
    assert result["tests_failed"] == 0


def test_wrong_output_is_counted_as_failed():
    result = analyze_code("print(5)", expected_output="4")

    assert result["tests_passed"] == 0
    assert result["tests_failed"] == 1


def test_complexity_counts_decisions():
    syntax_tree = ast.parse(
        """
def choose(value):
    if value > 10:
        return 'large'
    for number in range(value):
        if number == 3:
            return 'three'
    return 'small'
"""
    )

    assert calculate_complexity(syntax_tree) == 4


def test_analysis_includes_complexity():
    result = analyze_code("if True:\n    print('yes')")

    assert result["complexity_score"] == 2


def test_comparison_summary_explains_the_outcome():
    human_result = {
        "tests_passed": 1,
        "tests_failed": 0,
        "execution_time": 0.05,
        "complexity_score": 2,
    }
    ai_result = {
        "tests_passed": 0,
        "tests_failed": 1,
        "execution_time": 0.04,
        "complexity_score": 1,
    }

    summary = compare_results(human_result, ai_result)

    assert "Human-written code was better" in summary["verdict"]
    assert any("AI-generated code ran" in line for line in summary["details"])


def test_program_runs_against_multiple_test_cases():
    result = analyze_test_cases(
        "number = int(input())\nprint(number * 2)",
        [
            {"input": "2", "expected_output": "4"},
            {"input": "5", "expected_output": "10"},
            {"input": "0", "expected_output": "0"},
        ],
    )

    assert result["tests_passed"] == 3
    assert result["tests_failed"] == 0
    assert len(result["test_details"]) == 3


def test_multiple_test_cases_show_the_failed_case():
    result = analyze_test_cases(
        "number = int(input())\nprint(number + 1)",
        [
            {"input": "2", "expected_output": "3"},
            {"input": "5", "expected_output": "10"},
        ],
    )

    assert result["tests_passed"] == 1
    assert result["tests_failed"] == 1
    assert result["test_details"][1]["passed"] is False


def test_runtime_error_is_reported_without_crashing():
    result = analyze_test_cases(
        "number = int(input())\nprint(10 / number)",
        [{"input": "0", "expected_output": "0"}],
    )

    assert result["tests_failed"] == 1
    assert "ZeroDivisionError" in result["error"]


def test_multiline_output_matches_browser_line_endings():
    result = analyze_code("print('café\\nsecond line')", expected_output="café\r\nsecond line")

    assert result["tests_passed"] == 1


def test_invalid_utf8_fails_the_case():
    result = analyze_code(
        "import sys\nsys.stdout.buffer.write(b'\\xff')",
        expected_output=r"\xff",
    )

    assert result["tests_failed"] == 1
    assert "UTF-8" in result["error"]


def test_equal_partial_results_stay_tied():
    human_result = {
        "tests_passed": 1,
        "tests_failed": 2,
        "execution_time": 0.01,
        "complexity_score": 1,
    }
    ai_result = {**human_result, "complexity_score": 3}

    summary = compare_results(human_result, ai_result)

    assert summary["verdict_class"] == "tie"
    assert "passed 1 of 3 cases" in summary["details"][0]


def test_single_run_timing_does_not_break_a_correctness_and_complexity_tie():
    human_result = {
        "tests_passed": 2,
        "tests_failed": 0,
        "execution_time": 0.01,
        "complexity_score": 1,
    }
    ai_result = {**human_result, "execution_time": 0.04}

    summary = compare_results(human_result, ai_result)

    assert summary["verdict_class"] == "tie"
    assert any("Human-written code ran" in detail for detail in summary["details"])
