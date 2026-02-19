
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os
import asyncio
import json

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.agent import AgentBrain

class TestRetryLogic(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Patch config to have a valid key for AgentBrain instantiation
        self.config_patcher = patch('core.agent.config.GEMINI_API_KEY', 'dummy_test_key')
        self.config_patcher.start()
        
        self.agent = AgentBrain(provider='gemini', model_name='gemini-2.5-flash')
        # Mock logger to avoid clutter
        self.agent.logger = MagicMock()

    def tearDown(self):
        self.config_patcher.stop()

    # @unittest.skip("Flaky mock behavior in this environment. Logic verified by test_retry_exhaustion.")
    async def test_retry_success_after_failure(self):
        """Test that it retries and succeeds after a 429 error."""
        client_mock = MagicMock()
        
        # Define side effects
        valid_response = MagicMock()
        valid_response.candidates = [MagicMock()]
        valid_response.candidates[0].content.parts[0].text = "Success"
        
        # Error with code 429 attribute
        error_429 = Exception("429 RESOURCE_EXHAUSTED")
        error_429.code = 429
        
        # AsyncMock for generate_content
        # Provide enough side effects to cover retries
        generate_content_mock = AsyncMock(side_effect=[error_429, valid_response, valid_response])
        client_mock.aio.models.generate_content = generate_content_mock
        
        # Call _generate_with_retry
        result = await self.agent._generate_with_retry(
            client=client_mock, 
            model='model', 
            contents='test', 
            config={}, 
            retries=3, 
            initial_delay=0.01
        )
        
        self.assertEqual(result, valid_response)
        self.assertEqual(generate_content_mock.call_count, 2)
        
    async def test_retry_exhaustion(self):
        """Test that it raises exception after max retries."""
        client_mock = MagicMock()
        error_str = Exception("429 RESOURCE_EXHAUSTED")
        generate_content_mock = AsyncMock(side_effect=[error_str] * 10)
        client_mock.aio.models.generate_content = generate_content_mock
        
        with self.assertRaises(Exception) as cm:
            await self.agent._generate_with_retry(
                client=client_mock, 
                model='model', 
                contents='test', 
                config={}, 
                retries=2, 
                initial_delay=0.01
            )
        self.assertTrue("429" in str(cm.exception))

    async def test_no_retry_for_other_errors(self):
        """Test that it does NOT retry for non-429 errors."""
        client_mock = MagicMock()
        error_500 = Exception("500 Internal Server Error")
        generate_content_mock = AsyncMock(side_effect=error_500)
        client_mock.aio.models.generate_content = generate_content_mock
        
        with self.assertRaises(Exception) as cm:
            await self.agent._generate_with_retry(
                client=client_mock, 
                model='model', 
                contents='test', 
                config={}, 
                retries=3, 
                initial_delay=0.01
            )
        self.assertEqual(generate_content_mock.call_count, 1)

    async def test_process_dory_fix_multi_part(self):
        """
        Test 'Dory Fix': valid tool call in the SECOND part of the response 
        should be executed, ignoring the text in the FIRST part.
        """
        # Mock dependencies
        self.agent._get_gemini_client = MagicMock(return_value=MagicMock())
        # Mock _generate_with_retry to return our multi-part response
        
        # Create Multi-part response
        # Part 1: Text "Vou buscar..."
        part1 = MagicMock()
        part1.text = "Vou buscar sua notícia..."
        part1.function_call = None
        
        # Part 2: Function Call
        part2 = MagicMock()
        part2.text = None
        part2.function_call.name = "rss_list"
        part2.function_call.args = {}
        
        response_mock = MagicMock()
        response_mock.candidates = [MagicMock()]
        response_mock.candidates[0].content.parts = [part1, part2]
        
        # Mock _generate_with_retry on the agent instance (since we are testing process which calls it)
        self.agent._generate_with_retry = AsyncMock(return_value=response_mock)
        
        # Mock _execute_tool_call
        self.agent._execute_tool_call = AsyncMock(return_value='{"status": "ok"}')
        
        # Mock config
        with patch('core.agent.config.AI_PROVIDER', 'gemini'), \
             patch('core.agent.config.GEMINI_API_KEY', 'dummy'):
                 
            # Force agent provider to gemini
            self.agent.provider = 'gemini'
            
            # We must break the infinite loop in process (it loops max_turns)
            # We can do this by making the second call to generate return something that exits?
            # Or just check that _execute_tool_call was called.
            
            # Actually process calls generate -> execute -> generate (with tool result).
            # We'll mock the SECOND generate call to return final text to exit loop.
            
            final_response = MagicMock()
            final_response.candidates = [MagicMock()]
            final_response.candidates[0].content.parts = [MagicMock(text="Aqui está.", function_call=None)]
            
            self.agent._generate_with_retry = AsyncMock(side_effect=[response_mock, final_response])

            context = {}
            result = await self.agent.process("Mensagem do usuario", context)
            
            # Assertions
            # 1. Verify tool was called
            self.agent._execute_tool_call.assert_called_with("rss_list", {}, context)
            
            # 2. Verify result contains final text
            self.assertEqual(result, "Aqui está.")

if __name__ == '__main__':
    unittest.main()
