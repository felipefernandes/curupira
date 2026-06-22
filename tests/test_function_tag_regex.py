from core.agent import AgentBrain


class TestFunctionTagRegex:
    """Tests for malformed <function> tag regex patterns."""

    def test_slash_format_with_angle_bracket(self):
        """Groq actual format: <function/name>{"args"}</function>"""
        text = '<function/google_calendar>{"action": "list_calendar_events", "time_range": "today"}</function>'
        match = AgentBrain._RE_FUNC_SLASH.search(text)
        assert match is not None
        assert match.group(1) == "google_calendar"
        assert '"action": "list_calendar_events"' in match.group(2)

    def test_slash_format_without_angle_bracket(self):
        """Variant: <function/name{"args"}</function>"""
        text = '<function/google_calendar{"action": "list_calendar_events"}</function>'
        match = AgentBrain._RE_FUNC_SLASH.search(text)
        assert match is not None
        assert match.group(1) == "google_calendar"

    def test_equals_angles_format(self):
        """<function=name>{"args"}</function>"""
        text = '<function=google_calendar>{"action": "setup_calendar"}</function>'
        match = AgentBrain._RE_FUNC_ANGLES.search(text)
        assert match is not None
        assert match.group(1) == "google_calendar"

    def test_parens_format(self):
        """<function=name(args)</function>"""
        text = '<function=google_calendar({"action": "list"})</function>'
        match = AgentBrain._RE_FUNC_PARENS.search(text)
        assert match is not None
        assert match.group(1) == "google_calendar"

    def test_direct_json_format(self):
        """<function=name{"args"}</function>"""
        text = '<function=google_calendar{"action": "list"}</function>'
        match = AgentBrain._RE_FUNC_DIRECT_JSON.search(text)
        assert match is not None
        assert match.group(1) == "google_calendar"

    def test_cleanup_removes_function_tags(self):
        """Catch-all cleanup strips any remaining <function> tags."""
        text = 'Aqui estão seus eventos: <function/calendar>{"x": 1}</function> fim'
        result = AgentBrain._RE_FUNC_CLEANUP.sub('', text)
        assert result == 'Aqui estão seus eventos:  fim'

    def test_cleanup_removes_unclosed_function_tags(self):
        """Cleanup strips unclosed <function> tags."""
        text = 'text <function=calendar> more text'
        result = AgentBrain._RE_FUNC_UNCLOSED.sub('', text)
        assert result == 'text  more text'

    def test_slash_with_preamble_text(self):
        """Function tag with preamble text extracts correctly."""
        text = 'Vou verificar seus eventos. <function/google_calendar>{"action": "list_calendar_events"}</function>'
        match = AgentBrain._RE_FUNC_SLASH.search(text)
        assert match is not None
        preamble = text[:match.start()].strip()
        assert preamble == "Vou verificar seus eventos."

    def test_double_equals_format(self):
        """<function=name={"args"}></function>"""
        text = '<function=google_calendar={"action": "list"}></function>'
        match = AgentBrain._RE_FUNC_DOUBLE_EQUALS.search(text)
        assert match is not None
        assert match.group(1) == "google_calendar"
