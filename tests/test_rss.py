import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from skills.rss import RssReadSkill, RssListSkill
import asyncio

class TestRssReadSkill(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.skill = RssReadSkill()
        from skills.rss import _translation_cache
        _translation_cache.clear()
        
    async def test_execute_validation(self):
        # Test Empty Input
        res_empty = await self.skill.execute({}, feed_identifier="")
        self.assertEqual(res_empty["status"], "error")
        self.assertIn("Nome do feed", res_empty["error"])

        # Test Invalid Limit
        res_limit = await self.skill.execute({}, feed_identifier="TestFeed", limit=0)
        self.assertEqual(res_limit["status"], "error")
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
        self.assertEqual(result['data']['total_available'], 1)
        self.assertEqual(result['data']['entries'][0]['title'], "Test Entry")

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
        await self.skill.execute({}, feed_identifier="testfeed")
        
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
        
        entry = result['data']['entries'][0]
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
        
        self.assertEqual(len(result['data']['entries']), 5)
        self.assertEqual(result['data']['entries'][0]['title'], "Entry 0")

    @patch('skills.rss.feedparser.parse')
    async def test_execute_with_url_blocked(self, mock_parse):
        # Arbitrary URL should now fail
        url = "http://direct.url.com/rss"
        result = await self.skill.execute({}, feed_identifier=url)
        
        # Verify it was BLOCKED (not parsed)
        self.assertEqual(result["status"], "error")
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
        
        self.assertEqual(result["status"], "error")
        self.assertIn("Connection Refused", str(result))

    @patch('core.config.RSS_FEEDS', {"TestFeed": "http://example.com/feed"})
    @patch('skills.rss.asyncio.wait_for')
    @patch('skills.rss.asyncio.to_thread', new_callable=MagicMock)
    async def test_read_feed_timeout(self, mock_to_thread, mock_wait_for):
        # Setup mock_to_thread to return an awaitable (coroutine mock)
        async def mock_coro(*args, **kwargs):
            return []
        mock_to_thread.side_effect = mock_coro

        # Setup mock_wait_for to raise TimeoutError AND close the coro
        async def side_effect_wait(coro, timeout):
             coro.close() # Avoid RuntimeWarning
             raise asyncio.TimeoutError()

        mock_wait_for.side_effect = side_effect_wait
        
        result = await self.skill.execute({}, feed_identifier="TestFeed")
        
        self.assertEqual(result["status"], "error")
        self.assertIn("Timeout", result["error"])

    @patch('core.config.RSS_FEEDS', {"GlobalNews": "http://example.com/global"})
    @patch('core.config.RSS_FEEDS_LANGUAGES', {"GlobalNews": "EN"})
    @patch('skills.rss.feedparser.parse')
    async def test_read_feed_auto_translation(self, mock_parse):
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.feed = {"title": "Global News"}
        mock_feed.entries = [{"title": "Original Title", "link": "http://link.com"}]
        mock_parse.return_value = mock_feed
        
        # Mock the translation method
        with patch.object(self.skill, '_translate_titles', new_callable=AsyncMock) as mock_translate:
            mock_translate.return_value = ["Título Traduzido"]
            
            result = await self.skill.execute({}, feed_identifier="GlobalNews", auto_translate=True)
            
            # Verify translation was called
            mock_translate.assert_called_once_with(["Original Title"], "EN")
            
            # Verify the entry title was replaced and tagged
            entry = result['data']['entries'][0]
            self.assertEqual(entry['title'], "Título Traduzido (EN)")
            
    @patch('core.config.RSS_FEEDS', {"LocalNews": "http://example.com/local"})
    @patch('core.config.RSS_FEEDS_LANGUAGES', {}) # Empty = PT-BR (no translation)
    @patch('skills.rss.feedparser.parse')
    async def test_read_feed_no_translation_needed(self, mock_parse):
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.feed = {"title": "Local News"}
        mock_feed.entries = [{"title": "Título Original", "link": "http://link.com"}]
        mock_parse.return_value = mock_feed
        
        with patch.object(self.skill, '_translate_titles', new_callable=AsyncMock) as mock_translate:
            result = await self.skill.execute({}, feed_identifier="LocalNews", auto_translate=True)
            
            # Verify translation was NOT called
            mock_translate.assert_not_called()
            
            # Verify the entry title remained the same
            entry = result['data']['entries'][0]
            self.assertEqual(entry['title'], "Título Original")

    async def test_translate_titles_ptbr_check(self):
        titles = ["Test 1"]
        # It should skip translation if language is PT-BR
        res = await self.skill._translate_titles(titles, "PT-BR")
        self.assertEqual(res, titles)
        res_pt = await self.skill._translate_titles(titles, "pt")
        self.assertEqual(res_pt, titles)

    @patch("skills.rss.config")
    async def test_translate_titles_groq(self, mock_config):
        mock_config.AI_PROVIDER = "groq"
        titles = ["Hello"]
        
        with patch.object(self.skill, '_call_groq', new_callable=AsyncMock) as mock_groq:
            mock_groq.return_value = "- Olá"
            res = await self.skill._translate_titles(titles, "EN")
            self.assertEqual(res, ["Olá"])
            mock_groq.assert_called_once()
            
    def test_parse_translation(self):
        # Normal
        res = self.skill._parse_translation("- Olá\n- Mundo", 2)
        self.assertEqual(res, ["Olá", "Mundo"])
        
        # With numbers
        res2 = self.skill._parse_translation("1. Olá\n2. Mundo", 2)
        self.assertEqual(res2, ["Olá", "Mundo"])
        
        # Mismatch
        res3 = self.skill._parse_translation("Olá", 2)
        self.assertEqual(res3, [])

    async def test_translate_titles_cache(self):
        from skills.rss import _translation_cache
        _translation_cache.clear()
        
        titles = ["Something new"]
        with patch.object(self.skill, '_call_groq', new_callable=AsyncMock) as mock_groq, \
             patch("skills.rss.config") as mock_config:
            mock_config.AI_PROVIDER = "groq"
            mock_groq.return_value = "Algo novo"
            
            # First call
            res1 = await self.skill._translate_titles(titles, "EN")
            self.assertEqual(res1, ["Algo novo"])
            self.assertEqual(mock_groq.call_count, 1)
            
            # Second call (should hit cache)
            res2 = await self.skill._translate_titles(titles, "EN")
            self.assertEqual(res2, ["Algo novo"])
            self.assertEqual(mock_groq.call_count, 1)  # Stays 1
            
        _translation_cache.clear()

    @patch("skills.rss.config")
    async def test_translate_titles_gemini(self, mock_config):
        mock_config.AI_PROVIDER = "gemini"
        titles = ["Hello World"]

        with patch.object(self.skill, '_call_gemini', new_callable=AsyncMock) as mock_gemini:
            mock_gemini.return_value = "Olá Mundo"
            res = await self.skill._translate_titles(titles, "EN")
            self.assertEqual(res, ["Olá Mundo"])
            mock_gemini.assert_called_once()

    @patch("skills.rss.config")
    async def test_translate_titles_unknown_provider(self, mock_config):
        mock_config.AI_PROVIDER = "openai"
        titles = ["Hello"]
        res = await self.skill._translate_titles(titles, "EN")
        # Should fallback to original titles
        self.assertEqual(res, titles)

    @patch("skills.rss.config")
    async def test_translate_titles_empty_response_fallback(self, mock_config):
        mock_config.AI_PROVIDER = "groq"
        titles = ["Hello"]

        with patch.object(self.skill, '_call_groq', new_callable=AsyncMock) as mock_groq:
            mock_groq.return_value = ""  # Empty response
            res = await self.skill._translate_titles(titles, "EN")
            # Should fallback to original titles
            self.assertEqual(res, titles)

    @patch("skills.rss.config")
    async def test_translate_titles_exception_fallback(self, mock_config):
        mock_config.AI_PROVIDER = "groq"
        titles = ["Hello"]

        with patch.object(self.skill, '_call_groq', new_callable=AsyncMock) as mock_groq:
            mock_groq.side_effect = RuntimeError("API timeout")
            res = await self.skill._translate_titles(titles, "EN")
            # Should fallback to original titles
            self.assertEqual(res, titles)

    async def test_translate_titles_empty_list(self):
        res = await self.skill._translate_titles([], "EN")
        self.assertEqual(res, [])

    def test_parse_translation_empty_text(self):
        res = self.skill._parse_translation("", 2)
        self.assertEqual(res, [])

    @patch("os.getenv", return_value=None)
    @patch("skills.rss.config")
    async def test_call_groq_no_api_key(self, mock_config, mock_getenv):
        mock_config.GROQ_API_KEY = None
        res = await self.skill._call_groq("test prompt")
        self.assertEqual(res, "")

    @patch("os.getenv", return_value="fake-key")
    @patch("skills.rss.config")
    async def test_call_groq_success(self, mock_config, mock_getenv):
        mock_config.GROQ_MODEL = "test-model"

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "  Translated  "

        with patch("groq.AsyncGroq") as MockGroq:
            mock_client = AsyncMock()
            MockGroq.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            res = await self.skill._call_groq("test prompt")
            self.assertEqual(res, "Translated")

    @patch("os.getenv", return_value=None)
    @patch("skills.rss.config")
    async def test_call_gemini_no_api_key(self, mock_config, mock_getenv):
        mock_config.GEMINI_API_KEY = None
        res = await self.skill._call_gemini("test prompt")
        self.assertEqual(res, "")

    @patch("os.getenv", return_value="fake-key")
    @patch("skills.rss.config")
    async def test_call_gemini_no_candidates(self, mock_config, mock_getenv):
        mock_config.GEMINI_MODEL = "test-model"

        mock_response = MagicMock()
        mock_response.candidates = []

        with patch("google.genai.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            res = await self.skill._call_gemini("test prompt")
            self.assertEqual(res, "")

    @patch("os.getenv", return_value="fake-key")
    @patch("skills.rss.config")
    async def test_call_gemini_success(self, mock_config, mock_getenv):
        mock_config.GEMINI_MODEL = "test-model"

        mock_part = MagicMock()
        mock_part.text = "  Traduzido  "
        mock_candidate = MagicMock()
        mock_candidate.content.parts = [mock_part]
        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]

        with patch("google.genai.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            res = await self.skill._call_gemini("test prompt")
            self.assertEqual(res, "Traduzido")

    @patch('core.config.RSS_FEEDS', {"GlobalNews": "http://example.com/global"})
    @patch('core.config.RSS_FEEDS_LANGUAGES', {"GlobalNews": "EN"})
    @patch('skills.rss.feedparser.parse')
    async def test_read_feed_auto_translate_disabled(self, mock_parse):
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.feed = {"title": "Global News"}
        mock_feed.entries = [{"title": "Original Title", "link": "http://link.com"}]
        mock_parse.return_value = mock_feed

        with patch.object(self.skill, '_translate_titles', new_callable=AsyncMock) as mock_translate:
            result = await self.skill.execute({}, feed_identifier="GlobalNews", auto_translate=False)
            mock_translate.assert_not_called()
            entry = result['data']['entries'][0]
            self.assertEqual(entry['title'], "Original Title")

class TestRssSkillGroup(unittest.TestCase):
    def test_rss_read_skill_group(self):
        skill = RssReadSkill()
        self.assertEqual(skill.skill_group, "rss")
        self.assertEqual(skill.skill_group_emoji, "📰")

    def test_rss_list_skill_group(self):
        skill = RssListSkill()
        self.assertEqual(skill.skill_group, "rss")
        self.assertEqual(skill.skill_group_emoji, "📰")


class TestRssListSkill(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.skill = RssListSkill()

    async def test_skill_metadata(self):
        self.assertEqual(self.skill.name, "rss_list")
        self.assertTrue("RSS" in self.skill.display_name)

    @patch('core.config.RSS_FEEDS', {"G1": "http://g1.com", "Tech": "http://tech.com"})
    async def test_list_feeds(self):
        result = await self.skill.execute({})
        self.assertEqual(result['data']['total'], 2)
        names = [f['name'] for f in result['data']['feeds']]
        self.assertIn("G1", names)
        self.assertIn("Tech", names)

    @patch('core.config.RSS_FEEDS', {})
    async def test_list_feeds_empty(self):
        result = await self.skill.execute({})
        self.assertEqual(result['data']['feeds'], [])
        self.assertIn("message", result)

if __name__ == '__main__':
    unittest.main()
