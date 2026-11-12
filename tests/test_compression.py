"""Tests for the token-saving compression helpers."""

import ast

from gitingest.utils.compression import compress_content

PY = '''#!/usr/bin/env python
"""Module doc."""
import os  # trailing


def f(x):
    """Docstring."""
    # comment
    s = "a # not comment"
    return s


class A:
    """only doc"""
'''


def test_python_comments_and_docstrings_removed() -> None:
    """Comments/docstrings go away, strings stay, result is still valid Python."""
    out = compress_content(PY, "a.py", compact_whitespace=False, strip_comments=True)
    assert "Docstring" not in out
    assert "# comment" not in out
    assert "# trailing" not in out
    assert "a # not comment" in out
    assert out.startswith("#!/usr/bin/env python")
    ast.parse(out)


def test_c_style_comments_keep_urls_and_strings() -> None:
    """``//`` inside strings or URLs must survive."""
    src = 'const u = "http://x.com"; // hi\n/* block */\nconst v = 1;\n'
    out = compress_content(src, "a.js", compact_whitespace=False, strip_comments=True)
    assert "http://x.com" in out
    assert "hi" not in out
    assert "block" not in out


def test_compact_whitespace() -> None:
    """Trailing spaces trimmed, blank runs collapsed, 4-space indent halved."""
    src = "def f():   \n\n\n\n    return 1\n"
    out = compress_content(src, "a.py", compact_whitespace=True, strip_comments=False)
    assert out == "def f():\n\n  return 1\n"


def test_invalid_python_is_left_untouched() -> None:
    """Unparseable code is returned as is when stripping comments."""
    src = "def (:\n  # c\n"
    assert compress_content(src, "a.py", compact_whitespace=False, strip_comments=True) == src


def test_placeholders_unchanged() -> None:
    """Binary / empty placeholders are not modified."""
    assert compress_content("[Binary file]", "a.png", compact_whitespace=True, strip_comments=True) == "[Binary file]"
