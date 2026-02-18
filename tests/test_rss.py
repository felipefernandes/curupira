import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from skills.rss import RssReadSkill, RssListSkill
from core import config
import asyncio

class TestRssReadSkill(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.skill = RssReadSkill()
        
    async def test_execute_validation(self):
        # Test Empty Input
        res_empty = await self.skill.execute({}, feed_identifier="")
        self.assertIn("error", res_empty)
        self.assertIn("Nome do feed", res_empty["error"])

        # Test Invalid Limit
        res_limit = await self.skill.execute({}, feed_identifier="TestFeed", limit=0)
        self.assertIn("error", res_limit)
        self.assertIn("Limite", res_limit["error"])

    async def test_execute_string_limit_conversion(self):
        # Test Limit as String (LLM behavior)
        # Should NOT raise TypeError, but cast to int
        with patch('skills.rss.config.RSS_FEEDS', {"TestFeed": "http://example.com/feed"}), \
             patch('skills.rss.feedparser.parse') as mock_parse:
            
            mock_feed = MagicMock()
            mock_feed.entries = []
            mock_parse.return_value = mock_feed
            
            # Passing string "5" should work
            try:
                await self.skill.execute({}, feed_identifier="TestFeed", limit="5")
            except TypeError:
                self.fail("TypeError raised when limit is a string")

    @patch('core.config.RSS_FEEDS', {"TestFeed": "http://example.com/feed"})
    @patch('skills.rss.feedparser.parse')
    async def test_execute_with_name_resolution(self, mock_parse):
        # Mock Feedparser
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [{"title": "Test Entry", "link": "http://link.com"}]
        mock_feed.feed = {"title": "Test Feed"}
        mock_parse.return_value = mock_feed
        
        # Execute with NAME "TestFeed"
        result = await self.skill.execute({}, feed_identifier="TestFeed")
        
        # Verify URL was resolved
        args, _ = mock_parse.call_args
        self.assertEqual(args[0], "http://example.com/feed")
        self.assertEqual(result['total_available'], 1)
        self.assertEqual(result['entries'][0]['title'], "Test Entry")

    @patch('core.config.RSS_FEEDS', {"TestFeed": "http://example.com/feed"})
    @patch('skills.rss.feedparser.parse')
    async def test_execute_with_case_insensitive_name(self, mock_parse):
        # Mock Feedparser
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = []
        mock_feed.feed = {"title": "Test Feed"}
        mock_parse.return_value = mock_feed
        
        # Execute with NAME "testfeed" (lower case)
        result = await self.skill.execute({}, feed_identifier="testfeed")
        
        # Verify URL was resolved
        args, _ = mock_parse.call_args
        self.assertEqual(args[0], "http://example.com/feed")

    @patch('core.config.RSS_FEEDS', {"TestFeed": "http://example.com/feed"})
    @patch('skills.rss.feedparser.parse')
    async def test_read_feed_missing_fields(self, mock_parse):
        # Mock Feed with missing optional fields
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.feed = {"title": "Test Feed"}
        # Entry with no fields
        mock_feed.entries = [{}]
        mock_parse.return_value = mock_feed
        
        result = await self.skill.execute({}, feed_identifier="TestFeed")
        
        entry = result['entries'][0]
        self.assertEqual(entry['title'], "Sem título")
        self.assertEqual(entry['link'], "")
        
    @patch('core.config.RSS_FEEDS', {"TestFeed": "http://example.com/feed"})
    @patch('skills.rss.feedparser.parse')
    async def test_read_feed_default_limit(self, mock_parse):
        # Mock Feed with 10 entries
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.feed = {"title": "Test Feed"}
        mock_feed.entries = [{"title": f"Entry {i}"} for i in range(10)]
        mock_parse.return_value = mock_feed
        
        # Default limit should be 5
        result = await self.skill.execute({}, feed_identifier="TestFeed")
        
        self.assertEqual(len(result['entries']), 5)
        self.assertEqual(result['entries'][0]['title'], "Entry 0")

    @patch('skills.rss.feedparser.parse')
    async def test_execute_with_url_blocked(self, mock_parse):
        # Arbitrary URL should now fail
        url = "http://direct.url.com/rss"
        result = await self.skill.execute({}, feed_identifier=url)
        
        # Verify it was BLOCKED (not parsed)
        self.assertIn("error", result)
        self.assertIn("Security", result.get("reason", ""))
        # Verify available feeds are listed
        self.assertIn("Opções disponíveis", result["error"])
        mock_parse.assert_not_called()

    @patch('core.config.RSS_FEEDS', {"TestFeed": "http://example.com/feed"})
    @patch('skills.rss.feedparser.parse')
    async def test_execute_failure(self, mock_parse):
        mock_feed = MagicMock()
        mock_feed.bozo = 1
        mock_feed.entries = []
        mock_feed.bozo_exception = Exception("Connection Refused")
        mock_parse.return_value = mock_feed
        
        # Use a VALID name so it passes security check
        result = await self.skill.execute({}, feed_identifier="TestFeed")
        
        self.assertIn("error", result)
        self.assertIn("Connection Refused", str(result))

    @patch('core.config.RSS_FEEDS', {"TestFeed": "http://example.com/feed"})
    @patch('skills.rss.asyncio.wait_for')
    async def test_read_feed_timeout(self, mock_wait_for):
        # Implement side effect to cleanup coroutine and raise error
        async def side_effect(fut, timeout):
            if asyncio.iscoroutine(fut):
                fut.close()
            raise asyncio.TimeoutError()

        mock_wait_for.side_effect = side_effect
        
        result = await self.skill.execute({}, feed_identifier="TestFeed")
        
        self.assertIn("error", result)
        self.assertIn("Timeout", result["error"])


class TestRssListSkill(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.skill = RssListSkill()

    async def test_skill_metadata(self):
        self.assertEqual(self.skill.name, "rss_list")
        self.assertTrue("RSS" in self.skill.display_name)

    @patch('core.config.RSS_FEEDS', {"G1": "http://g1.com", "Tech": "http://tech.com"})
    async def test_list_feeds(self):
        result = await self.skill.execute({})
        self.assertEqual(result['total'], 2)
        names = [f['name'] for f in result['feeds']]
        self.assertIn("G1", names)
        self.assertIn("Tech", names)

    @patch('core.config.RSS_FEEDS', {})
    async def test_list_feeds_empty(self):
        result = await self.skill.execute({})
        self.assertEqual(result['feeds'], [])
        self.assertIn("message", result)

if __name__ == '__main__':
    unittest.main()
