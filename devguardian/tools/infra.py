# 🛡️ DevGuardian Project — Core Module
"""
🐳 Infrastructure Generator
=============================
Generates production-ready infrastructure files tailored to the project:
  • Dockerfile + docker-compose.yml  →  `dockerize()`
  • GitHub Actions CI/CD workflow    →  `generate_ci()`
Uses build_project_context() to understand the tech stack automatically.
"""

from pathlib import Path
from devguardian.utils.gemini_client import ask_gemini
from devguardian.utils.file_reader import build_project_context


_DOCKER_SYSTEM = (
    "You are a senior DevOps engineer. "
    "Generate a production-grade Dockerfile and docker-compose.yml for the given project. "
    "Use multi-stage builds where appropriate. "
    "Output EXACTLY two files separated by the delimiter '### docker-compose.yml ###'. "
    "No markdown fences, no explanations — just the raw file contents."
)

_CI_SYSTEM = (
    "You are a senior DevOps engineer. "
    "Generate a GitHub Actions CI/CD workflow YAML file for the given project. "
    "Include: linting, testing, and (optionally) Docker build steps. "
    "Output ONLY valid YAML — no markdown fences, no explanations."
)


def _strip_fences(text: str) -> str:
    """Remove accidental markdown code fences."""
    lines = [l for l in text.splitlines() if not l.strip().startswith("```")]
    return "\n".join(lines).strip()


def dockerize(project_path: str) -> str:
    """
    Analyze the project and generate:
      - Dockerfile  → project_path/Dockerfile
      - docker-compose.yml → project_path/docker-compose.yml

    Returns a summary of what was generated.
    """
    root = Path(project_path)
    ctx = build_project_context(project_path)

    prompt = (
        f"{ctx}\n\n"
        "Generate a Dockerfile and docker-compose.yml for this project. "
        "Infer the language, runtime, and start command from the context above. "
        "Separate the two files with the exact line:\n### docker-compose.yml ###"
    )

    raw = ask_gemini(prompt, system_instruction=_DOCKER_SYSTEM)
    raw = _strip_fences(raw)

    # Split on the delimiter
    delimiter = "### docker-compose.yml ###"
    if delimiter in raw:
        dockerfile_content, compose_content = raw.split(delimiter, 1)
    else:
        # Best-effort: put everything in Dockerfile
        dockerfile_content = raw
        compose_content = "version: '3.8'\nservices:\n  app:\n    build: .\n    ports:\n      - '8000:8000'\n"

    dockerfile_path = root / "Dockerfile"
    compose_path = root / "docker-compose.yml"

    dockerfile_path.write_text(dockerfile_content.strip(), encoding="utf-8")
    compose_path.write_text(compose_content.strip(), encoding="utf-8")

    return (
        f"## 🐳 Dockerization Complete!\n\n"
        f"Generated files in `{project_path}`:\n"
        f"- ✅ `Dockerfile`\n"
        f"- ✅ `docker-compose.yml`\n\n"
        f"### Dockerfile Preview\n```dockerfile\n{dockerfile_content.strip()[:800]}\n```\n\n"
        f"### docker-compose.yml Preview\n```yaml\n{compose_content.strip()[:400]}\n```"
    )


def generate_ci(project_path: str, deploy_target: str = "") -> str:
    """
    Analyze the project and generate a GitHub Actions CI workflow.
    Writes to: .github/workflows/ci.yml

    Args:
        project_path:  Absolute path to the project root.
        deploy_target: Optional deployment target hint (e.g., 'docker', 'heroku', 'railway').
    """
    root = Path(project_path)
    ctx = build_project_context(project_path)

    deploy_hint = f"\nDeployment target: {deploy_target}" if deploy_target else ""
    prompt = (
        f"{ctx}{deploy_hint}\n\n"
        "Generate a complete GitHub Actions CI/CD workflow YAML. "
        "Infer the correct test commands and linting tools from the project context. "
        "The workflow should trigger on push and PR to main branch."
    )

    yaml_content = ask_gemini(prompt, system_instruction=_CI_SYSTEM)
    yaml_content = _strip_fences(yaml_content)

    workflow_dir = root / ".github" / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    ci_file = workflow_dir / "ci.yml"
    ci_file.write_text(yaml_content, encoding="utf-8")

    return (
        f"## 🚀 CI/CD Workflow Generated!\n\n"
        f"Written to: `.github/workflows/ci.yml`\n\n"
        f"```yaml\n{yaml_content[:1200]}\n```\n"
        + ("*(truncated — see file for full content)*" if len(yaml_content) > 1200 else "")
    )


def generate_gitignore(project_path: str, include_env: bool = False) -> str:
    """
    Analyze the project and generate a tailored .gitignore.
    """
    from devguardian.utils.security import generate_smart_gitignore

    content = generate_smart_gitignore(project_path, include_env=include_env)
    root = Path(project_path)
    gitignore_path = root / ".gitignore"

    # Backup if it exists
    if gitignore_path.exists():
        backup = gitignore_path.with_suffix(".gitignore.bak")
        gitignore_path.rename(backup)

    gitignore_path.write_text(content, encoding="utf-8")

    return (
        f"## 🛡️ Smart .gitignore Generated!\n\n"
        f"Project: `{project_path}`\n"
        f"- ✅ Tailored to project structure\n"
        f"- ✅ Sensitive file check: {'Enabled' if include_env else 'Manual review requested'}\n\n"
        f"```text\n{content[:800]}\n```\n" + ("*(truncated — see file for full content)*" if len(content) > 800 else "")
    )
