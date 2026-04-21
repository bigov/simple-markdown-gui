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
    text = re.sub(r"<u>(.*?)</u>", r"\1", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"~~(.*?)~~", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    return text


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
        line = re.sub(r"^#{1,6}\s+", "", line)
        normalized_lines.append(_normalize_inline_markdown(line).strip())
    return "\n".join(normalized_lines).strip()


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
    edited_chunks = _split_markdown_chunks(edited_markdown)

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

        for chunk in edited_chunks[edited_start:edited_end]:
            previous_chunk = merged_chunks[-1] if merged_chunks else None
            merged_chunks.append(_demote_inherited_heading(chunk, previous_chunk))

    return "".join(f"{chunk.block}{chunk.separator}" for chunk in merged_chunks)
