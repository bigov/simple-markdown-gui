"""Markdown rendering helpers with CSS styling."""

import re
import markdown

from config import AppConfig, DEFAULT_STYLES_TEMPLATE


def _convert_headings_to_divs(html_content):
    """Convert heading tags to divs to work around Qt's built-in heading scaling.

    Qt applies fixed scaling factors to h1-h6 tags that cannot be overridden by CSS.
    Converting to divs with CSS classes allows proper styling control.
    """
    # Replace opening heading tags: <h1> -> <div class="h1">
    for level in range(1, 7):
        html_content = re.sub(
            rf"<h{level}([\s>])",
            rf'<div class="h{level}"\1',
            html_content,
            flags=re.IGNORECASE,
        )
        # Replace closing tags: </h1> -> </div>
        html_content = re.sub(
            rf"</h{level}>", "</div>", html_content, flags=re.IGNORECASE
        )

    return html_content


def _wrap_code_blocks_in_table(html_content):
    """Wrap pre blocks in a two-cell table that Qt renders reliably.

    QTextDocument supports this old-school table layout more consistently than
    CSS box-model properties on pre elements.
    """

    return re.sub(
        r"<pre>(.*?)</pre>",
        (
            '<table class="code-block" width="100%" cellpadding="0" cellspacing="0"><tr>'
            '<td class="code-block-gutter" width="16"></td>'
            '<td class="code-block-content"><pre>'
            r"\1</pre>"
            "</td></tr></table>"
        ),
        html_content,
        flags=re.DOTALL | re.IGNORECASE,
    )


def build_styled_markdown_html(markdown_text):
    html_content = markdown.markdown(
        markdown_text, extensions=["tables", "fenced_code"]
    )

    try:
        with open(AppConfig.get_styles_path(), "r", encoding="utf-8") as css_file:
            css_content = css_file.read()
    except FileNotFoundError:
        css_content = DEFAULT_STYLES_TEMPLATE

    # Convert heading tags to divs to bypass Qt's built-in heading scaling
    html_content = _convert_headings_to_divs(html_content)
    html_content = _wrap_code_blocks_in_table(html_content)

    return f"""
<!DOCTYPE html>
<html>
<head>
<style>
{css_content}
</style>
</head>
<body>
{html_content}
</body>
</html>
"""


def render_markdown_with_styles(editor, markdown_text):
    try:
        editor.setHtml(build_styled_markdown_html(markdown_text))
    except FileNotFoundError:
        editor.setMarkdown(markdown_text)
