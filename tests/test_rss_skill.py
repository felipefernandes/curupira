"""Tests for skills/rss.py RssReadSkill and RssListSkill."""

import asyncio
import os
import sys
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.rss import RssReadSkill, RssListSkill


def _make_mock_feed(bozo=False, title="Test Feed", entries=None):
    """Helper to create a mock feedparser result."""
    feed = MagicMock()
    feed.bozo = bozo
    feed.feed.get = lambda k, d=None: {"title": title}.get(k, d)
    feed.entries = entries if entries is not None else []
    return feed


class TestRssReadSkill:
    """Tests for RssReadSkill."""

    def setup_method(self):
        self.skill = RssReadSkill()

    def test_skill_properties(self):
        assert self.skill.name == "rss_read"
        assert "RSS" in self.skill.display_name or "Feed" in self.skill.display_name
        assert "url" in self.skill.parameters["properties"]
        assert "limit" in self.skill.parameters["properties"]
        assert "url" in self.skill.parameters["required"]

    @pytest.mark.asyncio
    async def test_read_feed_success(self):
        """Test parsing a well-formed feed."""
        mock_feed = _make_mock_feed(title="Test Feed", entries=[
            {"title": "Article 1", "link": "https://example.com/1", "published": "2026-01-01"},
            {"title": "Article 2", "link": "https://example.com/2", "published": "2026-01-02"},
            {"title": "Article 3", "link": "https://example.com/3", "published": "2026-01-03"},
        ])

        with patch("skills.rss.asyncio.to_thread", new_callable=AsyncMock, return_value=mock_feed):
            result = await self.skill.execute({}, url="https://example.com/feed", limit=2)

        assert result["feed_title"] == "Test Feed"
        assert result["total_available"] == 3
        assert len(result["entries"]) == 2
        assert result["entries"][0]["title"] == "Article 1"

    @pytest.mark.asyncio
    async def test_read_feed_default_limit(self):
        """Test that default limit is 5."""
        mock_feed = _make_mock_feed(title="Big Feed", entries=[
            {"title": f"Article {i}", "link": f"https://example.com/{i}", "published": ""}
            for i in range(10)
        ])

        with patch("skills.rss.asyncio.to_thread", new_callable=AsyncMock, return_value=mock_feed):
            result = await self.skill.execute({}, url="https://example.com/feed")

        assert len(result["entries"]) == 5

    @pytest.mark.asyncio
    async def test_read_feed_bozo_no_entries(self):
        """Test error handling for unparseable feed."""
        mock_feed = _make_mock_feed(bozo=True, entries=[])

        with patch("skills.rss.asyncio.to_thread", new_callable=AsyncMock, return_value=mock_feed):
            result = await self.skill.execute({}, url="https://bad.example.com/feed")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_read_feed_bozo_with_entries(self):
        """Test that bozo feeds with entries still return data."""
        mock_feed = _make_mock_feed(bozo=True, title="Partial Feed", entries=[
            {"title": "Still works", "link": "https://example.com/ok", "published": ""},
        ])

        with patch("skills.rss.asyncio.to_thread", new_callable=AsyncMock, return_value=mock_feed):
            result = await self.skill.execute({}, url="https://example.com/feed")

        assert "entries" in result
        assert len(result["entries"]) == 1

    @pytest.mark.asyncio
    async def test_read_feed_missing_fields(self):
        """Test entries with missing optional fields use defaults."""
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.feed.get = lambda k, d=None: d
        mock_feed.entries = [{}]

        with patch("skills.rss.asyncio.to_thread", new_callable=AsyncMock, return_value=mock_feed):
            result = await self.skill.execute({}, url="https://example.com/feed")

        entry = result["entries"][0]
        assert entry["title"] == "Sem título"
        assert entry["link"] == ""
        assert entry["published"] == ""

    @pytest.mark.asyncio
    async def test_read_feed_timeout(self):
        """Test that a slow feed returns a timeout error."""
        async def slow_fetch(*args, **kwargs):
            raise asyncio.TimeoutError()

        with patch("skills.rss.asyncio.wait_for", side_effect=asyncio.TimeoutError):
            result = await self.skill.execute({}, url="https://slow.example.com/feed")

        assert "error" in result
        assert "Timeout" in result["error"]


class TestRssListSkill:
    """Tests for RssListSkill."""

    def setup_method(self):
        self.skill = RssListSkill()

    def test_skill_properties(self):
        assert self.skill.name == "rss_list"
        assert self.skill.parameters["properties"] == {}

    @pytest.mark.asyncio
    async def test_list_feeds_with_config(self):
        """Test listing feeds when config has entries."""
        mock_feeds = {"G1": "https://g1.globo.com/rss/g1/", "HN": "https://hnrss.org/frontpage"}

        with patch("skills.rss.config") as mock_config:
            mock_config.RSS_FEEDS = mock_feeds
            result = await self.skill.execute({})

        assert result["total"] == 2
        names = [f["name"] for f in result["feeds"]]
        assert "G1" in names
        assert "HN" in names

    @pytest.mark.asyncio
    async def test_list_feeds_empty(self):
        """Test listing feeds when none are configured."""
        with patch("skills.rss.config") as mock_config:
            mock_config.RSS_FEEDS = {}
            result = await self.skill.execute({})

        assert result["feeds"] == []
        assert "message" in result
