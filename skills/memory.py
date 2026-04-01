import aiosqlite
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
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

            # Migration: add metadata column to conversations for structured history
            async with db.execute("PRAGMA table_info(conversations)") as cursor:
                conv_cols = {row[1] for row in await cursor.fetchall()}
            if "metadata" not in conv_cols:
                try:
                    await db.execute("ALTER TABLE conversations ADD COLUMN metadata TEXT")
                    await db.commit()
                    self.logger.info("Migrated conversations table: added column 'metadata'.")
                except Exception as e:
                    self.logger.error(f"Failed to add metadata column to conversations: {e}")

            # Create index on conversations for faster context queries
            try:
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_conversations_user_timestamp "
                    "ON conversations(user_id, timestamp DESC)"
                )
                await db.commit()
            except Exception as e:
                self.logger.error(f"Failed to create conversations index: {e}")

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

    async def log_message(self, user_id, role, content, metadata: Optional[Dict[str, Any]] = None):
        """Logs a message to the conversation history.

        Args:
            user_id: Telegram user ID.
            role: Message role — "user", "assistant"/"model", or "tool".
            content: Text content (may be None for tool-call messages).
            metadata: Optional structured data (tool_call_id, tool_name, tool_args).
        """
        # Normalise role for DB storage (keep legacy "model" value)
        db_role = "model" if role == "assistant" else role

        metadata_json = json.dumps(metadata) if metadata else None

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO conversations (user_id, role, content, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, db_role, content, datetime.now(), metadata_json))
            await db.commit()

    async def get_context(
        self, user_id, limit=50, minutes_ago=240
    ) -> List[Dict[str, Any]]:
        """Retrieves recent messages as a structured list for multi-turn context.

        Returns a list of message dicts compatible with OpenAI/Groq chat format::

            [
                {"role": "user", "content": "Olá"},
                {"role": "assistant", "content": "Oi!"},
                ...
            ]

        Tool-call and tool-result messages carry extra keys
        (``tool_calls``, ``tool_call_id``, ``name``) when metadata is present.
        """
        from datetime import timedelta

        cutoff_time = datetime.now() - timedelta(minutes=minutes_ago)
        messages: List[Dict[str, Any]] = []

        async with aiosqlite.connect(self.db_path) as db:
            # Fetch N most-recent rows in reverse, then reverse again for chronological order
            async with db.execute("""
                SELECT role, content, metadata FROM conversations
                WHERE user_id = ? AND timestamp >= ?
                ORDER BY id DESC LIMIT ?
            """, (user_id, cutoff_time, limit)) as cursor:
                rows = await cursor.fetchall()

        for role, content, metadata_json in reversed(list(rows)):
            # Normalise legacy "model" → "assistant"
            if role == "model":
                role = "assistant"

            msg: Dict[str, Any] = {"role": role, "content": content}

            if metadata_json:
                try:
                    meta = json.loads(metadata_json)

                    # Assistant tool-call message (has tool_name but role is assistant)
                    if role == "assistant" and meta.get("tool_call_id") and meta.get("tool_name"):
                        msg["content"] = None
                        msg["tool_calls"] = [{
                            "id": meta["tool_call_id"],
                            "type": "function",
                            "function": {
                                "name": meta["tool_name"],
                                "arguments": json.dumps(meta.get("tool_args", {})),
                            },
                        }]

                    # Tool result message
                    elif role == "tool" and meta.get("tool_call_id"):
                        msg["tool_call_id"] = meta["tool_call_id"]
                        msg["name"] = meta.get("tool_name", "unknown")

                except json.JSONDecodeError:
                    self.logger.warning(f"Invalid metadata JSON in conversation row: {metadata_json[:80]}")

            messages.append(msg)

        return messages

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

    async def get_tool_usage_stats(
        self, user_id: int, days: int = 7
    ) -> List[Dict[str, Any]]:
        """Retorna contagem de uso de tools pelo usuário nos últimos N dias.

        Cada entrada: {"tool_name": str, "call_count": int, "args_samples": List[dict]}
        Ordenado por call_count DESC.
        """
        interval = f"-{days} days"
        rows_by_tool: Dict[str, Dict[str, Any]] = {}

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                SELECT
                    json_extract(metadata, '$.tool_name'),
                    json_extract(metadata, '$.tool_args')
                FROM conversations
                WHERE
                    user_id = ?
                    AND role = 'assistant'
                    AND json_extract(metadata, '$.tool_name') IS NOT NULL
                    AND timestamp >= datetime('now', ?)
                """,
                (user_id, interval),
            ) as cursor:
                async for tool_name, args_json in cursor:
                    if tool_name not in rows_by_tool:
                        rows_by_tool[tool_name] = {
                            "tool_name": tool_name,
                            "call_count": 0,
                            "args_samples": [],
                        }
                    rows_by_tool[tool_name]["call_count"] += 1
                    if args_json:
                        try:
                            parsed = json.loads(args_json)
                            if isinstance(parsed, dict):
                                rows_by_tool[tool_name]["args_samples"].append(parsed)
                        except (json.JSONDecodeError, TypeError):
                            pass

        return sorted(
            rows_by_tool.values(), key=lambda x: x["call_count"], reverse=True
        )


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
