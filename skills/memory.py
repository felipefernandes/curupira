import aiosqlite
import logging
from datetime import datetime
from typing import Any, Dict
import os

import shutil
import pathlib

from skills.base import BaseSkill

# Define path for SQLite DB
# Use a dedicated data directory to avoid git conflicts
DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
DB_FILE = DATA_DIR / "curupira.db"

class MemoryManager:
    """Gerenciador de banco de dados SQLite para habilidades de memória."""

    def __init__(self, db_path=None):
        """Inicializa o gerenciador com caminho do banco de dados.
        
        Args:
            db_path: Caminho customizado para o DB. Caso None, usa DATA_DIR.
        """
        self.logger = logging.getLogger("MemoryManager")
        
        # Ensure data directory exists
        if not DATA_DIR.exists():
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            
        # Check for legacy DB at root and migrate if needed
        legacy_db = pathlib.Path(__file__).parent.parent / "curupira.db"
        target_path = pathlib.Path(db_path) if db_path else DB_FILE
        if legacy_db.exists() and not target_path.exists():
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
            await db.execute("""
                CREATE TABLE IF NOT EXISTS token_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT,
                    model TEXT,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    timestamp DATETIME
                )
            """)
            await db.commit()

            # Migration: add recurrence columns if they don't exist yet
            async with db.execute("PRAGMA table_info(reminders)") as cursor:
                existing_cols = {row[1] for row in await cursor.fetchall()}
            for col, defn in [
                ("recurrence", "TEXT DEFAULT NULL"),
                ("is_task", "INTEGER DEFAULT 0"),
                ("external_id", "TEXT DEFAULT NULL"),
            ]:
                if col not in existing_cols:
                    try:
                        await db.execute(f"ALTER TABLE reminders ADD COLUMN {col} {defn}")
                        await db.commit()
                        self.logger.info(f"Migrated reminders table: added column '{col}'.")
                    except Exception as e:
                        self.logger.error(
                            f"Failed to migrate reminders table — could not add column '{col}': {e}"
                        )

            # Create index on external_id for performance (Google Calendar integration)
            try:
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_reminders_external_id ON reminders(external_id)"
                )
                await db.commit()
                self.logger.info("Created index on reminders.external_id.")
            except Exception as e:
                self.logger.error(f"Failed to create index on external_id: {e}")

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

    async def get_facts(self, user_id, limit: int = 20):
        """Retrieves facts for a user as a formatted text list.

        Returns the most recent `limit` facts to avoid bloating the agent prompt.
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT key, value FROM facts WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit)
            ) as cursor:
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

    async def get_context(self, user_id, limit=20, minutes_ago=30):
        """Retrieves the recent messages for context injection within a timeframe."""
        from datetime import timedelta
        cutoff_time = datetime.now() - timedelta(minutes=minutes_ago)
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT role, content FROM conversations 
                WHERE user_id = ? AND timestamp >= ?
                ORDER BY id DESC LIMIT ?
            """, (user_id, cutoff_time, limit)) as cursor:
                rows = await cursor.fetchall()
                # Reverse to correct chronological order
                history = reversed(rows)
                formatted_history = []
                for role, content in history:
                     role_name = "User" if role == "user" else "Model"
                     formatted_history.append(f"{role_name}: {content}")
                return "\n".join(formatted_history)

    async def log_token_usage(self, provider: str, model: str, prompt_tokens: int, completion_tokens: int):
        """Logs the tokens consumed by the LLM."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO token_usage (provider, model, prompt_tokens, completion_tokens, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (provider, model, prompt_tokens, completion_tokens, datetime.now()))
            await db.commit()

    async def get_usage_summary(self) -> Dict[str, Dict[str, int]]:
        """Returns a consolidated report of token usage grouped by provider."""
        summary = {}
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT provider, SUM(prompt_tokens), SUM(completion_tokens)
                FROM token_usage
                GROUP BY provider
            """) as cursor:
                async for row in cursor:
                    summary[row[0]] = {
                        "prompt_tokens": row[1] or 0,
                        "completion_tokens": row[2] or 0
                    }
        return summary


class SaveFactSkill(BaseSkill):
    """Skill para o agente persistir fatos importantes sobre o usuário."""

    def __init__(self, memory_manager: MemoryManager):
        self._memory = memory_manager

    @property
    def name(self) -> str:
        return "save_user_fact"

    @property
    def display_name(self) -> str:
        return "🧠 Salvar Fato do Usuário"

    @property
    def skill_group(self) -> str:
        return "system"

    @property
    def skill_group_emoji(self) -> str:
        return "🖥️"

    @property
    def description(self) -> str:
        return "Persiste um fato importante sobre o usuário no banco de longo prazo (ex: nome, idades, rotinas ou preferências)."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Identificador do fato (ex: 'city', 'preferred_name')."
                },
                "value": {
                    "type": "string",
                    "description": "Valor do fato (ex: 'São Paulo', 'português')."
                }
            },
            "required": ["key", "value"]
        }

    async def execute(self, context: Dict[str, Any], **kwargs) -> Any:
        user_id = context.get("user_id")
        key = kwargs.get("key", "").strip()
        value = kwargs.get("value", "").strip()

        if not user_id:
            return self.error("user_id ausente no contexto. Não foi possível salvar o fato.")
        if not key:
            return self.error("O campo 'key' é obrigatório e não pode ser vazio.")
        if not value:
            return self.error("O campo 'value' é obrigatório e não pode ser vazio.")

        await self._memory.save_fact(user_id, key, value)
        return self.success({"key": key, "value": value}, message=f"Fato salvo com sucesso: {key}")
