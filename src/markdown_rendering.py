"""Markdown rendering helpers with CSS styling."""

import markdown

from config import AppConfig


def build_styled_markdown_html(markdown_text):
    html_content = markdown.markdown(
        markdown_text, extensions=["tables", "fenced_code"]
    )

    with open(AppConfig.get_styles_path(), "r", encoding="utf-8") as css_file:
        css_content = css_file.read()

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
