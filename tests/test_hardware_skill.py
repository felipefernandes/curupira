"""Tests for HardwareMonitoringSkill."""

import pytest
from unittest.mock import patch
from skills.hardware import HardwareMonitoringSkill

class TestHardwareMonitoringSkill:
    def setup_method(self):
        self.skill = HardwareMonitoringSkill()

    def test_metadata(self):
        assert self.skill.name == "hardware_monitoring"
        assert "Monitoramento" in self.skill.display_name
        assert "hardware" in self.skill.description.lower()
        assert self.skill.parameters["type"] == "object"

    @pytest.mark.asyncio
    @patch("skills.hardware.psutil")
    async def test_execute_success(self, mock_psutil):
        class FakePsutilError(Exception): pass
        mock_psutil.Error = FakePsutilError
        
        # Mocks para psutil
        mock_mem = mock_psutil.virtual_memory.return_value
        mock_mem.total = 8 * 1024**3
        mock_mem.used = 4 * 1024**3
        mock_mem.percent = 50.0

        mock_disk = mock_psutil.disk_usage.return_value
        mock_disk.free = 100 * 1024**3

        mock_psutil.cpu_percent.return_value = 25.5
        
        # Testando sem sensores de temperatura
        del mock_psutil.sensors_temperatures
        
        result = await self.skill.execute({})
        
        assert result["status"] == "success", result.get("error", "Unknown error")
        assert result["data"]["cpu_percent"] == 25.5
        msg = result.get("message", "")
        assert "25.5" in msg

    @pytest.mark.asyncio
    @patch("skills.hardware.psutil")
    async def test_execute_psutil_error(self, mock_psutil):
        class FakePsutilError(Exception): pass
        mock_psutil.Error = FakePsutilError
        mock_psutil.virtual_memory.side_effect = FakePsutilError("Simulated error")
        
        result = await self.skill.execute({})
        assert result["status"] == "error"
        assert "psutil" in result["error"].lower()

    @pytest.mark.asyncio
    @patch("skills.hardware.psutil")
    async def test_execute_general_exception(self, mock_psutil):
        class FakePsutilError(Exception): pass
        mock_psutil.Error = FakePsutilError
        mock_psutil.virtual_memory.side_effect = Exception("General failure")
        
        result = await self.skill.execute({})
        assert result["status"] == "error"
        assert "General failure" in result["error"]
