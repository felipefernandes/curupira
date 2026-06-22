"""
Tests for core.telegram_formatter.TelegramFormatter.

Covers: format detection, Markdown→HTML conversion, tag stripping,
idempotency, edge cases, and full normalize() pipeline.
"""

from core.telegram_formatter import TelegramFormatter


class TestDetectFormat:
    def test_pure_html_bold(self):
        assert TelegramFormatter._detect_format("<b>texto</b>") == "html"

    def test_pure_html_code(self):
        assert TelegramFormatter._detect_format("<code>x = 1</code>") == "html"

    def test_pure_markdown_bold(self):
        assert TelegramFormatter._detect_format("**negrito**") == "markdown"

    def test_pure_markdown_fence(self):
        assert TelegramFormatter._detect_format("```python\ncode\n```") == "markdown"

    def test_pure_markdown_header(self):
        assert TelegramFormatter._detect_format("## Título") == "markdown"

    def test_mixed(self):
        assert TelegramFormatter._detect_format("**bold** e <b>html</b>") == "mixed"

    def test_plain_text(self):
        assert TelegramFormatter._detect_format("Olá, como vai?") == "plain"

    def test_plain_with_emoji(self):
        assert TelegramFormatter._detect_format("✅ Tudo certo!") == "plain"


class TestMarkdownToHtml:
    def test_bold_asterisks(self):
        result = TelegramFormatter._markdown_to_html("**negrito**")
        assert result == "<b>negrito</b>"

    def test_bold_underscores(self):
        result = TelegramFormatter._markdown_to_html("__negrito__")
        assert result == "<b>negrito</b>"

    def test_italic_asterisk(self):
        result = TelegramFormatter._markdown_to_html("*itálico*")
        assert result == "<i>itálico</i>"

    def test_italic_underscore(self):
        result = TelegramFormatter._markdown_to_html("_itálico_")
        assert result == "<i>itálico</i>"

    def test_code_fence(self):
        result = TelegramFormatter._markdown_to_html("```\nbloco\n```")
        assert "<pre>" in result
        assert "bloco" in result

    def test_inline_code(self):
        result = TelegramFormatter._markdown_to_html("`variavel`")
        assert result == "<code>variavel</code>"

    def test_header_h1(self):
        result = TelegramFormatter._markdown_to_html("# Título")
        assert result == "<b>Título</b>"

    def test_header_h3(self):
        result = TelegramFormatter._markdown_to_html("### Seção")
        assert result == "<b>Seção</b>"

    def test_link(self):
        result = TelegramFormatter._markdown_to_html("[Clique](https://example.com)")
        assert result == '<a href="https://example.com">Clique</a>'

    def test_bullet_asterisk(self):
        result = TelegramFormatter._markdown_to_html("* item1\n* item2")
        assert "• item1" in result
        assert "• item2" in result

    def test_bullet_dash(self):
        result = TelegramFormatter._markdown_to_html("- item")
        assert "• item" in result

    def test_existing_html_preserved(self):
        """Tags HTML existentes não devem ser corrompidas no modo mixed."""
        result = TelegramFormatter._markdown_to_html("<b>já html</b>")
        assert result == "<b>já html</b>"

    def test_mixed_bold_and_existing_html(self):
        result = TelegramFormatter._markdown_to_html("**novo** e <b>existente</b>")
        assert "<b>novo</b>" in result
        assert "<b>existente</b>" in result

    def test_code_fence_escapes_html(self):
        """Conteúdo dentro de ``` deve ser html-escaped."""
        result = TelegramFormatter._markdown_to_html("```\n<b>not bold</b>\n```")
        assert "&lt;b&gt;" in result


class TestStripUnsupported:
    def test_keeps_b(self):
        assert TelegramFormatter._strip_unsupported("<b>x</b>") == "<b>x</b>"

    def test_keeps_i(self):
        assert TelegramFormatter._strip_unsupported("<i>x</i>") == "<i>x</i>"

    def test_keeps_code(self):
        assert TelegramFormatter._strip_unsupported("<code>x</code>") == "<code>x</code>"

    def test_keeps_pre(self):
        assert TelegramFormatter._strip_unsupported("<pre>x</pre>") == "<pre>x</pre>"

    def test_keeps_tg_spoiler(self):
        assert TelegramFormatter._strip_unsupported("<tg-spoiler>x</tg-spoiler>") == "<tg-spoiler>x</tg-spoiler>"

    def test_strips_div(self):
        assert TelegramFormatter._strip_unsupported("<div>x</div>") == "x"

    def test_strips_script(self):
        assert TelegramFormatter._strip_unsupported("<script>x</script>") == "x"

    def test_strips_function_tag(self):
        text = '<function/google_calendar>{"action":"list"}</function>'
        result = TelegramFormatter._strip_unsupported(text)
        assert '{"action":"list"}' in result

    def test_strips_br(self):
        assert TelegramFormatter._strip_unsupported("a<br>b") == "ab"


class TestNormalizeFull:
    def test_markdown_bold_normalized(self):
        result = TelegramFormatter.normalize("**Status:** OK")
        assert "<b>Status:</b>" in result

    def test_html_passthrough(self):
        html = "<b>já formatado</b>"
        assert TelegramFormatter.normalize(html) == html

    def test_plain_passthrough(self):
        text = "Olá, tudo bem?"
        assert TelegramFormatter.normalize(text) == text

    def test_idempotent(self):
        """Chamar normalize duas vezes não corrompe o resultado."""
        text = "**negrito** e _itálico_"
        once = TelegramFormatter.normalize(text)
        twice = TelegramFormatter.normalize(once)
        assert once == twice

    def test_think_block_stripped(self):
        text = "<think>raciocínio interno</think>Resposta final."
        result = TelegramFormatter.normalize(text)
        assert "<think>" not in result
        assert "Resposta final." in result

    def test_emoji_preserved(self):
        text = "✅ Lembrete criado! 🔁 Recorrente"
        result = TelegramFormatter.normalize(text)
        assert "✅" in result
        assert "🔁" in result

    def test_empty_string(self):
        assert TelegramFormatter.normalize("") == ""

    def test_none_like_empty(self):
        # normalize("") should not raise
        assert TelegramFormatter.normalize("") == ""

    def test_long_text_truncated(self):
        long_text = "a" * 5000
        result = TelegramFormatter.normalize(long_text)
        assert len(result) <= 4096

    def test_unsupported_tags_stripped_in_html_mode(self):
        text = "<b>ok</b><div>stripped</div>"
        result = TelegramFormatter.normalize(text)
        assert "<div>" not in result
        assert "<b>ok</b>" in result
        assert "stripped" in result

    def test_mixed_markdown_and_html(self):
        text = "**negrito** e <b>html</b>"
        result = TelegramFormatter.normalize(text)
        assert "<b>negrito</b>" in result
        assert "<b>html</b>" in result

    def test_think_block_only_returns_empty(self):
        """Text that becomes empty after stripping <think> block returns ''."""
        # Line 89: return "" when think-block stripping leaves empty text
        result = TelegramFormatter.normalize("<think>só raciocínio</think>")
        assert result == ""

    def test_html_text_over_limit_truncated(self):
        """HTML/Markdown text > 4096 chars is truncated (line 105)."""
        # Use bold markdown so it goes through the html/markdown path, not plain
        long_text = "**" + "a" * 5000 + "**"
        result = TelegramFormatter.normalize(long_text)
        assert len(result) <= 4096
        assert result.endswith("...")
