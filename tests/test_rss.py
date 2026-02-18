import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from skills.rss import RssReadSkill
from core import config

class TestRssReadSkill(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.skill = RssReadSkill()
        
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
        result = await self.skill.execute({}, url="TestFeed")
        
        # Verify URL was resolved
        args, _ = mock_parse.call_args
        self.assertEqual(args[0], "http://example.com/feed")
        self.assertEqual(result['total_available'], 1)

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
        result = await self.skill.execute({}, url="testfeed")
        
        # Verify URL was resolved
        args, _ = mock_parse.call_args
        self.assertEqual(args[0], "http://example.com/feed")

    @patch('skills.rss.feedparser.parse')
    async def test_execute_with_url_blocked(self, mock_parse):
        # Arbitrary URL should now fail
        url = "http://direct.url.com/rss"
        result = await self.skill.execute({}, url=url)
        
        # Verify it was BLOCKED (not parsed)
        self.assertIn("error", result)
        self.assertIn("Security", result.get("reason", ""))
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
        result = await self.skill.execute({}, url="TestFeed")
        
        self.assertIn("error", result)
        self.assertIn("Connection Refused", str(result))

if __name__ == '__main__':
    unittest.main()
