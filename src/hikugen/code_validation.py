# ABOUTME: Validation utilities for Pydantic extraction code
# ABOUTME: AST-based validation for imports, function signatures, and security restrictions

import ast
import re
import sys
from typing import Optional, Set

# Pydantic extraction code validation constants
ALLOWED_THIRD_PARTY = {"requests", "bs4", "beautifulsoup4"}

def validate_code_complete(
    code: str, allowed_third_party: Optional[Set[str]] = ALLOWED_THIRD_PARTY
) -> tuple[bool, str]:
    """Complete validation of generated Pydantic extraction code.

    Validates imports, function signature, and parameter usage.

    Args:
        code: Python code to validate
        allowed_third_party: Set of allowed third-party module names

    Returns:
        Tuple of (is_valid, error_message). error_message is empty if valid.
    """
    # Check imports first
    is_valid, error_msg = validate_code_imports(code, allowed_third_party)
    if not is_valid:
        return False, error_msg

    # Check function usage
    is_valid, error_msg = validate_function_usage(code)
    if not is_valid:
        return False, error_msg

    return True, ""


def is_stdlib_module(module_name: str) -> bool:
    """Check if a module is part of Python's standard library.

    Uses Python's authoritative stdlib_module_names for reliable detection,
    with dangerous module filtering for security.

    Args:
        module_name: Name of the module to check

    Returns:
        True if module is safe stdlib, False for dangerous or non-stdlib modules
    """
    dangerous_modules = {
        "os",
        "subprocess",
        "sys",
        "importlib",
        "runpy",
        "exec",
        "eval",
        "compile",
        "__import__",
        "open",
        "file",
        "execfile",
        "input",
        "raw_input",
    }

    if module_name in dangerous_modules:
        return False

    # Use Python's authoritative standard library module list (Python 3.10+)
    if hasattr(sys, "stdlib_module_names"):
        return module_name in sys.stdlib_module_names

    # Fallback for older Python versions - check builtins only
    return module_name in sys.builtin_module_names


def validate_function_usage(code: str) -> tuple[bool, str]:
    """Validate that code uses correct function signature and parameter names.

    Checks for correct function signature and proper parameter usage to catch
    common LLM mistakes like using 'htmlContent' instead of 'html_content'.

    Args:
        code: Python code to validate

    Returns:
        Tuple of (is_valid, error_message). error_message is empty if valid.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    # Check for the required function
    function_found = False
    correct_parameter = False

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "extract_data":
            function_found = True

            # Check function signature
            if len(node.args.args) != 1:
                return (
                    False,
                    "Function extract_data must have exactly one parameter",
                )

            param_name = node.args.args[0].arg
            if param_name == "html_content":
                correct_parameter = True
            else:
                return False, f"Parameter must be 'html_content', not '{param_name}'"

    if not function_found:
        return False, "Function 'extract_data' not found"

    if not correct_parameter:
        return False, "Function must use parameter name 'html_content'"

    return True, ""


def validate_code_imports(
    code: str, allowed_third_party: Optional[Set[str]] = None
) -> tuple[bool, str]:
    """Validate that code only uses allowed imports.

    Checks that all imports are either safe Python standard library modules
    or explicitly allowed third-party packages.

    Args:
        code: Python code to validate
        allowed_third_party: Set of allowed third-party module names

    Returns:
        Tuple of (is_valid, error_message). error_message is empty if valid.
    """
    if allowed_third_party is None:
        allowed_third_party = ALLOWED_THIRD_PARTY

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_parts = alias.name.split(".")
                base_module = module_parts[0]

                if (
                    not is_stdlib_module(base_module)
                    and base_module not in allowed_third_party
                ):
                    return False, f"Forbidden import: {alias.name}"

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_parts = node.module.split(".")
                base_module = module_parts[0]

                if (
                    not is_stdlib_module(base_module)
                    and base_module not in allowed_third_party
                ):
                    return False, f"Forbidden import: {node.module}"

    return True, ""
