import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import json
import os
from core.agent import AgentBrain
from core import config

class TestAgentReflection(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.brain = AgentBrain("groq", "fake_key")
        
    @patch('core.config.REFLECTION_ENABLED', True)
    @patch('core.config.GROQ_API_KEY', 'fake_key')
    @patch('core.agent.AgentBrain._get_groq_client')
    async def test_reflect_silence_groq(self, mock_get_client):
        # Mock Client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock Response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "SILENCE"
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        context = {"time": "10:00"}
        result = await self.brain.reflect(context)
        
        self.assertIsNone(result)

    @patch('core.config.REFLECTION_ENABLED', True)
    @patch('core.config.GROQ_API_KEY', 'fake_key')
    @patch('core.agent.AgentBrain._get_groq_client')
    async def test_reflect_speaking_groq(self, mock_get_client):
        # Mock Client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock Response
        msg = "Hello user, drink water."
        mock_response = MagicMock()
        mock_response.choices[0].message.content = msg
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        context = {"time": "10:00"}
        result = await self.brain.reflect(context)
        
        self.assertEqual(result, msg)
        
    @patch('core.config.REFLECTION_ENABLED', False)
    async def test_reflect_disabled(self):
        result = await self.brain.reflect({})
        self.assertIsNone(result)

    @patch('core.config.REFLECTION_ENABLED', True)
    @patch('core.config.GROQ_API_KEY', 'fake_key')
    @patch('core.agent.AgentBrain._get_groq_client')
    async def test_reflect_fuzzy_silence(self, mock_get_client):
        # Iara likely flagged this: "SILENCE." or "silence" should work
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "SILENCE."
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        result = await self.brain.reflect({})
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
