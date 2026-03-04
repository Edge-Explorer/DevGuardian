"""
File reader utility — reads project files to give Gemini context.
"""

import os
from pathlib import Path

# Extensions we consider "readable source code"
_SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss",
    ".json", ".yaml", ".yml", ".toml", ".md", ".txt", ".env.example",
    ".sh", ".bat", ".ps1", ".c", ".cpp", ".h", ".java", ".go", ".rs",
    ".sql", ".graphql", ".xml",
}

_IGNORE_DIRS = {
    ".venv", "venv", "__pycache__", "node_modules", ".git",
    "dist", "build", ".idea", ".vscode",
}


def read_file(file_path: str) -> str:
    """Read a single file and return its content as a string."""
    path = Path(file_path)
    if not path.exists():
        return f"❌ File not found: {file_path}"
    if not path.is_file():
        return f"❌ Path is not a file: {file_path}"
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"❌ Could not read file: {exc}"


def list_project_files(project_path: str, max_files: int = 50) -> list[str]:
    """
    Recursively list all source code files in a project directory.
    Returns a list of absolute path strings.
    """
    root = Path(project_path)
    if not root.exists() or not root.is_dir():
        return []

    files: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip ignored directories in-place
        dirnames[:] = [d for d in dirnames if d not in _IGNORE_DIRS]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            if fpath.suffix.lower() in _SOURCE_EXTENSIONS:
                files.append(str(fpath))
                if len(files) >= max_files:
                    return files
    return files


def build_project_context(project_path: str, max_chars: int = 8000) -> str:
    """
    Gather a snippet of each source file and return one big context string
    suitable for pasting into a Gemini prompt.
    """
    files = list_project_files(project_path)
    if not files:
        return "No source files found in the given path."

    chunks: list[str] = []
    total = 0
    for fp in files:
        content = read_file(fp)
        header = f"\n\n### File: {fp}\n```\n"
        footer = "\n```"
        snippet = content[:1500]  # cap each file to keep prompt manageable
        entry = header + snippet + footer
        if total + len(entry) > max_chars:
            break
        chunks.append(entry)
        total += len(entry)

    return "".join(chunks)
