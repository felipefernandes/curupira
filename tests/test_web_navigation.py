import unittest
from unittest.mock import patch, AsyncMock, MagicMock
import httpx

from skills.web_navigation import WebNavigationSkill, _MAX_TEXT_CHARS


class TestWebNavigationSkillMetadata(unittest.TestCase):
    def setUp(self):
        self.skill = WebNavigationSkill()

    def test_name(self):
        self.assertEqual(self.skill.name, "web_navigation")

    def test_display_name(self):
        self.assertIn("Web", self.skill.display_name)

    def test_skill_group(self):
        self.assertEqual(self.skill.skill_group, "web_navigation")
        self.assertEqual(self.skill.skill_group_emoji, "🌐")

    def test_parameters_schema(self):
        params = self.skill.parameters
        self.assertEqual(params["type"], "object")
        self.assertIn("action", params["properties"])
        self.assertIn("url", params["properties"])
        self.assertEqual(params["required"], ["action", "url"])


class TestWebNavigationSkillExecute(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.skill = WebNavigationSkill()

    async def test_invalid_action(self):
        result = await self.skill.execute({}, action="delete", url="http://example.com")
        self.assertEqual(result["status"], "error")
        self.assertIn("Ação inválida", result["error"])

    async def test_empty_url(self):
        result = await self.skill.execute({}, action="extract", url="")
        self.assertEqual(result["status"], "error")
        self.assertIn("URL não fornecida", result["error"])

    async def test_missing_action(self):
        result = await self.skill.execute({}, action="", url="http://example.com")
        self.assertEqual(result["status"], "error")

    @patch("skills.web_navigation.httpx.AsyncClient")
    @patch("skills.web_navigation.trafilatura.extract")
    async def test_extract_success(self, mock_extract, mock_client_cls):
        mock_extract.return_value = "Texto limpo do artigo."

        mock_response = MagicMock()
        mock_response.text = "<html><body>Artigo</body></html>"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await self.skill.execute(
            {}, action="extract", url="http://example.com/article"
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["text"], "Texto limpo do artigo.")
        self.assertEqual(result["data"]["url"], "http://example.com/article")
        self.assertIn("length", result["data"])

    @patch("skills.web_navigation.httpx.AsyncClient")
    @patch("skills.web_navigation.trafilatura.extract")
    async def test_summarize_returns_message(self, mock_extract, mock_client_cls):
        mock_extract.return_value = "Conteúdo do site."

        mock_response = MagicMock()
        mock_response.text = "<html><body>Conteúdo</body></html>"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await self.skill.execute(
            {}, action="summarize", url="http://example.com/article"
        )

        self.assertEqual(result["status"], "success")
        self.assertIn("Resuma", result["message"])
        self.assertEqual(result["data"]["text"], "Conteúdo do site.")

    @patch("skills.web_navigation.httpx.AsyncClient")
    async def test_http_timeout(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("timeout")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await self.skill.execute(
            {}, action="extract", url="http://example.com/slow"
        )

        self.assertEqual(result["status"], "error")
        self.assertIn("Timeout", result["error"])

    @patch("skills.web_navigation.httpx.AsyncClient")
    async def test_http_404(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await self.skill.execute(
            {}, action="extract", url="http://example.com/missing"
        )

        self.assertEqual(result["status"], "error")
        self.assertIn("404", result["error"])

    @patch("skills.web_navigation.httpx.AsyncClient")
    async def test_connection_error(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.RequestError("DNS failure")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await self.skill.execute(
            {}, action="extract", url="http://invalid.example"
        )

        self.assertEqual(result["status"], "error")
        self.assertIn("Erro de conexão", result["error"])

    @patch("skills.web_navigation.httpx.AsyncClient")
    @patch("skills.web_navigation.trafilatura.extract")
    async def test_extraction_returns_none(self, mock_extract, mock_client_cls):
        mock_extract.return_value = None

        mock_response = MagicMock()
        mock_response.text = "<html><script>app()</script></html>"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await self.skill.execute(
            {}, action="extract", url="http://example.com/spa"
        )

        self.assertEqual(result["status"], "error")
        self.assertIn("extrair texto", result["error"])

    @patch("skills.web_navigation.httpx.AsyncClient")
    @patch("skills.web_navigation.trafilatura.extract")
    async def test_text_truncation(self, mock_extract, mock_client_cls):
        long_text = "A" * (_MAX_TEXT_CHARS + 5000)
        mock_extract.return_value = long_text

        mock_response = MagicMock()
        mock_response.text = "<html><body>" + long_text + "</body></html>"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await self.skill.execute(
            {}, action="extract", url="http://example.com/huge"
        )

        self.assertEqual(result["status"], "success")
        self.assertIn("truncado", result["data"]["text"])
        self.assertTrue(len(result["data"]["text"]) <= _MAX_TEXT_CHARS + 100)


if __name__ == "__main__":
    unittest.main()
