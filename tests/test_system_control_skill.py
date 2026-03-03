"""Tests for SystemControlSkill."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from skills.system_control import SystemControlSkill


class TestSystemControlSkill:
    def setup_method(self):
        self.skill = SystemControlSkill()

    def test_metadata(self):
        """Test skill metadata properties."""
        assert self.skill.name == "system_control"
        assert "Sistema" in self.skill.display_name
        assert "sistema" in self.skill.description.lower()
        assert self.skill.parameters["type"] == "object"
        assert "action" in self.skill.parameters["properties"]

    def test_parameters_schema(self):
        """Test that all expected actions are in parameters."""
        actions = self.skill.parameters["properties"]["action"]["enum"]
        expected_actions = [
            "get_ip",
            "get_hostname",
            "get_disk_space",
            "read_system_logs",
            "read_file",
            "configure_wifi",
            "execute_command",
        ]
        for action in expected_actions:
            assert action in actions, f"Action {action} missing from schema"

    @pytest.mark.asyncio
    async def test_execute_missing_action(self):
        """Test error when no action is provided."""
        result = await self.skill.execute({})
        assert result["status"] == "error"
        assert "não especificada" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_unknown_action(self):
        """Test error for unknown action."""
        result = await self.skill.execute({}, action="unknown_action")
        assert result["status"] == "error"
        assert "desconhecida" in result["error"].lower()

    @pytest.mark.asyncio
    @patch("skills.system_control.shutil.which")
    async def test_execute_safe_command_success(self, mock_which):
        """Test successful execution of whitelisted safe command."""
        mock_which.return_value = "/usr/bin/hostname"

        # Mock _run_subprocess to avoid actual execution
        async def mock_subprocess(cmd):
            return "raspberrypi\n", "", 0

        self.skill._run_subprocess = mock_subprocess

        result = await self.skill.execute({}, action="get_hostname")

        assert result["status"] == "success"
        assert "output" in result["data"]
        assert "raspberrypi" in result["data"]["output"]

    @pytest.mark.asyncio
    @patch("skills.system_control.shutil.which")
    async def test_execute_safe_command_not_available(self, mock_which):
        """Test error when command is not available on system."""
        mock_which.return_value = None

        result = await self.skill.execute({}, action="get_ip")

        assert result["status"] == "error"
        assert "não disponível" in result["error"].lower()

    @pytest.mark.asyncio
    @patch("skills.system_control.shutil.which")
    async def test_execute_safe_command_failure(self, mock_which):
        """Test handling of command execution failure."""
        mock_which.return_value = "/usr/bin/df"

        # Mock subprocess that returns error
        async def mock_subprocess(cmd):
            return "", "Error: disk not found", 1

        self.skill._run_subprocess = mock_subprocess

        result = await self.skill.execute({}, action="get_disk_space")

        assert result["status"] == "error"
        assert "Falha" in result["error"]

    @pytest.mark.asyncio
    @patch("skills.system_control.shutil.which")
    async def test_read_system_logs_success(self, mock_which):
        """Test reading system logs via journalctl."""
        mock_which.return_value = "/usr/bin/journalctl"

        # Mock subprocess
        async def mock_subprocess(cmd):
            log_output = "Jan 01 12:00:00 host kernel: Log entry 1\nJan 01 12:01:00 host kernel: Log entry 2"
            return log_output, "", 0

        self.skill._run_subprocess = mock_subprocess

        result = await self.skill.execute({}, action="read_system_logs", log_lines=50)

        assert result["status"] == "success"
        assert "logs" in result["data"]
        assert "Log entry" in result["data"]["logs"]
        assert result["data"]["line_count"] >= 1

    @pytest.mark.asyncio
    @patch("skills.system_control.shutil.which")
    async def test_read_system_logs_invalid_filter(self, mock_which):
        """Test that unsafe log filters are rejected."""
        mock_which.return_value = "/usr/bin/journalctl"

        result = await self.skill.execute(
            {},
            action="read_system_logs",
            log_filter="--output=json --eval='rm -rf /'"  # Dangerous flag
        )

        assert result["status"] == "error"
        assert "não permitida" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_read_file_missing_path(self):
        """Test error when file_path is not provided."""
        result = await self.skill.execute({}, action="read_file")
        assert result["status"] == "error"
        assert "não fornecido" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_read_file_sensitive_path(self):
        """Test that sensitive files are blocked."""
        result = await self.skill.execute(
            {},
            action="read_file",
            file_path="/etc/shadow"
        )
        assert result["status"] == "error"
        assert "negado" in result["error"].lower()

    @pytest.mark.asyncio
    @patch("skills.system_control.Path")
    async def test_read_file_not_found(self, mock_path):
        """Test error when file doesn't exist."""
        mock_path_instance = MagicMock()
        mock_path_instance.is_file.return_value = False
        mock_path.return_value.resolve.return_value = mock_path_instance

        result = await self.skill.execute(
            {},
            action="read_file",
            file_path="/tmp/nonexistent.txt"
        )
        assert result["status"] == "error"
        assert "não encontrado" in result["error"].lower()

    @pytest.mark.asyncio
    @patch("skills.system_control.shutil.which")
    async def test_configure_wifi_missing_ssid(self, mock_which):
        """Test error when SSID is not provided for WiFi config."""
        result = await self.skill.execute({}, action="configure_wifi")
        assert result["status"] == "error"
        assert "não fornecido" in result["error"].lower()

    @pytest.mark.asyncio
    @patch("skills.system_control.shutil.which")
    async def test_configure_wifi_nmcli_unavailable(self, mock_which):
        """Test error when nmcli is not available."""
        mock_which.return_value = None

        result = await self.skill.execute(
            {},
            action="configure_wifi",
            ssid="MyNetwork"
        )
        assert result["status"] == "error"
        assert "NetworkManager" in result["error"]

    @pytest.mark.asyncio
    @patch("skills.system_control.shutil.which")
    @patch("skills.system_control.get_security_guard")
    async def test_configure_wifi_success(self, mock_guard, mock_which):
        """Test successful WiFi configuration."""
        mock_which.return_value = "/usr/bin/nmcli"

        # Mock subprocess
        async def mock_subprocess(cmd):
            return "Device 'wlan0' successfully activated", "", 0

        self.skill._run_subprocess = mock_subprocess

        result = await self.skill.execute(
            {},
            action="configure_wifi",
            ssid="MyNetwork",
            password="mypassword"
        )

        assert result["status"] == "success"
        assert result["data"]["ssid"] == "MyNetwork"
        assert result["data"]["status"] == "connected"

    @pytest.mark.asyncio
    async def test_execute_command_missing_command(self):
        """Test error when command is not provided."""
        result = await self.skill.execute({}, action="execute_command")
        assert result["status"] == "error"
        assert "não fornecido" in result["error"].lower()

    @pytest.mark.asyncio
    @patch("skills.system_control.get_config")
    @patch("skills.system_control.get_security_guard")
    async def test_execute_command_blocked_by_guard(self, mock_guard_func, mock_get_config):
        """Test that dangerous commands are blocked by security guard."""
        # Mock configuration to allow custom commands
        mock_config = MagicMock()
        mock_config.system_control_security_level = "normal"
        mock_config.system_control_allow_custom_commands = True
        mock_config.system_control_allow_file_writes = False
        mock_get_config.return_value = mock_config

        # Mock security guard to reject command
        mock_guard = AsyncMock()
        mock_guard.evaluate_command = AsyncMock(
            return_value=(False, "REJECT: Comando destrutivo detectado")
        )
        mock_guard_func.return_value = mock_guard

        result = await self.skill.execute(
            {},
            action="execute_command",
            command="rm -rf /"
        )

        assert result["status"] == "error"
        assert "bloqueado" in result["error"].lower()
        assert "destrutivo" in result["error"].lower()

    @pytest.mark.asyncio
    @patch("skills.system_control.get_config")
    @patch("skills.system_control.shutil.which")
    @patch("skills.system_control.get_security_guard")
    async def test_execute_command_approved_and_success(self, mock_guard_func, mock_which, mock_get_config):
        """Test successful execution of LLM-approved command."""
        # Mock configuration to allow custom commands
        mock_config = MagicMock()
        mock_config.system_control_security_level = "normal"
        mock_config.system_control_allow_custom_commands = True
        mock_config.system_control_allow_file_writes = False
        mock_get_config.return_value = mock_config

        # Mock security guard to approve command
        mock_guard = AsyncMock()
        mock_guard.evaluate_command = AsyncMock(
            return_value=(True, "Comando aprovado")
        )
        mock_guard_func.return_value = mock_guard

        mock_which.return_value = "/bin/echo"

        # Mock subprocess
        async def mock_subprocess(cmd):
            return "Hello World\n", "", 0

        self.skill._run_subprocess = mock_subprocess

        result = await self.skill.execute(
            {},
            action="execute_command",
            command="echo 'Hello World'"
        )

        assert result["status"] == "success"
        assert "Hello World" in result["data"]["output"]

    @pytest.mark.asyncio
    async def test_run_subprocess_timeout(self):
        """Test subprocess timeout handling."""
        import asyncio

        # Mock asyncio.create_subprocess_exec to return a never-ending process
        async def mock_create_subprocess(*args, **kwargs):
            mock_process = MagicMock()
            mock_process.returncode = None

            async def mock_communicate():
                await asyncio.sleep(100)  # Simulate long-running process
                return b"", b""

            mock_process.communicate = mock_communicate
            mock_process.kill = MagicMock()
            mock_process.wait = AsyncMock()
            return mock_process

        # Temporarily reduce timeout for faster test
        original_timeout = self.skill.COMMAND_TIMEOUT
        self.skill.COMMAND_TIMEOUT = 0.1

        with patch("asyncio.create_subprocess_exec", side_effect=mock_create_subprocess):
            with pytest.raises(asyncio.TimeoutError):
                await self.skill._run_subprocess(["sleep", "10"])

        # Restore original timeout
        self.skill.COMMAND_TIMEOUT = original_timeout

    @pytest.mark.asyncio
    async def test_run_subprocess_output_truncation(self):
        """Test that large outputs are truncated to prevent OOM."""
        # Mock subprocess that returns large output (using short repeating pattern to avoid token detection)
        large_output = "line\n" * ((self.skill.MAX_OUTPUT_SIZE // 5) + 200)

        async def mock_create_subprocess(*args, **kwargs):
            mock_process = MagicMock()
            mock_process.returncode = 0

            async def mock_communicate():
                return large_output.encode(), b""

            mock_process.communicate = mock_communicate
            return mock_process

        with patch("asyncio.create_subprocess_exec", side_effect=mock_create_subprocess):
            stdout, stderr, returncode = await self.skill._run_subprocess(["echo"])

            # Verify output was truncated
            assert len(stdout) <= self.skill.MAX_OUTPUT_SIZE + 50  # Account for truncation message
            assert "truncada" in stdout if len(large_output) > self.skill.MAX_OUTPUT_SIZE else True
