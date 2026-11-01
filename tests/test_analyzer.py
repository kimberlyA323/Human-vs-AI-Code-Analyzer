from analyzer import analyze_code


def test_valid_code_runs():
    result = analyze_code("name = input()\nprint('Hello', name)", "Kim\n")

    assert result["success"] is True
    assert result["output"] == "Hello Kim"


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
