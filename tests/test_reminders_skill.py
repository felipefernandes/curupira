"""Tests for AddReminderSkill._preprocess_time_string."""

import os
import sys
import pytest
from unittest.mock import MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.reminders import AddReminderSkill, ReminderManager


@pytest.fixture
def skill():
    manager = MagicMock(spec=ReminderManager)
    manager.logger = MagicMock()
    return AddReminderSkill(manager)


class TestPreprocessTimeString:
    """Tests for _preprocess_time_string."""

    def test_toda_manha_maps_to_0800(self, skill):
        result = skill._preprocess_time_string("toda manhã")
        assert "08:00" in result

    def test_de_manha_maps_to_0800(self, skill):
        result = skill._preprocess_time_string("de manhã")
        assert "08:00" in result

    def test_manha_without_accent_maps_to_0800(self, skill):
        result = skill._preprocess_time_string("manha")
        assert "08:00" in result

    def test_toda_tarde_maps_to_1400(self, skill):
        result = skill._preprocess_time_string("toda tarde")
        assert "14:00" in result

    def test_de_tarde_maps_to_1400(self, skill):
        result = skill._preprocess_time_string("de tarde")
        assert "14:00" in result

    def test_toda_noite_maps_to_2000(self, skill):
        result = skill._preprocess_time_string("toda noite")
        assert "20:00" in result

    def test_de_noite_maps_to_2000(self, skill):
        result = skill._preprocess_time_string("de noite")
        assert "20:00" in result

    def test_explicit_time_unchanged(self, skill):
        result = skill._preprocess_time_string("às 10:00")
        assert "10:00" in result

    def test_amanha_as_10h(self, skill):
        result = skill._preprocess_time_string("amanhã as 10h")
        assert "às 10:00" in result

    def test_unrelated_string_unchanged(self, skill):
        result = skill._preprocess_time_string("em 30 minutos")
        assert "30" in result
