"""
Tests for Job Hunter skills.
Ref: Issue #95
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from skills.job_hunter import JobHunterGetDefaultsSkill, JobHunterRunSearchSkill


FAKE_URL = "https://job-hunter.vercel.app"
FAKE_TOKEN = "secret123"


class TestJobHunterRunSearchSkill(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.skill = JobHunterRunSearchSkill()

    # --- Metadata ---

    def test_metadata(self):
        self.assertEqual(self.skill.name, "job_hunter_run_search")
        self.assertIn("vaga", self.skill.description.lower())
        self.assertIn("Buscar", self.skill.display_name)
        self.assertEqual(self.skill.skill_group, "jobs")
        self.assertEqual(self.skill.skill_group_emoji, "💼")

    def test_parameters_all_optional(self):
        params = self.skill.parameters
        self.assertEqual(params.get("required"), [])
        self.assertIn("sources", params["properties"])
        self.assertIn("keywords", params["properties"])
        self.assertIn("prompt_override", params["properties"])
        self.assertIn("score_cutoff", params["properties"])

    # --- Config validation ---

    @patch("skills.job_hunter.config.JOB_HUNTER_URL", "")
    async def test_missing_url_returns_error(self):
        result = await self.skill.execute({})
        self.assertIn("error", result)
        self.assertIn("JOB_HUNTER_URL", result["error"])

    @patch("skills.job_hunter.config.JOB_HUNTER_URL", FAKE_URL)
    @patch("skills.job_hunter.config.JOB_HUNTER_TOKEN", "")
    async def test_missing_token_returns_error(self):
        result = await self.skill.execute({})
        self.assertIn("error", result)
        self.assertIn("JOB_HUNTER_TOKEN", result["error"])

    # --- Successful search ---

    @patch("skills.job_hunter.config.JOB_HUNTER_URL", FAKE_URL)
    @patch("skills.job_hunter.config.JOB_HUNTER_TOKEN", FAKE_TOKEN)
    @patch("skills.job_hunter.config.JOB_HUNTER_SOURCES", None)
    @patch("skills.job_hunter.config.JOB_HUNTER_KEYWORDS", None)
    @patch("skills.job_hunter.config.JOB_HUNTER_SCORE_CUTOFF", None)
    @patch("skills.job_hunter.requests.post")
    async def test_run_search_no_overrides(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success", "fetched": 10, "approved": 2}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = await self.skill.execute({})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["fetched"], 10)
        self.assertEqual(result["data"]["approved"], 2)
        # Body should be empty (no overrides)
        _, call_kwargs = mock_post.call_args
        self.assertEqual(call_kwargs["json"], {})

    @patch("skills.job_hunter.config.JOB_HUNTER_URL", FAKE_URL)
    @patch("skills.job_hunter.config.JOB_HUNTER_TOKEN", FAKE_TOKEN)
    @patch("skills.job_hunter.config.JOB_HUNTER_SOURCES", None)
    @patch("skills.job_hunter.config.JOB_HUNTER_KEYWORDS", None)
    @patch("skills.job_hunter.config.JOB_HUNTER_SCORE_CUTOFF", None)
    @patch("skills.job_hunter.requests.post")
    async def test_run_search_with_prompt_override(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success", "fetched": 4, "approved": 1}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        await self.skill.execute({}, prompt_override="Avalie vagas de jogos indie.")

        _, call_kwargs = mock_post.call_args
        self.assertEqual(call_kwargs["json"]["prompt_override"], "Avalie vagas de jogos indie.")

    @patch("skills.job_hunter.config.JOB_HUNTER_URL", FAKE_URL)
    @patch("skills.job_hunter.config.JOB_HUNTER_TOKEN", FAKE_TOKEN)
    @patch("skills.job_hunter.config.JOB_HUNTER_SOURCES", None)
    @patch("skills.job_hunter.config.JOB_HUNTER_KEYWORDS", None)
    @patch("skills.job_hunter.config.JOB_HUNTER_SCORE_CUTOFF", None)
    async def test_invalid_sources_type_returns_error(self):
        result = await self.skill.execute({}, sources=[1, 2, 3])
        self.assertIn("error", result)
        self.assertIn("sources", result["error"].lower())

    @patch("skills.job_hunter.config.JOB_HUNTER_URL", FAKE_URL)
    @patch("skills.job_hunter.config.JOB_HUNTER_TOKEN", FAKE_TOKEN)
    @patch("skills.job_hunter.config.JOB_HUNTER_SOURCES", None)
    @patch("skills.job_hunter.config.JOB_HUNTER_KEYWORDS", None)
    @patch("skills.job_hunter.config.JOB_HUNTER_SCORE_CUTOFF", None)
    async def test_invalid_keywords_type_returns_error(self):
        result = await self.skill.execute({}, keywords=[True, False])
        self.assertIn("error", result)
        self.assertIn("keywords", result["error"].lower())

    @patch("skills.job_hunter.config.JOB_HUNTER_URL", FAKE_URL)
    @patch("skills.job_hunter.config.JOB_HUNTER_TOKEN", FAKE_TOKEN)
    @patch("skills.job_hunter.config.JOB_HUNTER_SOURCES", None)
    @patch("skills.job_hunter.config.JOB_HUNTER_KEYWORDS", None)
    @patch("skills.job_hunter.config.JOB_HUNTER_SCORE_CUTOFF", None)
    @patch("skills.job_hunter.requests.post")
    async def test_run_search_with_llm_overrides(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success", "fetched": 5, "approved": 1}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = await self.skill.execute(
            {},
            sources=["gupy.io"],
            keywords=["Product Manager"],
            score_cutoff=8.0,
        )

        self.assertEqual(result["status"], "success")
        _, call_kwargs = mock_post.call_args
        body = call_kwargs["json"]
        self.assertEqual(body["sources"], ["gupy.io"])
        self.assertEqual(body["keywords"], ["Product Manager"])
        self.assertEqual(body["score_cutoff"], 8.0)

    @patch("skills.job_hunter.config.JOB_HUNTER_URL", FAKE_URL)
    @patch("skills.job_hunter.config.JOB_HUNTER_TOKEN", FAKE_TOKEN)
    @patch("skills.job_hunter.config.JOB_HUNTER_SOURCES", ["lever.co"])
    @patch("skills.job_hunter.config.JOB_HUNTER_KEYWORDS", ["Agente de IA"])
    @patch("skills.job_hunter.config.JOB_HUNTER_SCORE_CUTOFF", 7.5)
    @patch("skills.job_hunter.requests.post")
    async def test_run_search_uses_personal_env_overrides(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success", "fetched": 3, "approved": 0}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = await self.skill.execute({})

        _, call_kwargs = mock_post.call_args
        body = call_kwargs["json"]
        self.assertEqual(body["sources"], ["lever.co"])
        self.assertEqual(body["keywords"], ["Agente de IA"])
        self.assertEqual(body["score_cutoff"], 7.5)

    @patch("skills.job_hunter.config.JOB_HUNTER_URL", FAKE_URL)
    @patch("skills.job_hunter.config.JOB_HUNTER_TOKEN", FAKE_TOKEN)
    @patch("skills.job_hunter.config.JOB_HUNTER_SOURCES", ["lever.co"])
    @patch("skills.job_hunter.config.JOB_HUNTER_KEYWORDS", ["Agente de IA"])
    @patch("skills.job_hunter.config.JOB_HUNTER_SCORE_CUTOFF", 7.5)
    @patch("skills.job_hunter.requests.post")
    async def test_llm_overrides_take_priority_over_env(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success", "fetched": 2, "approved": 1}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        await self.skill.execute(
            {},
            sources=["gupy.io"],
            keywords=["Producer"],
            score_cutoff=9.0,
        )

        _, call_kwargs = mock_post.call_args
        body = call_kwargs["json"]
        # LLM args should win over env config
        self.assertEqual(body["sources"], ["gupy.io"])
        self.assertEqual(body["keywords"], ["Producer"])
        self.assertEqual(body["score_cutoff"], 9.0)

    # --- Error handling ---

    @patch("skills.job_hunter.config.JOB_HUNTER_URL", FAKE_URL)
    @patch("skills.job_hunter.config.JOB_HUNTER_TOKEN", FAKE_TOKEN)
    @patch("skills.job_hunter.config.JOB_HUNTER_SOURCES", None)
    @patch("skills.job_hunter.config.JOB_HUNTER_KEYWORDS", None)
    @patch("skills.job_hunter.config.JOB_HUNTER_SCORE_CUTOFF", None)
    @patch("skills.job_hunter.asyncio.wait_for")
    async def test_timeout_returns_error(self, mock_wait_for):
        async def raise_timeout(coro, timeout):
            coro.close()
            raise asyncio.TimeoutError()

        mock_wait_for.side_effect = raise_timeout

        result = await self.skill.execute({})
        self.assertIn("error", result)
        self.assertIn("Timeout", result["error"])

    @patch("skills.job_hunter.config.JOB_HUNTER_URL", FAKE_URL)
    @patch("skills.job_hunter.config.JOB_HUNTER_TOKEN", FAKE_TOKEN)
    @patch("skills.job_hunter.config.JOB_HUNTER_SOURCES", None)
    @patch("skills.job_hunter.config.JOB_HUNTER_KEYWORDS", None)
    @patch("skills.job_hunter.config.JOB_HUNTER_SCORE_CUTOFF", None)
    @patch("skills.job_hunter.requests.post")
    async def test_http_error_returns_error(self, mock_post):
        import requests as req

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        http_err = req.HTTPError(response=mock_response)
        mock_post.return_value = MagicMock(
            raise_for_status=MagicMock(side_effect=http_err),
        )

        result = await self.skill.execute({})
        self.assertIn("error", result)
        self.assertIn("401", result["error"])

    @patch("skills.job_hunter.config.JOB_HUNTER_URL", FAKE_URL)
    @patch("skills.job_hunter.config.JOB_HUNTER_TOKEN", FAKE_TOKEN)
    @patch("skills.job_hunter.config.JOB_HUNTER_SOURCES", None)
    @patch("skills.job_hunter.config.JOB_HUNTER_KEYWORDS", None)
    @patch("skills.job_hunter.config.JOB_HUNTER_SCORE_CUTOFF", None)
    @patch("skills.job_hunter.requests.post")
    async def test_connection_error_returns_error(self, mock_post):
        import requests as req

        mock_post.side_effect = req.ConnectionError("Connection refused")

        result = await self.skill.execute({})
        self.assertIn("error", result)
        self.assertIn("conexão", result["error"].lower())


class TestJobHunterGetDefaultsSkill(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.skill = JobHunterGetDefaultsSkill()

    def test_metadata(self):
        self.assertEqual(self.skill.name, "job_hunter_get_defaults")
        self.assertIn("Config", self.skill.display_name)
        self.assertIn("padrão", self.skill.description.lower())
        self.assertEqual(self.skill.parameters.get("required"), [])
        self.assertEqual(self.skill.skill_group, "jobs")
        self.assertEqual(self.skill.skill_group_emoji, "💼")

    @patch("skills.job_hunter.config.JOB_HUNTER_URL", "")
    async def test_missing_url_returns_error(self):
        result = await self.skill.execute({})
        self.assertIn("error", result)

    @patch("skills.job_hunter.config.JOB_HUNTER_URL", FAKE_URL)
    @patch("skills.job_hunter.config.JOB_HUNTER_TOKEN", FAKE_TOKEN)
    @patch("skills.job_hunter.requests.get")
    async def test_get_defaults_success(self, mock_get):
        expected = {
            "sources": ["gupy.io"],
            "keywords": ["Product Manager"],
            "score_cutoff": 7.0,
        }
        mock_response = MagicMock()
        mock_response.json.return_value = expected
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = await self.skill.execute({})

        self.assertEqual(result["data"]["sources"], ["gupy.io"])
        self.assertEqual(result["data"]["score_cutoff"], 7.0)
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertIn("/api/config_endpoint", call_args[0][0])

    @patch("skills.job_hunter.config.JOB_HUNTER_URL", FAKE_URL)
    @patch("skills.job_hunter.config.JOB_HUNTER_TOKEN", FAKE_TOKEN)
    @patch("skills.job_hunter.asyncio.wait_for")
    async def test_timeout_returns_error(self, mock_wait_for):
        async def raise_timeout(coro, timeout):
            coro.close()
            raise asyncio.TimeoutError()

        mock_wait_for.side_effect = raise_timeout

        result = await self.skill.execute({})
        self.assertIn("error", result)
        self.assertIn("Timeout", result["error"])

    @patch("skills.job_hunter.config.JOB_HUNTER_URL", FAKE_URL)
    @patch("skills.job_hunter.config.JOB_HUNTER_TOKEN", FAKE_TOKEN)
    @patch("skills.job_hunter.requests.get")
    async def test_http_error_returns_error(self, mock_get):
        import requests as req

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(
                side_effect=req.HTTPError(response=mock_response)
            )
        )

        result = await self.skill.execute({})
        self.assertIn("error", result)
        self.assertIn("403", result["error"])


    @patch("skills.job_hunter.config.JOB_HUNTER_URL", FAKE_URL)
    @patch("skills.job_hunter.config.JOB_HUNTER_TOKEN", FAKE_TOKEN)
    @patch("skills.job_hunter.requests.get")
    async def test_connection_error_returns_error(self, mock_get):
        import requests as req

        mock_get.side_effect = req.ConnectionError("Connection refused")

        result = await self.skill.execute({})
        self.assertIn("error", result)
        self.assertIn("conexão", result["error"].lower())


if __name__ == "__main__":
    unittest.main()
