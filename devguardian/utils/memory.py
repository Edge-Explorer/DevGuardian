"""
DevGuardian Semantic Memory
============================
Handles persistence of "lessons learned" and project preferences.
Uses a simple JSON-based vector-like store for local project memory.
"""

import json
from pathlib import Path
from datetime import datetime


class ProjectMemory:
    def __init__(self, project_path: str):
        self.root = Path(project_path)
        self.memory_path = self.root / ".devguardian_memory.json"
        self.data = self._load()

    def _load(self) -> dict:
        if self.memory_path.exists():
            try:
                return json.loads(self.memory_path.read_text(encoding="utf-8"))
            except:
                return {"preferences": [], "lessons": []}
        return {"preferences": [], "lessons": []}

    def save(self):
        self.memory_path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def add_preference(self, pref: str):
        """Add a persistent coding style preference."""
        if pref not in self.data["preferences"]:
            self.data["preferences"].append(pref)
            self.save()

    def add_lesson(self, task: str, finding: str):
        """Record a lesson learned from a specific task."""
        self.data["lessons"].append({"timestamp": datetime.now().isoformat(), "task": task, "finding": finding})
        # Keep only last 10 lessons to prevent context bloat
        self.data["lessons"] = self.data["lessons"][-10:]
        self.save()

    def get_context_string(self) -> str:
        """Returns a formatted string of memory for LLM context."""
        parts = []
        if self.data["preferences"]:
            parts.append("### User Preferences\n- " + "\n- ".join(self.data["preferences"]))

        if self.data["lessons"]:
            parts.append("### Recent Lessons Learned")
            for l in self.data["lessons"]:
                parts.append(f"- Task: {l['task']}\n  Lesson: {l['finding']}")

        return "\n\n".join(parts) if parts else "No specific project memory yet."
