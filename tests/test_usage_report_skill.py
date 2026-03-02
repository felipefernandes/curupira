import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from skills.usage_report import UsageReportSkill
from skills.memory import MemoryManager

@pytest.fixture
def mock_memory():
    mgr = MagicMock(spec=MemoryManager)
    return mgr

@pytest.fixture
def skill(mock_memory):
    return UsageReportSkill(mock_memory)

class TestUsageReportSkill:
    @pytest.mark.asyncio
    async def test_execute_with_data(self, skill, mock_memory):
        mock_memory.get_usage_summary = AsyncMock(return_value={
            "groq": {"prompt_tokens": 1000000, "completion_tokens": 500000},
            "gemini": {"prompt_tokens": 2000000, "completion_tokens": 100000}
        })
        
        result = await skill.execute({})
        
        assert result["status"] == "success"
        report = result["data"]["report"]
        assert "GROQ" in report
        assert "GEMINI" in report
        
        # 1M groq prompt = 0.50
        # 500k groq comp = 0.40
        # Total groq = 0.90
        # 2M gemini prompt = 0.15
        # 100k gemini comp = 0.03
        # Total gemini = 0.18
        # Total Estimated = 1.08
        
        assert "Custo Total Estimado: $1.08000 USD" in report

    @pytest.mark.asyncio
    async def test_execute_empty(self, skill, mock_memory):
        mock_memory.get_usage_summary = AsyncMock(return_value={})
        
        result = await skill.execute({})
        assert result["status"] == "success"
        assert "Nenhum consumo de tokens registrado" in result["data"]["message"]

    @pytest.mark.asyncio
    async def test_execute_error(self, skill, mock_memory):
        mock_memory.get_usage_summary = AsyncMock(side_effect=Exception("DB connection error"))
        
        result = await skill.execute({})
        assert result["status"] == "error"
        assert "Erro ao consultar o banco de dados" in result["error"]
