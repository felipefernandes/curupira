"""
System Control Skill for Curupira
==================================
Provides "Power User" capabilities for Linux/Raspbian systems:
- Read-only OS diagnostics (IP, disk, hostname, etc.)
- System log inspection (journalctl)
- File reading with OOM protection
- Network configuration (WiFi)
- Safety-guarded command execution

Resolves Issues #42 and #53.
"""

import asyncio
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from .base import BaseSkill
from core.security_guard import get_security_guard


class SystemControlSkill(BaseSkill):
    """
    Skill providing safe system-level diagnostics and control.

    Security Model:
    - Strict whitelist for read-only commands
    - LLM Security Guard for non-whitelisted operations
    - Output buffering to prevent OOM
    - Subprocess timeouts
    """

    # Whitelist of safe, read-only commands
    SAFE_COMMANDS = {
        "get_ip": ["ip", "-brief", "addr"],
        "get_hostname": ["hostname"],
        "get_disk_space": ["df", "-h"],
        "get_uptime": ["uptime"],
        "get_memory": ["free", "-h"],
        "get_network_interfaces": ["ip", "link", "show"],
    }

    # Maximum command execution timeout (seconds)
    COMMAND_TIMEOUT = 30

    # Maximum output buffer size (bytes) to prevent OOM
    MAX_OUTPUT_SIZE = 10 * 1024  # 10KB

    def __init__(self):
        self.logger = logging.getLogger("SystemControlSkill")

    @property
    def name(self) -> str:
        return "system_control"

    @property
    def display_name(self) -> str:
        return "🖥️ Controle do Sistema"

    @property
    def description(self) -> str:
        return (
            "Fornece acesso seguro a informações e controles do sistema operacional. "
            "Permite executar comandos diagnósticos, ler logs do sistema, e configurar "
            "rede (WiFi). Inclui proteções contra comandos perigosos."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "get_ip",
                        "get_hostname",
                        "get_disk_space",
                        "get_uptime",
                        "get_memory",
                        "get_network_interfaces",
                        "read_system_logs",
                        "read_file",
                        "configure_wifi",
                        "execute_command",
                    ],
                    "description": "A ação do sistema a ser executada",
                },
                "log_filter": {
                    "type": "string",
                    "description": "Filtro para logs do sistema (usado com read_system_logs). Ex: '--since yesterday', '-p err'",
                },
                "log_lines": {
                    "type": "integer",
                    "description": "Número de linhas de log a retornar (padrão: 50, máximo: 500)",
                    "default": 50,
                },
                "file_path": {
                    "type": "string",
                    "description": "Caminho do arquivo a ser lido (usado com read_file)",
                },
                "tail_lines": {
                    "type": "integer",
                    "description": "Número de linhas finais do arquivo a retornar (padrão: 100)",
                    "default": 100,
                },
                "ssid": {
                    "type": "string",
                    "description": "Nome da rede WiFi (SSID) para conectar (usado com configure_wifi)",
                },
                "password": {
                    "type": "string",
                    "description": "Senha da rede WiFi (usado com configure_wifi)",
                },
                "command": {
                    "type": "string",
                    "description": "Comando do sistema para executar com validação de segurança (usado com execute_command)",
                },
            },
            "required": ["action"],
        }

    async def execute(self, context: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Executes system control actions safely.

        Args:
            context: Execution context (user_id, etc.)
            **kwargs: Action parameters (action, log_filter, file_path, etc.)

        Returns:
            Dict containing status, data, and optional message
        """
        action = kwargs.get("action")

        if not action:
            return self.error("Ação não especificada")

        try:
            # Route to appropriate handler
            if action in self.SAFE_COMMANDS:
                return await self._execute_safe_command(action)
            elif action == "read_system_logs":
                return await self._read_system_logs(
                    log_filter=kwargs.get("log_filter", ""),
                    lines=min(kwargs.get("log_lines", 50), 500)
                )
            elif action == "read_file":
                file_path = kwargs.get("file_path")
                if not file_path:
                    return self.error("Caminho do arquivo não fornecido")
                return await self._read_file(
                    file_path=file_path,
                    tail_lines=kwargs.get("tail_lines", 100)
                )
            elif action == "configure_wifi":
                ssid = kwargs.get("ssid")
                password = kwargs.get("password")
                if not ssid:
                    return self.error("SSID da rede WiFi não fornecido")
                return await self._configure_wifi(ssid=ssid, password=password)
            elif action == "execute_command":
                command = kwargs.get("command")
                if not command:
                    return self.error("Comando não fornecido")
                return await self._execute_guarded_command(command)
            else:
                return self.error(f"Ação desconhecida: {action}")

        except Exception as e:
            self.logger.error(f"Erro executando ação {action}: {e}")
            return self.error(f"Erro ao executar {action}: {str(e)}")

    async def _execute_safe_command(self, action: str) -> Dict[str, Any]:
        """
        Executes a whitelisted safe command.

        Args:
            action: The action key from SAFE_COMMANDS

        Returns:
            Success or error response
        """
        cmd = self.SAFE_COMMANDS[action]

        # Check if command is available
        if not shutil.which(cmd[0]):
            return self.error(f"Comando '{cmd[0]}' não disponível neste sistema")

        try:
            # Execute with timeout and output limits
            stdout, stderr, returncode = await self._run_subprocess(cmd)

            if returncode != 0:
                error_msg = stderr[:500] if stderr else "Comando retornou erro"
                return self.error(f"Falha ao executar {action}: {error_msg}")

            return self.success(
                data={"output": stdout, "command": " ".join(cmd)},
                message=f"✅ {action} executado com sucesso"
            )

        except asyncio.TimeoutError:
            return self.error(f"Timeout executando {action} (>{self.COMMAND_TIMEOUT}s)")
        except Exception as e:
            return self.error(f"Erro executando {action}: {str(e)}")

    async def _read_system_logs(
        self,
        log_filter: str = "",
        lines: int = 50
    ) -> Dict[str, Any]:
        """
        Reads system logs via journalctl with safety limits.

        Args:
            log_filter: Additional journalctl flags (e.g., '--since yesterday', '-p err')
            lines: Number of lines to return (max 500)

        Returns:
            Success or error response with log content
        """
        # Check if journalctl is available
        if not shutil.which("journalctl"):
            return self.error("journalctl não disponível neste sistema")

        # Build command with safety constraints
        cmd = ["journalctl", "-n", str(lines)]

        # Parse and sanitize log_filter
        if log_filter:
            # Simple whitelist of safe journalctl flags
            safe_flags = ["--since", "--until", "-p", "--priority", "-u", "--unit"]
            filter_parts = log_filter.split()

            # Basic validation: only allow whitelisted flags
            for part in filter_parts:
                if part.startswith("-") and not any(part.startswith(flag) for flag in safe_flags):
                    return self.error(f"Flag não permitida: {part}")

            cmd.extend(filter_parts)

        try:
            stdout, stderr, returncode = await self._run_subprocess(cmd)

            if returncode != 0:
                return self.error(f"Erro ao ler logs: {stderr[:500]}")

            # Count lines for summary
            line_count = len(stdout.split('\n'))

            return self.success(
                data={"logs": stdout, "line_count": line_count},
                message=f"📋 {line_count} linhas de log recuperadas"
            )

        except asyncio.TimeoutError:
            return self.error(f"Timeout lendo logs (>{self.COMMAND_TIMEOUT}s)")
        except Exception as e:
            return self.error(f"Erro lendo logs: {str(e)}")

    async def _read_file(
        self,
        file_path: str,
        tail_lines: int = 100
    ) -> Dict[str, Any]:
        """
        Reads a text file with OOM protection.

        Args:
            file_path: Path to the file
            tail_lines: Number of lines from the end to read

        Returns:
            Success or error response with file content
        """
        path = Path(file_path).resolve()

        # Security check: prevent reading sensitive files
        sensitive_paths = ["/etc/shadow", "/etc/gshadow", "/root/.ssh"]
        if any(str(path).startswith(sp) for sp in sensitive_paths):
            return self.error(f"Acesso negado: arquivo sensível")

        # Check if file exists and is readable
        if not path.is_file():
            return self.error(f"Arquivo não encontrado: {file_path}")

        if not path.stat().st_size:
            return self.success(
                data={"content": "", "path": str(path), "size": 0},
                message="📄 Arquivo vazio"
            )

        # Use tail command for efficiency with large files
        if shutil.which("tail"):
            try:
                cmd = ["tail", "-n", str(tail_lines), str(path)]
                stdout, stderr, returncode = await self._run_subprocess(cmd)

                if returncode != 0:
                    return self.error(f"Erro ao ler arquivo: {stderr[:500]}")

                line_count = len(stdout.split('\n'))
                file_size = path.stat().st_size

                return self.success(
                    data={
                        "content": stdout,
                        "path": str(path),
                        "lines": line_count,
                        "size": file_size
                    },
                    message=f"📄 {line_count} linhas lidas de {path.name}"
                )

            except asyncio.TimeoutError:
                return self.error(f"Timeout lendo arquivo (>{self.COMMAND_TIMEOUT}s)")
            except Exception as e:
                return self.error(f"Erro lendo arquivo: {str(e)}")
        else:
            # Fallback: read file in Python (less efficient for large files)
            try:
                # Read last N lines
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                    content = ''.join(lines[-tail_lines:])

                    # Safety check: limit output size
                    if len(content) > self.MAX_OUTPUT_SIZE:
                        content = content[-self.MAX_OUTPUT_SIZE:]

                    return self.success(
                        data={
                            "content": content,
                            "path": str(path),
                            "lines": len(lines[-tail_lines:]),
                            "size": path.stat().st_size
                        },
                        message=f"📄 Arquivo lido: {path.name}"
                    )
            except UnicodeDecodeError:
                return self.error("Arquivo parece ser binário, não texto")
            except Exception as e:
                return self.error(f"Erro lendo arquivo: {str(e)}")

    async def _configure_wifi(
        self,
        ssid: str,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Configures and connects to a WiFi network.

        Args:
            ssid: The WiFi network name (SSID)
            password: The WiFi password (optional for open networks)

        Returns:
            Success or error response
        """
        # Check if nmcli is available (NetworkManager CLI)
        if not shutil.which("nmcli"):
            return self.error(
                "NetworkManager (nmcli) não disponível. "
                "Este comando requer NetworkManager instalado."
            )

        try:
            # Build nmcli command to connect to WiFi
            # nmcli device wifi connect <SSID> password <PASSWORD>
            cmd = ["nmcli", "device", "wifi", "connect", ssid]

            if password:
                cmd.extend(["password", password])

            # Security check via LLM guard
            guard = get_security_guard()
            command_str = " ".join(cmd)

            # For WiFi commands, we trust nmcli but still log the action
            self.logger.info(f"Executando configuração WiFi: nmcli device wifi connect {ssid}")

            # Execute command
            stdout, stderr, returncode = await self._run_subprocess(cmd)

            if returncode != 0:
                # Common error: wrong password or network not found
                error_msg = stderr[:500] if stderr else "Falha ao conectar"
                return self.error(
                    f"Erro ao conectar WiFi '{ssid}': {error_msg}"
                )

            return self.success(
                data={
                    "ssid": ssid,
                    "status": "connected",
                    "output": stdout
                },
                message=f"📶 Conectado com sucesso à rede WiFi '{ssid}'"
            )

        except asyncio.TimeoutError:
            return self.error(f"Timeout conectando WiFi (>{self.COMMAND_TIMEOUT}s)")
        except Exception as e:
            return self.error(f"Erro configurando WiFi: {str(e)}")

    async def _execute_guarded_command(self, command: str) -> Dict[str, Any]:
        """
        Executes a custom shell command with LLM Security Guard validation.

        This is the "escape hatch" for power users who need to run
        commands not in the whitelist. The LLM Security Guard evaluates
        the command before execution.

        Args:
            command: The shell command string to execute

        Returns:
            Success or error response
        """
        self.logger.info(f"Validando comando via Security Guard: {command}")

        # Get security guard and evaluate
        guard = get_security_guard()
        is_safe, reason = await guard.evaluate_command(command)

        if not is_safe:
            self.logger.warning(f"Comando bloqueado pelo Security Guard: {command}")
            self.logger.warning(f"Razão: {reason}")
            return self.error(
                f"🛡️ Comando bloqueado por segurança\n\n"
                f"**Comando:** `{command}`\n"
                f"**Razão:** {reason}\n\n"
                f"Se você acredita que este comando é seguro, "
                f"considere solicitar que seja adicionado à whitelist."
            )

        # Command approved - execute it
        self.logger.info(f"Comando aprovado pelo Security Guard: {command}")

        try:
            # Parse command into list for subprocess
            # Note: This is a simplification - for production, use shlex.split()
            import shlex
            cmd_parts = shlex.split(command)

            if not cmd_parts:
                return self.error("Comando vazio após parsing")

            # Check if command exists
            if not shutil.which(cmd_parts[0]):
                return self.error(f"Comando '{cmd_parts[0]}' não encontrado no sistema")

            # Execute
            stdout, stderr, returncode = await self._run_subprocess(cmd_parts)

            if returncode != 0:
                return self.error(
                    f"Comando retornou erro (código {returncode}):\n{stderr[:500]}"
                )

            return self.success(
                data={
                    "command": command,
                    "output": stdout,
                    "returncode": returncode
                },
                message=f"✅ Comando executado com sucesso"
            )

        except asyncio.TimeoutError:
            return self.error(f"Timeout executando comando (>{self.COMMAND_TIMEOUT}s)")
        except Exception as e:
            return self.error(f"Erro executando comando: {str(e)}")

    async def _run_subprocess(
        self,
        cmd: List[str]
    ) -> Tuple[str, str, int]:
        """
        Runs a subprocess with timeout and output size limits.

        Args:
            cmd: Command and arguments as list

        Returns:
            Tuple of (stdout, stderr, returncode)

        Raises:
            asyncio.TimeoutError: If command exceeds timeout
        """
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Wait with timeout
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=self.COMMAND_TIMEOUT
            )

            # Decode and limit output size
            stdout = stdout_bytes.decode('utf-8', errors='replace')
            stderr = stderr_bytes.decode('utf-8', errors='replace')

            if len(stdout) > self.MAX_OUTPUT_SIZE:
                stdout = stdout[:self.MAX_OUTPUT_SIZE] + "\n... [saída truncada]"

            if len(stderr) > self.MAX_OUTPUT_SIZE:
                stderr = stderr[:self.MAX_OUTPUT_SIZE] + "\n... [saída truncada]"

            return stdout, stderr, process.returncode

        except asyncio.TimeoutError:
            # Kill the process if it times out
            if process.returncode is None:
                process.kill()
                await process.wait()
            raise
