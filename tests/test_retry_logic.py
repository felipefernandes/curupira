
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os
import asyncio

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.agent import AgentBrain

class TestRetryLogic(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.agent = AgentBrain(provider='gemini', api_key='dummy', model_name='gemini-2.5-flash')
        # Mock logger to avoid clutter
        self.agent.logger = MagicMock()

    async def test_retry_success_after_failure(self):
        """Test that it retries and succeeds after a 429 error."""
        client_mock = MagicMock()
        model_mock = MagicMock()
        
        # Mock genai behavior
        # First call raises Exception("429"), Second call returns Success
        
        # We need to simulate the Method call: client.aio.models.generate_content
        # It's an async method
        
        # Define side effects
        valid_response = MagicMock()
        valid_response.candidates = [MagicMock()]
        valid_response.candidates[0].content.parts[0].text = "Success"
        
        # Error with code 429 attribute
        error_429 = Exception("Resource Exhausted")
        error_429.code = 429
        
        # AsyncMock for generate_content
        generate_content_mock = AsyncMock(side_effect=[error_429, valid_response])
        
        client_mock.aio.models.generate_content = generate_content_mock
        
        # Call _generate_with_retry
        # retries=3, initial_delay=0.1 to be fast
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
        
        generate_content_mock = AsyncMock(side_effect=error_str)
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
        self.assertEqual(generate_content_mock.call_count, 3) # Initial + 2 retries

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
            
        self.assertTrue("500" in str(cm.exception))
        self.assertEqual(generate_content_mock.call_count, 1)

if __name__ == '__main__':
    unittest.main()
