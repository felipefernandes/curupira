import aiosqlite
import logging
from datetime import datetime
import os

# Define path for SQLite DB
DB_FILE = "curupira.db"

class MemoryManager:
    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        self.logger = logging.getLogger("MemoryManager")

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
            await db.execute("""
                INSERT INTO facts (user_id, key, value, created_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, key, value, datetime.now()))
            await db.commit()

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
