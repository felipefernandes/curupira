import aiosqlite
import logging
from datetime import datetime
import os

import shutil
import pathlib

# Define path for SQLite DB
# Use a dedicated data directory to avoid git conflicts
DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
DB_FILE = DATA_DIR / "curupira.db"

class MemoryManager:
    def __init__(self, db_path=None):
        self.logger = logging.getLogger("MemoryManager")
        
        # Ensure data directory exists
        if not DATA_DIR.exists():
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            
        # Check for legacy DB at root and migrate if needed
        legacy_db = pathlib.Path(__file__).parent.parent / "curupira.db"
        if legacy_db.exists() and not (db_path or DB_FILE).exists():
            self.logger.warning(f"Migrating legacy database from {legacy_db} to {DB_FILE}")
            try:
                shutil.move(str(legacy_db), str(DB_FILE))
                self.logger.info("Database migration successful.")
            except Exception as e:
                self.logger.error(f"Failed to migrate database: {e}")

        self.db_path = db_path or str(DB_FILE)

    async def init_db(self):
        """Initializes the database tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    first_seen DATETIME
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    key TEXT,
                    value TEXT,
                    created_at DATETIME,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    role TEXT,
                    content TEXT,
                    timestamp DATETIME,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message TEXT,
                    remind_at DATETIME,
                    created_at DATETIME,
                    status TEXT DEFAULT 'PENDING',
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )
            """)
            await db.commit()
            self.logger.info("Database initialized.")

    async def add_user(self, user_id, username, full_name):
        """Adds or updates a user."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR IGNORE INTO users (user_id, username, full_name, first_seen)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, full_name, datetime.now()))
            # Update info if exists (optional, keeping it simple for now)
            await db.commit()

    async def save_fact(self, user_id, key, value):
        """Saves a long-term fact."""
        async with aiosqlite.connect(self.db_path) as db:
            # Check if exists first to update or insert
            cursor = await db.execute("SELECT id FROM facts WHERE user_id = ? AND key = ?", (user_id, key))
            row = await cursor.fetchone()
            if row:
                await db.execute("UPDATE facts SET value = ? WHERE id = ?", (value, row[0]))
            else:
                await db.execute("""
                    INSERT INTO facts (user_id, key, value, created_at)
                    VALUES (?, ?, ?, ?)
                """, (user_id, key, value, datetime.now()))
            await db.commit()

    async def get_fact_value(self, user_id, key):
        """Retrieves a specific fact value."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT value FROM facts WHERE user_id = ? AND key = ?", (user_id, key)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def get_facts(self, user_id):
        """Retrieves all facts for a user as a formatted text list."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT key, value FROM facts WHERE user_id = ?", (user_id,)) as cursor:
                rows = await cursor.fetchall()
                if not rows:
                    return ""
                return "\n".join([f"- {key}: {value}" for key, value in rows])

    async def log_message(self, user_id, role, content):
        """Logs a message to the conversation history."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO conversations (user_id, role, content, timestamp)
                VALUES (?, ?, ?, ?)
            """, (user_id, role, content, datetime.now()))
            await db.commit()

    async def get_context(self, user_id, limit=10):
        """Retrieves the last N messages for context injection."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT role, content FROM conversations 
                WHERE user_id = ? 
                ORDER BY id DESC LIMIT ?
            """, (user_id, limit)) as cursor:
                rows = await cursor.fetchall()
                # Reverse to correct chronological order
                history = reversed(rows)
                formatted_history = []
                for role, content in history:
                     role_name = "User" if role == "user" else "Model"
                     formatted_history.append(f"{role_name}: {content}")
                return "\n".join(formatted_history)
