"""
DevGuardian Architect — Structural Awareness & Diagramming
==========================================================
Analyzes project imports and file structure to generate:
1. Mermaid.js Flowcharts
2. Architecture Summaries
"""

import os
import re
from pathlib import Path
from devguardian.utils.file_reader import list_project_files


def _extract_internal_imports(file_path: Path, project_root: Path) -> list[str]:
    """Finds all internal imports (e.g., from devguardian.utils...) in a file."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except:
        return []

    # Matches: from devguardian.utils... import ... OR import devguardian...
    patterns = [
        r"^\s*from\s+(devguardian[\w.]+)\s+import",
        r"^\s*import\s+(devguardian[\w.]+)",
    ]

    internal_imports = []
    for pat in patterns:
        for match in re.findall(pat, content, re.MULTILINE):
            # Clean up: e.g. devguardian.utils.memory -> devguardian/utils/memory.py (abstractly)
            internal_imports.append(match)

    return list(set(internal_imports))


def generate_architecture_map(project_path: str) -> str:
    """
    Generates a Mermaid.js diagram representing the internal dependencies.
    """
    root = Path(project_path)
    all_files = list_project_files(project_path, max_files=200)

    # Map nodes: file_path -> simple_name
    # Example: devguardian/tools/infra.py -> tools.infra
    nodes = {}
    edges = []

    for f in all_files:
        fp = Path(f)
        rel_path = fp.relative_to(root)

        # We only care about .py files for the dependency map
        if fp.suffix != ".py" or "__pycache__" in str(rel_path):
            continue

        # Clean name for node: devguardian/utils/security.py -> utils.security
        node_id = str(rel_path).replace(os.sep, ".").replace(".py", "")
        if node_id.startswith("devguardian."):
            node_id = node_id.replace("devguardian.", "", 1)

        nodes[node_id] = node_id

        # Find who this file imports
        imports = _extract_internal_imports(fp, root)
        for imp in imports:
            # devguardian.utils.security -> utils.security
            target_id = imp.replace("devguardian.", "", 1) if imp.startswith("devguardian.") else imp
            edges.append((node_id, target_id))

    # Build Mermaid syntax
    mermaid = ["graph TD", "  subgraph DevGuardian_Core"]

    # Deduplicate edges and filter to only existing internal nodes
    seen_edges = set()
    for source, target in edges:
        if source in nodes and target in nodes and source != target:
            edge = f"    {source.replace('.', '_')} --> {target.replace('.', '_')}"
            if edge not in seen_edges:
                mermaid.append(edge)
                seen_edges.add(edge)

    mermaid.append("  end")

    # Add human-readable labels to make it look premium
    for nid in nodes:
        clean_id = nid.replace(".", "_")
        mermaid.append(f'  {clean_id}["{nid}"]')

    return "\n".join(mermaid)


def generate_technical_docs(project_path: str) -> str:
    """
    Generates a technical README snippet explaining the architecture.
    """
    from devguardian.utils.gemini_client import ask_gemini
    from devguardian.utils.file_reader import build_project_context

    ctx = build_project_context(project_path)
    prompt = (
        f"{ctx}\n\n"
        "Based on the project structure and context above, write a Deep Architecture Document. "
        "Explain: \n"
        "1. The Core Engine (How server.py orchestrates things)\n"
        "2. The Tool Matrix (What each tool in /tools does)\n"
        "3. The Agent Intelligence (How the swarm works)\n"
        "4. The Data Flow (How information moves from tools to agents)\n"
        "\nFormat in professional markdown with icons."
    )

    system = "You are a lead software architect. Provide a high-density, professional architecture summary."
    return ask_gemini(prompt, system_instruction=system)
