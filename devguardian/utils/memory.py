"""
💾 DevGuardian Memory Utility
Manages SQLite persistence for LangGraph agents.
"""

import aiosqlite
import os
from pathlib import Path

DB_PATH = Path("devguardian.db")

async def init_db():
    """Ensure the memory database and necessary tables exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Checkpoint table for LangGraph (Standard schema)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                thread_id TEXT NOT NULL,
                checkpoint_id TEXT NOT NULL,
                parent_id TEXT,
                checkpoint BLOB NOT NULL,
                metadata BLOB NOT NULL,
                PRIMARY KEY (thread_id, checkpoint_id)
            )
        """)
        
        # Knowledge Journal (for the agent's long-term project insights)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                topic TEXT,
                insight TEXT,
                tags TEXT
            )
        """)
        await db.commit()

async def add_insight(topic: str, insight: str, tags: str = ""):
    """Record a project-specific insight for future reference."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO journal (topic, insight, tags) VALUES (?, ?, ?)",
            (topic, insight, tags)
        )
        await db.commit()

async def get_insights(topic: str = None):
    """Retrieve recorded insights."""
    async with aiosqlite.connect(DB_PATH) as db:
        if topic:
            async with db.execute("SELECT * FROM journal WHERE topic LIKE ?", (f"%{topic}%",)) as cursor:
                return await cursor.fetchall()
        async with db.execute("SELECT * FROM journal ORDER BY timestamp DESC") as cursor:
            return await cursor.fetchall()
