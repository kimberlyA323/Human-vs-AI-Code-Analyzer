from analyzer import analyze_code


def test_valid_code_runs():
    result = analyze_code("name = input()\nprint('Hello', name)", "Kim\n")

    assert result["success"] is True
    assert result["output"] == "Hello Kim"


def test_syntax_error_is_returned():
    result = analyze_code("print('missing parenthesis'")

    assert result["success"] is False
    assert "Syntax error" in result["error"]
