import ast

from analyzer import analyze_code, calculate_complexity, compare_results


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

    assert "Human-written code" in summary["headline"]
    assert any("AI-generated code ran" in line for line in summary["details"])
