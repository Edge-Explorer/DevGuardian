import pytest
from unittest.mock import patch
from devguardian.tools.debugger import debug_error


@patch("devguardian.tools.debugger.ask_gemini")
@patch("devguardian.tools.debugger.build_project_context")
def test_debug_error_with_project_path(mock_build_project_context, mock_ask_gemini):
    """
    Test debug_error function with project_path provided.
    Ensures project context is built and passed to ask_gemini.
    """
    mock_build_project_context.return_value = "Mocked Project Context"
    mock_ask_gemini.return_value = "Mocked Gemini Response"

    error_message = "TypeError: 'NoneType' object is not subscriptable"
    stack_trace = "File 'main.py', line 10, in <module>\n  print(x.lower())"
    code_snippet = "x = None\nprint(x.lower())"
    language = "Python"
    project_path = "/path/to/project"

    result = debug_error(error_message, stack_trace, code_snippet, language, project_path)

    assert result == "Mocked Gemini Response"
    mock_build_project_context.assert_called_once_with(project_path, code=code_snippet)
    mock_ask_gemini.assert_called_once()
    prompt = mock_ask_gemini.call_args[0][0]
    assert "Mocked Project Context" in prompt
    assert "TypeError: 'NoneType' object is not subscriptable" in prompt
    assert "File 'main.py', line 10, in <module>" in prompt
    assert "x = None\nprint(x.lower())" in prompt
    assert "Language: Python" in prompt
    assert mock_ask_gemini.call_args[0][1] is not None


@patch("devguardian.tools.debugger.ask_gemini")
@patch("devguardian.tools.debugger.build_project_context")
def test_debug_error_without_project_path(mock_build_project_context, mock_ask_gemini):
    """
    Test debug_error function without project_path.
    Ensures project context is not built.
    """
    mock_ask_gemini.return_value = "Mocked Gemini Response"

    error_message = "ValueError: invalid literal for int() with base 10: 'abc'"
    stack_trace = "File 'app.py', line 5, in <module>\n  num = int('abc')"
    code_snippet = "num = int('abc')"
    language = "Python"

    result = debug_error(error_message, stack_trace, code_snippet, language)

    assert result == "Mocked Gemini Response"
    mock_build_project_context.assert_not_called()
    mock_ask_gemini.assert_called_once()
    prompt = mock_ask_gemini.call_args[0][0]
    assert "ValueError: invalid literal for int() with base 10: 'abc'" in prompt
    assert "File 'app.py', line 5, in <module>" in prompt
    assert "num = int('abc')" in prompt
    assert "Language: Python" in prompt
    assert mock_ask_gemini.call_args[0][1] is not None


@patch("devguardian.tools.debugger.ask_gemini")
def test_debug_error_no_stack_trace_or_code(mock_ask_gemini):
    """
    Test debug_error function with only error_message.
    Ensures stack trace and code snippet are not included in prompt.
    """
    mock_ask_gemini.return_value = "Mocked Gemini Response"

    error_message = "KeyError: 'missing_key'"

    result = debug_error(error_message)

    assert result == "Mocked Gemini Response"
    mock_ask_gemini.assert_called_once()
    prompt = mock_ask_gemini.call_args[0][0]
    assert "KeyError: 'missing_key'" in prompt
    assert "Stack Trace" not in prompt
    assert "Code That Caused the Error" not in prompt
    assert mock_ask_gemini.call_args[0][1] is not None


@patch("devguardian.tools.debugger.ask_gemini")
def test_debug_error_empty_language(mock_ask_gemini):
    """
    Test debug_error function with empty language string.
    Ensures language hint is not added to the prompt.
    """
    mock_ask_gemini.return_value = "Mocked Gemini Response"

    error_message = "IndexError: list index out of range"
    stack_trace = "File 'data.py', line 20, in <module>\n  print(my_list[10])"
    code_snippet = "my_list = [1, 2, 3]\nprint(my_list[10])"

    result = debug_error(error_message, stack_trace, code_snippet, "")

    assert result == "Mocked Gemini Response"
    mock_ask_gemini.assert_called_once()
    prompt = mock_ask_gemini.call_args[0][0]
    assert "IndexError: list index out of range" in prompt
    assert "File 'data.py', line 20, in <module>" in prompt
    assert "my_list = [1, 2, 3]\nprint(my_list[10])" in prompt
    assert "Language:" not in prompt
    assert mock_ask_gemini.call_args[0][1] is not None