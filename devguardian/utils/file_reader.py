"""
File reader & smart project context builder for DevGuardian.

build_project_context() assembles a structured "Project DNA" string that is
prepended to every AI prompt, giving Gemini full awareness of:
  1. What the project IS         (README)
  2. What tools are available    (pyproject.toml / requirements.txt / package.json)
  3. How the project is laid out (file tree)
  4. What the code being analysed actually imports (import-aware retrieval)
  5. Key entry-point source files (server.py, main.py, __init__.py …)
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_IGNORE_DIRS: set[str] = {
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".git",
    "dist",
    "build",
    ".idea",
    ".vscode",
    ".mypy_cache",
    ".pytest_cache",
    ".eggs",
    ".tox",
    "htmlcov",
}

_SOURCE_EXTENSIONS: set[str] = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".html",
    ".css",
    ".scss",
    ".go",
    ".rs",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".rb",
    ".php",
}

# Priority order when looking for the README
_README_NAMES = ["README.md", "README.rst", "README.txt", "readme.md"]

# Priority order when looking for dependency declarations
_DEP_FILES = ["pyproject.toml", "requirements.txt", "package.json", "Cargo.toml", "go.mod"]

# Source files worth always including in context (if they exist)
_PRIORITY_FILENAMES = {"server.py", "main.py", "app.py", "index.py", "__init__.py"}


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def read_file(file_path: str) -> str:
    """Read a single file and return its full content as a string."""
    path = Path(file_path)
    if not path.exists():
        return f"File not found: {file_path}"
    if not path.is_file():
        return f"Path is not a file: {file_path}"
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"Could not read file: {exc}"


def _safe_read(path: Path, max_chars: int = 2000) -> str:
    """Read a file, capping at max_chars and noting if truncated."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    if len(text) > max_chars:
        return text[:max_chars] + f"\n... [{len(text) - max_chars} more chars truncated]"
    return text


def list_project_files(project_path: str, max_files: int = 100) -> list[str]:
    """Recursively list all source code files in a project directory."""
    root = Path(project_path)
    if not root.exists() or not root.is_dir():
        return []
    files: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _IGNORE_DIRS)
        for fname in filenames:
            fpath = Path(dirpath) / fname
            if fpath.suffix.lower() in _SOURCE_EXTENSIONS:
                files.append(str(fpath))
                if len(files) >= max_files:
                    return files
    return files


# ---------------------------------------------------------------------------
# File tree builder
# ---------------------------------------------------------------------------


def _build_file_tree(root: Path, max_entries: int = 80) -> str:
    """
    Build a compact, human-readable file tree string.
    Example output:
        devguardian/
          server.py
          tools/
            git_ops.py
            code_helper.py
    """
    lines: list[str] = [f"{root.name}/"]
    count = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _IGNORE_DIRS and not d.endswith(".egg-info"))
        rel = Path(dirpath).relative_to(root)
        depth = len(rel.parts)
        indent = "  " * depth

        # Print sub-folder name
        if depth > 0:
            lines.append(f"{'  ' * (depth - 1)}  {rel.parts[-1]}/")

        for fname in sorted(filenames):
            lines.append(f"{indent}  {fname}")
            count += 1
            if count >= max_entries:
                lines.append(f"{indent}  ... (more files not shown)")
                return "\n".join(lines)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Import-aware retrieval
# ---------------------------------------------------------------------------


def _extract_python_imports(code: str) -> list[str]:
    """
    Extract module dotpaths from Python import statements.
    Handles:
        from devguardian.utils.memory import init_db   → devguardian.utils.memory
        import devguardian.server                       → devguardian.server
    """
    patterns = [
        r"^\s*from\s+([\w.]+)\s+import",
        r"^\s*import\s+([\w.]+)",
    ]
    found: list[str] = []
    for pat in patterns:
        found.extend(re.findall(pat, code, re.MULTILINE))
    return list(dict.fromkeys(found))  # deduplicate, preserve order


def _resolve_import(module_path: str, project_root: Path) -> Path | None:
    """
    Try to map a Python dotted module path to a real file inside project_root.
    Returns None if not resolvable.
    """
    parts = module_path.split(".")
    # Try: devguardian/utils/memory.py
    candidate = project_root.joinpath(*parts).with_suffix(".py")
    if candidate.exists():
        return candidate
    # Try: devguardian/utils/memory/__init__.py
    pkg_init = project_root.joinpath(*parts) / "__init__.py"
    if pkg_init.exists():
        return pkg_init
    return None


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------


def build_project_context(
    project_path: str,
    code: str = "",
    max_chars: int = 14000,
) -> str:
    """
    Build a structured "Project DNA" context string for Gemini.

    The context is assembled in priority order so the most important
    information always fits within max_chars:

        1️⃣  README           — what the project IS and why it exists
        2️⃣  Dependency file  — the tech stack (libraries, versions)
        3️⃣  File tree        — the structural layout
        4️⃣  Imported files   — files directly referenced by the code being analysed
        5️⃣  Key entry points — server.py, main.py, __init__.py …

    Args:
        project_path : Root directory of the project.
        code         : The code snippet being analysed (enables import-aware lookup).
        max_chars    : Hard cap on total context size to stay within token limits.

    Returns:
        A markdown-formatted context string ready to be injected into a prompt.
    """
    root = Path(project_path)
    if not root.exists():
        return ""

    parts: list[str] = ["# 🛡️ DevGuardian — Project Context\n"]
    total_chars = len(parts[0])

    def _add(text: str) -> bool:
        nonlocal total_chars
        if total_chars + len(text) > max_chars:
            return False
        parts.append(text)
        total_chars += len(text)
        return True

    # ── 1. README ────────────────────────────────────────────────────────────
    for name in _README_NAMES:
        readme = root / name
        if readme.exists():
            content = _safe_read(readme, max_chars=2500)
            _add(f"\n## 📖 Project Overview (`{name}`)\n{content}\n")
            break

    # ── 2. Dependency file ───────────────────────────────────────────────────
    for dep_name in _DEP_FILES:
        dep = root / dep_name
        if dep.exists():
            content = _safe_read(dep, max_chars=1500)
            _add(f"\n## 📦 Dependencies (`{dep_name}`)\n```\n{content}\n```\n")
            break

    # ── 3. File tree ─────────────────────────────────────────────────────────
    tree = _build_file_tree(root)
    _add(f"\n## 📂 Project File Structure\n```\n{tree}\n```\n")

    # ── 4. Import-aware retrieval ─────────────────────────────────────────────
    if code.strip():
        imports = _extract_python_imports(code)
        resolved: list[tuple[str, Path]] = []
        for imp in imports:
            fp = _resolve_import(imp, root)
            if fp:
                resolved.append((imp, fp))

        if resolved:
            _add("\n## 🔗 Files Directly Imported by the Analysed Code\n")
            for imp, fp in resolved:
                rel = fp.relative_to(root)
                content = _safe_read(fp, max_chars=2000)
                ok = _add(f"\n### `{rel}` (imported as `{imp}`)\n```python\n{content}\n```\n")
                if not ok:
                    break  # context budget exhausted

    # ── 5. Key entry-point source files ──────────────────────────────────────
    # Walk all Python files, sort so priority names come first
    all_py: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _IGNORE_DIRS]
        for fname in filenames:
            fp = Path(dirpath) / fname
            if fp.suffix == ".py":
                all_py.append(fp)

    all_py.sort(key=lambda p: (0 if p.name in _PRIORITY_FILENAMES else 1, str(p)))

    if all_py:
        _add("\n## 📑 Key Source Files\n")
        for fp in all_py[:10]:
            rel = fp.relative_to(root)
            content = _safe_read(fp, max_chars=1200)
            ok = _add(f"\n### `{rel}`\n```python\n{content}\n```\n")
            if not ok:
                break  # budget exhausted

    return "".join(parts)
