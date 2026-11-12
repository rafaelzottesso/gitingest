"""Helpers that reduce the size (and token count) of ingested file contents."""

from __future__ import annotations

import ast
import io
import re
import tokenize
from pathlib import PurePosixPath

_BLANK_RUN_RE = re.compile(r"\n{3,}")

# Files where trailing spaces / indentation can carry meaning: only trailing-whitespace trimming is skipped or limited.
_PROSE_SUFFIXES = {".md", ".markdown", ".rst", ".txt", ".diff", ".patch", ".tsv", ".csv"}

# Languages with C-style comments (// and /* */)
_C_STYLE_SUFFIXES = {
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".java", ".c", ".h", ".cc", ".cpp", ".hpp", ".cs", ".go",
    ".rs", ".swift", ".kt", ".kts", ".scala", ".dart", ".php", ".css", ".scss", ".less",
}  # fmt: skip
# Languages where a line starting with "#" is a comment
_HASH_SUFFIXES = {".sh", ".bash", ".zsh", ".rb", ".yml", ".yaml", ".toml", ".r", ".pl", ".ps1"}
_HASH_NAMES = {"dockerfile", "makefile"}

# Files whose indentation is safe to shrink from 4 to 2 spaces
_INDENT_SUFFIXES = (_C_STYLE_SUFFIXES - {".css", ".scss", ".less"}) | {".py", ".json", ".xml", ".html", ".vue"}


def compress_content(text: str, filename: str, *, compact_whitespace: bool, strip_comments: bool) -> str:
    """Apply the requested compressions to the text of a single file.

    Parameters
    ----------
    text : str
        Content of the file.
    filename : str
        Path or name of the file (used to pick language rules).
    compact_whitespace : bool
        Trim trailing spaces, collapse blank-line runs and shrink 4-space indentation to 2 spaces.
    strip_comments : bool
        Remove comments (and Python docstrings) for the languages that are supported.

    Returns
    -------
    str
        The compressed text. Placeholders such as ``[Binary file]`` are returned unchanged.

    """
    if text.startswith(("[Binary file]", "[Empty file]", "Error")):
        return text

    path = PurePosixPath(filename.replace("\\", "/"))
    suffix, name = path.suffix.lower(), path.name.lower()

    if strip_comments:
        text = _strip_comments(text, suffix, name)
    if compact_whitespace:
        text = _compact_whitespace(text, suffix)
    return text


def _compact_whitespace(text: str, suffix: str) -> str:
    lines = text.replace("\r\n", "\n").split("\n")

    if suffix not in {".md", ".markdown"}:
        lines = [line.rstrip() for line in lines]

    if suffix in _INDENT_SUFFIXES:
        indents = [len(line) - len(line.lstrip(" ")) for line in lines if line.strip() and not line.startswith("\t")]
        # Only shrink when every indented line uses a multiple of 4 spaces (consistent 4-space style)
        if any(indents) and all(n % 4 == 0 for n in indents):
            lines = [
                " " * ((len(line) - len(line.lstrip(" "))) // 2) + line.lstrip(" ") if line.strip() else line
                for line in lines
            ]

    return _BLANK_RUN_RE.sub("\n\n", "\n".join(lines)).strip("\n") + "\n"


def _strip_comments(text: str, suffix: str, name: str) -> str:
    try:
        if suffix == ".py":
            return _strip_python(text)
        if suffix in _C_STYLE_SUFFIXES:
            return _strip_c_style(text, allow_single_quote=suffix != ".rs")
        if suffix in _HASH_SUFFIXES or name in _HASH_NAMES:
            return _strip_hash_lines(text)
    except (SyntaxError, tokenize.TokenError, IndentationError, ValueError):
        pass  # leave the file untouched if it cannot be parsed safely
    return text


def _strip_python(text: str) -> str:
    """Remove ``#`` comments and docstrings from Python source."""
    tree = ast.parse(text)  # raises SyntaxError for invalid code -> caller keeps original
    lines = text.split("\n")

    # Docstrings: replace by ``pass`` when they are the only statement, otherwise blank the lines.
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        first = node.body[0] if node.body else None
        if not (
            isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str)
        ):
            continue
        start, end = first.lineno - 1, first.end_lineno - 1
        if first.col_offset and lines[start][: first.col_offset].strip():
            continue  # docstring shares a line with other code (e.g. ``def f(): "doc"``)
        replacement = " " * first.col_offset + "pass" if len(node.body) == 1 else ""
        lines[start] = replacement
        for i in range(start + 1, end + 1):
            lines[i] = ""

    # Comments (tokenize is string-aware, so ``#`` inside strings is safe)
    source = "\n".join(lines)
    cut: dict[int, int] = {}
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT:
            row, col = tok.start
            cut[row - 1] = col
    out = source.split("\n")
    for row, col in cut.items():
        if row == 0 and out[0].startswith("#!"):
            continue  # keep shebang
        out[row] = out[row][:col].rstrip()

    # Drop the blank line left right after a block opener (e.g. where a docstring or comment was)
    cleaned: list[str] = []
    for line in out:
        if not line.strip() and cleaned and cleaned[-1].rstrip().endswith(":"):
            continue
        cleaned.append(line)

    result = "\n".join(cleaned)
    ast.parse(result)  # safety net: never return code that no longer parses
    return result


def _strip_c_style(text: str, *, allow_single_quote: bool) -> str:
    """Remove ``//`` and ``/* */`` comments while respecting string literals."""
    out: list[str] = []
    i, n = 0, len(text)
    quotes = "\"`'" if allow_single_quote else '"`'
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if ch in quotes:
            j = i + 1
            while j < n and text[j] != ch:
                j += 2 if text[j] == "\\" else 1
                if ch != "`" and j < n and text[j] == "\n":
                    break  # unterminated single-line string: bail out of the literal
            out.append(text[i : j + 1])
            i = j + 1
        elif ch == "/" and nxt == "/":
            if i > 0 and text[i - 1] == ":":  # URL such as https://
                out.append(ch)
                i += 1
                continue
            while i < n and text[i] != "\n":
                i += 1
        elif ch == "/" and nxt == "*":
            end = text.find("*/", i + 2)
            if end == -1:
                out.append(text[i:])
                break
            i = end + 2
        else:
            out.append(ch)
            i += 1
    return "\n".join(line.rstrip() for line in "".join(out).split("\n"))


def _strip_hash_lines(text: str) -> str:
    """Remove full-line ``#`` comments (keeps the shebang)."""
    lines = text.split("\n")
    return "\n".join(
        line for i, line in enumerate(lines) if not line.lstrip().startswith("#") or (i == 0 and line.startswith("#!"))
    )
