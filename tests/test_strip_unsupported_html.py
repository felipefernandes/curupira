from bot import _strip_unsupported_html


class TestStripUnsupportedHtml:
    """Tests for _strip_unsupported_html helper."""

    def test_keeps_bold_tags(self):
        assert _strip_unsupported_html("<b>bold</b>") == "<b>bold</b>"

    def test_keeps_italic_tags(self):
        assert _strip_unsupported_html("<i>italic</i>") == "<i>italic</i>"

    def test_keeps_code_tags(self):
        assert _strip_unsupported_html("<code>x</code>") == "<code>x</code>"

    def test_keeps_pre_tags(self):
        assert _strip_unsupported_html("<pre>block</pre>") == "<pre>block</pre>"

    def test_keeps_underline_and_strikethrough(self):
        assert _strip_unsupported_html("<u>u</u> <s>s</s>") == "<u>u</u> <s>s</s>"

    def test_keeps_anchor_with_href(self):
        html = '<a href="https://example.com">link</a>'
        assert _strip_unsupported_html(html) == html

    def test_strips_script_tag(self):
        assert _strip_unsupported_html("<script>alert(1)</script>") == "alert(1)"

    def test_strips_div_tag(self):
        assert _strip_unsupported_html("<div>content</div>") == "content"

    def test_strips_function_tag(self):
        text = '<function/google_calendar>{"action":"list"}</function>'
        assert _strip_unsupported_html(text) == '{"action":"list"}'

    def test_strips_br_tag(self):
        assert _strip_unsupported_html("line1<br>line2") == "line1line2"

    def test_mixed_valid_and_invalid(self):
        text = "<b>Bom dia!</b><br><div>Previsão: <i>ensolarado</i></div>"
        result = _strip_unsupported_html(text)
        assert result == "<b>Bom dia!</b>Previsão: <i>ensolarado</i>"

    def test_empty_string(self):
        assert _strip_unsupported_html("") == ""

    def test_no_html(self):
        assert _strip_unsupported_html("plain text") == "plain text"

    def test_preserves_tg_spoiler(self):
        assert _strip_unsupported_html("<tg-spoiler>hidden</tg-spoiler>") == "<tg-spoiler>hidden</tg-spoiler>"

    def test_closing_tags_stripped_for_unsupported(self):
        assert _strip_unsupported_html("</div>text</span>") == "text"
