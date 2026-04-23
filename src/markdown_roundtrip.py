"""Helpers that preserve stable Markdown round-tripping in the visual editor."""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher


# Stores a markdown block together with the blank lines that follow it.
@dataclass
class MarkdownChunk:
    """Markdown block paired with the blank-line separator that follows it."""

    block: str
    separator: str


def _fence_marker(line):
    match = re.match(r"^(`{3,}|~{3,})", line.strip())
    if not match:
        return None
    return match.group(1)


def _is_fenced_chunk(lines):
    if len(lines) < 2:
        return False

    opening = _fence_marker(lines[0])
    closing = _fence_marker(lines[-1])
    if not opening or not closing:
        return False

    return opening[0] == closing[0]


# Splits markdown into comparable chunks while keeping fenced code blocks intact.
def _split_markdown_chunks(markdown_text):
    chunks = []
    current_block = []
    current_separator = []
    in_fence = False
    active_fence_char = None
    # Set to True right after the closing fence line is consumed so that the
    # next non-blank line always starts a new chunk, even without a blank-line
    # separator.  Qt's toMarkdown() sometimes omits the blank line that normally
    # follows a fenced block, which would otherwise merge it with the next chunk.
    fence_just_closed = False

    for line in markdown_text.splitlines(keepends=True):
        stripped = line.strip()

        if current_block and not in_fence and stripped == "":
            current_separator.append(line)
            fence_just_closed = False
            continue

        if current_separator or fence_just_closed:
            if current_block:
                chunks.append(
                    MarkdownChunk("".join(current_block), "".join(current_separator))
                )
            current_block = []
            current_separator = []
            fence_just_closed = False

        current_block.append(line)

        marker = _fence_marker(stripped)
        if marker:
            marker_char = marker[0]
            if not in_fence:
                in_fence = True
                active_fence_char = marker_char
            elif marker_char == active_fence_char:
                in_fence = False
                active_fence_char = None
                fence_just_closed = True

    if current_block or current_separator:
        chunks.append(MarkdownChunk("".join(current_block), "".join(current_separator)))

    return chunks


# Removes inline formatting markers so unchanged blocks can still be matched reliably.
def _normalize_inline_markdown(text):
    if "```" not in text and "~~~" not in text and text.count("`") % 2 == 1:
        # Qt may wrap a multi-line paragraph with one opening backtick on the
        # first line and one closing backtick on the last line. Normalize such
        # dangling markers in line signatures so unchanged text still matches.
        text = re.sub(r"^(\s*(?:>\s*)?)`", r"\1", text)
        text = re.sub(r"^((?:\s*[-+*]\s+))`", r"\1", text)
        text = re.sub(r"`(\s*)$", r"\1", text)
        if text.count("`") % 2 == 1:
            text = text.replace("`", "", 1)

    text = re.sub(r"<u>(.*?)</u>", r"\1", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"~~(.*?)~~", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    return text


def _normalize_table_line_signature(line):
    stripped = line.strip()
    if "|" not in stripped:
        return None

    cells = [cell.strip() for cell in stripped.split("|")]
    while cells and cells[0] == "":
        cells.pop(0)
    while cells and cells[-1] == "":
        cells.pop()

    if len(cells) < 2:
        return None

    normalized_cells = [_normalize_inline_markdown(cell) for cell in cells]

    is_separator_row = all(
        re.fullmatch(r":?-{3,}:?", cell) for cell in normalized_cells
    )
    if is_separator_row:
        return f"table-sep:{'|'.join(normalized_cells)}"

    return f"table-row:{'|'.join(normalized_cells)}"


def _strip_list_item_backtick_wrap(markdown_text):
    """Strip Qt artifact: entire list-item content wrapped in a single backtick pair.

    When a code block immediately precedes a list, Qt's font-rendering may mark
    the list-item text as monospace (code font) and then emit it surrounded by
    backticks in toMarkdown().  This is always an artifact — intentional inline
    code inside a list item would never wrap the *entire* content.
    """
    result = []
    for line in markdown_text.splitlines(keepends=True):
        eol = "\n" if line.endswith("\n") else ""
        stripped = line.rstrip("\n")
        m = re.match(r"^(\s*[-*+]\s+)(`[^`]+`)(\s*)$", stripped)
        if m:
            inner = m.group(2)[1:-1]
            stripped = m.group(1) + inner + m.group(3)
        result.append(stripped + eol)
    return "".join(result)


def _restore_qt_table_wrapped_code_blocks(markdown_text):
    """Convert Qt's markdown export for wrapped code-block tables back to fences."""

    def replace_table(match):
        code_lines = []
        for row in match.group(1).splitlines():
            cells = row.split("|")
            while cells and cells[-1].strip() == "":
                cells.pop()
            for cell in cells:
                stripped = cell.rstrip()
                if stripped.strip() == "":
                    continue
                code_lines.append(stripped)

        return "```\n" + "\n".join(code_lines) + "\n```"

    return re.sub(
        r"\|\|```[^\n]*\n(.*?)\n\n```",
        replace_table,
        markdown_text,
        flags=re.DOTALL,
    )


# Builds a normalized signature used to compare original and edited markdown chunks.
def _chunk_signature(chunk):
    block = chunk.block.strip("\n")
    if not block:
        return ""

    lines = block.splitlines()
    if _is_fenced_chunk(lines):
        # Qt may inject extra blank lines inside fenced blocks during toMarkdown().
        # Ignore blank-only lines for chunk matching, while preserving real code lines.
        return "\n".join(
            line.rstrip() for line in lines[1:-1] if line.strip() != ""
        ).strip()

    normalized_lines = []
    for line in lines:
        table_signature = _normalize_table_line_signature(line)
        if table_signature is not None:
            normalized_lines.append(table_signature)
            continue
        line = re.sub(r"^#{1,6}\s+", "", line)
        normalized_lines.append(_normalize_inline_markdown(line).strip())
    return "\n".join(normalized_lines).strip()


def _line_signature(line):
    line = line.rstrip("\r\n")
    table_signature = _normalize_table_line_signature(line)
    if table_signature is not None:
        return table_signature
    line = re.sub(r"^#{1,6}\s+", "", line)
    return _normalize_inline_markdown(line).strip()


def _merge_chunk_preserving_unchanged_lines(original_chunk, edited_chunk):
    original_lines = original_chunk.block.splitlines(keepends=True)
    edited_lines = edited_chunk.block.splitlines(keepends=True)

    if not original_lines or not edited_lines:
        return edited_chunk

    if _is_fenced_chunk([line.rstrip("\r\n") for line in edited_lines]):
        return edited_chunk

    original_signatures = [_line_signature(line) for line in original_lines]
    edited_signatures = [_line_signature(line) for line in edited_lines]

    merged_lines = []
    matcher = SequenceMatcher(None, original_signatures, edited_signatures)
    for (
        tag,
        original_start,
        original_end,
        edited_start,
        edited_end,
    ) in matcher.get_opcodes():
        if tag == "equal":
            merged_lines.extend(original_lines[original_start:original_end])
            continue
        merged_lines.extend(edited_lines[edited_start:edited_end])

    return MarkdownChunk("".join(merged_lines), edited_chunk.separator)


# Checks whether a chunk starts with a markdown heading marker.
def _is_heading_chunk(chunk):
    return bool(re.match(r"^#{1,6}\s+", chunk.block.lstrip()))


# Converts a falsely inherited heading back into a normal paragraph after edits.
def _demote_inherited_heading(chunk, previous_chunk):
    if previous_chunk is None or not _is_heading_chunk(previous_chunk):
        return chunk

    lines = chunk.block.splitlines(keepends=True)
    if not lines:
        return chunk

    match = re.match(r"^(#{1,6})\s+(.*)", lines[0])
    previous_match = re.match(r"^(#{1,6})\s+", previous_chunk.block.lstrip())
    if not match or not previous_match or match.group(1) != previous_match.group(1):
        return chunk

    lines[0] = f"{match.group(2)}\n"
    return MarkdownChunk("".join(lines), chunk.separator)


# Merges edited markdown with original unchanged chunks to preserve stable round-tripping.
def preserve_roundtrip_markdown(original_markdown, edited_markdown):
    original_chunks = _split_markdown_chunks(original_markdown)
    edited_chunks = _split_markdown_chunks(
        _strip_list_item_backtick_wrap(
            _restore_qt_table_wrapped_code_blocks(edited_markdown)
        )
    )

    original_signatures = [_chunk_signature(chunk) for chunk in original_chunks]
    edited_signatures = [_chunk_signature(chunk) for chunk in edited_chunks]

    merged_chunks = []
    matcher = SequenceMatcher(None, original_signatures, edited_signatures)

    for (
        tag,
        original_start,
        original_end,
        edited_start,
        edited_end,
    ) in matcher.get_opcodes():
        if tag == "equal":
            merged_chunks.extend(original_chunks[original_start:original_end])
            continue

        edited_slice = edited_chunks[edited_start:edited_end]
        original_slice = original_chunks[original_start:original_end]

        for index, chunk in enumerate(edited_slice):
            if index < len(original_slice):
                chunk = _merge_chunk_preserving_unchanged_lines(
                    original_slice[index], chunk
                )
            previous_chunk = merged_chunks[-1] if merged_chunks else None
            merged_chunks.append(_demote_inherited_heading(chunk, previous_chunk))

    return "".join(f"{chunk.block}{chunk.separator}" for chunk in merged_chunks)
