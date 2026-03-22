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

class TestRemindersMetadata:
    def test_add_reminder_metadata(self):
        manager = MagicMock(spec=ReminderManager)
        skill = AddReminderSkill(manager)
        assert skill.name == "add_reminder"
        assert "Criar" in skill.display_name
        assert "lembrete" in skill.description.lower()
        assert "message" in skill.parameters["properties"]
        assert skill.skill_group == "reminders"
        assert skill.skill_group_emoji == "⏰"

    def test_list_reminders_metadata(self):
        from skills.reminders import ListRemindersSkill
        manager = MagicMock(spec=ReminderManager)
        skill = ListRemindersSkill(manager)
        assert skill.name == "list_reminders"
        assert "Listar" in skill.display_name
        assert "listar os lembretes" in skill.description.lower()
        assert skill.parameters["type"] == "object"
        assert skill.skill_group == "reminders"
        assert skill.skill_group_emoji == "⏰"

    def test_delete_reminder_metadata(self):
        from skills.reminders import DeleteReminderSkill
        manager = MagicMock(spec=ReminderManager)
        skill = DeleteReminderSkill(manager)
        assert skill.name == "delete_reminder"
        assert "Deletar" in skill.display_name
        assert "cancelar" in skill.description.lower()
        assert "reminder_id" in skill.parameters["properties"]
        assert skill.skill_group == "reminders"
        assert skill.skill_group_emoji == "⏰"

    def test_update_reminder_metadata(self):
        from skills.reminders import UpdateReminderSkill
        manager = MagicMock(spec=ReminderManager)
        skill = UpdateReminderSkill(manager)
        assert skill.name == "update_reminder"
        assert "Atualizar" in skill.display_name
        assert "atualiza" in skill.description.lower()
        assert "reminder_id" in skill.parameters["properties"]
        assert skill.skill_group == "reminders"
        assert skill.skill_group_emoji == "⏰"

