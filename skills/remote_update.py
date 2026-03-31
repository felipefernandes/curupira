"""
Remote Update Skill for Curupira
=================================
Allows the authorized user to trigger a remote update of the bot via Telegram.

Flow:
  1. User sends a message containing "atualizar sistema" and "pin: <PIN>".
  2. Skill validates PIN against REMOTE_UPDATE_PIN env var (constant-time compare).
  3. Sends "⏳ Iniciando atualização..." to the chat.
  4. Runs `git pull` then `pip install -r requirements.txt` asynchronously.
  5. Writes a sentinel file (.update_pending) with the chat_id.
  6. Replaces the process via os.execv — bot restarts with updated code.
  7. On next startup, bot reads sentinel, sends "✅ Sistema atualizado", deletes file.
"""

import asyncio
import json
import logging
import os
import re
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from skills.base import BaseSkill

logger = logging.getLogger("RemoteUpdateSkill")

# Project root — used for subprocess CWD and sentinel file location.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

_SENTINEL_FILE = _PROJECT_ROOT / ".update_pending"
_SENTINEL_MAX_AGE_SECONDS = 600  # 10 minutes

# Regex: extracts PIN after "pin:" (case-insensitive, strips trailing whitespace)
_PIN_RE = re.compile(r"pin:\s*(\S+)", re.IGNORECASE)
# Trigger phrase detection (case-insensitive)
_TRIGGER_RE = re.compile(r"atualizar\s+sistema", re.IGNORECASE)


class RemoteUpdateSkill(BaseSkill):
    """PIN-authenticated skill that runs the update pipeline and restarts the bot."""

    # Timeout for the full update pipeline (git pull + pip install), in seconds.
    PIPELINE_TIMEOUT: int = 300

    @property
    def name(self) -> str:
        return "trigger_remote_update"

    @property
    def display_name(self) -> str:
        return "🔄 Atualização Remota"

    @property
    def description(self) -> str:
        return (
            "Executa a atualização remota do bot (git pull + pip install + restart). "
            "Requer que a mensagem do usuário contenha 'atualizar sistema' e 'pin: <PIN>'. "
            "Usar apenas quando o usuário solicitar explicitamente a atualização do sistema."
        )

    @property
    def skill_group(self) -> str:
        return "system"

    @property
    def skill_group_emoji(self) -> str:
        return "🖥️"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    # ── Subprocess helper ──────────────────────────────────────────────

    async def _run_subprocess(
        self, cmd: list[str], timeout: int
    ) -> Tuple[int, str]:
        """
        Runs a command asynchronously via asyncio.create_subprocess_exec.

        Returns:
            (returncode, stderr_output)
        """
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(_PROJECT_ROOT),
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise
        output = (stdout.decode(errors="replace") + stderr.decode(errors="replace")).strip()
        return proc.returncode, output

    # ── PIN helpers ────────────────────────────────────────────────────

    @staticmethod
    def _extract_pin(message: str) -> Optional[str]:
        """Extracts the PIN value from the raw message, or None if absent."""
        match = _PIN_RE.search(message)
        return match.group(1) if match else None

    @staticmethod
    def _validate_pin(provided: str, expected: str) -> bool:
        """Constant-time PIN comparison to prevent timing attacks."""
        return secrets.compare_digest(provided.encode(), expected.encode())

    # ── Sentinel helpers ───────────────────────────────────────────────

    @staticmethod
    def write_sentinel(chat_id: int) -> None:
        """Writes the update sentinel file before restarting."""
        payload = {
            "chat_id": chat_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        _SENTINEL_FILE.write_text(json.dumps(payload), encoding="utf-8")
        logger.info("Sentinel escrito: %s", _SENTINEL_FILE)

    # ── Main execute ───────────────────────────────────────────────────

    async def execute(self, context: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        from core import config as cfg

        # --- Validate configuration ---
        expected_pin = cfg.REMOTE_UPDATE_PIN
        if not expected_pin:
            logger.warning("REMOTE_UPDATE_PIN não configurado — skill desabilitada.")
            return self.error(
                "Atualização remota não está configurada. "
                "Defina REMOTE_UPDATE_PIN no arquivo .env."
            )

        # --- Extract and validate PIN from the raw message ---
        raw_message: str = context.get("raw_message", "")
        if not _TRIGGER_RE.search(raw_message):
            # Message doesn't contain the trigger phrase — not our call.
            return self.error("Comando de atualização não reconhecido.")

        provided_pin = self._extract_pin(raw_message)
        if not provided_pin or not self._validate_pin(provided_pin, expected_pin):
            # Silent fail — do not hint that a PIN exists.
            logger.warning("Tentativa de atualização com PIN inválido ou ausente.")
            return self.error("PIN inválido ou ausente.")

        # --- Send progress acknowledgement via Telegram ---
        bot = context.get("bot")
        chat_id: Optional[int] = context.get("chat_id")

        if bot and chat_id:
            try:
                await bot.send_message(chat_id=chat_id, text="⏳ Iniciando atualização...")
            except Exception as exc:
                logger.warning("Não foi possível enviar mensagem de progresso: %s", exc)

        # --- Run pipeline ---
        try:
            # Step 1: git pull
            returncode, output = await asyncio.wait_for(
                self._run_subprocess(["git", "pull"], timeout=self.PIPELINE_TIMEOUT),
                timeout=self.PIPELINE_TIMEOUT,
            )
            if returncode != 0:
                logger.error("git pull falhou (código %d): %s", returncode, output)
                return self.error(f"❌ Falha no git pull (código {returncode}). Atualização abortada.")

            logger.info("git pull concluído: %s", output[:200])

            # Step 2: pip install
            pip_cmd = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"]
            returncode, output = await asyncio.wait_for(
                self._run_subprocess(pip_cmd, timeout=self.PIPELINE_TIMEOUT),
                timeout=self.PIPELINE_TIMEOUT,
            )
            if returncode != 0:
                logger.error("pip install falhou (código %d): %s", returncode, output)
                return self.error(f"❌ Falha no pip install (código {returncode}). Atualização abortada.")

            logger.info("pip install concluído.")

        except asyncio.TimeoutError:
            logger.error("Pipeline de atualização excedeu o timeout de %ds.", self.PIPELINE_TIMEOUT)
            return self.error(
                f"❌ Atualização abortada: timeout de {self.PIPELINE_TIMEOUT}s excedido."
            )

        # --- Write sentinel and restart ---
        if chat_id:
            self.write_sentinel(chat_id)

        logger.info("Reiniciando processo via os.execv...")
        try:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as exc:
            logger.error("os.execv falhou (%s). Reinicialização manual necessária.", exc)
            return self.error(
                "Atualização concluída, mas o reinício automático falhou. "
                "Reinicie o bot manualmente."
            )

        # Unreachable — os.execv replaces the process.
        return self.success({}, message="Reiniciando...")  # pragma: no cover


# ── Startup sentinel check ─────────────────────────────────────────────

async def check_update_sentinel(bot: Any, authorized_user_id: int) -> None:
    """
    Checks for a post-update sentinel file on bot startup.

    If found and recent (< 10 minutes old), sends "✅ Sistema atualizado"
    to the stored chat_id and deletes the file.
    If stale, deletes the file without sending any message.

    Call this from post_init, after the Telegram Application is initialized.
    """
    if not _SENTINEL_FILE.exists():
        return

    try:
        payload = json.loads(_SENTINEL_FILE.read_text(encoding="utf-8"))
        chat_id = payload.get("chat_id")
        updated_at_str = payload.get("updated_at", "")

        if not chat_id or not updated_at_str:
            logger.warning("Sentinel inválido (campos faltando). Removendo.")
            _SENTINEL_FILE.unlink(missing_ok=True)
            return

        updated_at = datetime.fromisoformat(updated_at_str)
        age_seconds = (datetime.now(timezone.utc) - updated_at).total_seconds()

        if age_seconds > _SENTINEL_MAX_AGE_SECONDS:
            logger.warning(
                "Sentinel encontrado, mas está velho demais (%.0fs). Removendo sem notificar.",
                age_seconds,
            )
            _SENTINEL_FILE.unlink(missing_ok=True)
            return

        logger.info("Atualização detectada! Notificando chat_id=%s.", chat_id)
        await bot.send_message(chat_id=chat_id, text="✅ Sistema atualizado")
        _SENTINEL_FILE.unlink(missing_ok=True)

    except Exception as exc:
        logger.error("Erro ao processar sentinel de atualização: %s", exc)
        _SENTINEL_FILE.unlink(missing_ok=True)
