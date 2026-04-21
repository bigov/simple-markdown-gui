# This module protects Markdown round-tripping in the visual editor.
# It preserves unchanged parts of the original document, compares edited blocks
# with their source versions, and fixes cases where Qt inherits heading markup
# for newly inserted paragraphs.

import re
from dataclasses import dataclass
from difflib import SequenceMatcher


# Stores a markdown block together with the blank lines that follow it.
@dataclass
class MarkdownChunk:
    block: str
    separator: str


# Splits markdown into comparable chunks while keeping fenced code blocks intact.
def _split_markdown_chunks(markdown_text):
    chunks = []
    current_block = []
    current_separator = []
    in_fence = False

    for line in markdown_text.splitlines(keepends=True):
        stripped = line.strip()

        if current_block and not in_fence and stripped == "":
            current_separator.append(line)
            continue

        if current_separator:
            chunks.append(MarkdownChunk("".join(current_block), "".join(current_separator)))
            current_block = []
            current_separator = []

        current_block.append(line)

        if stripped.startswith("```"):
            in_fence = not in_fence

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
    if lines and lines[0].strip().startswith("```") and lines[-1].strip().startswith("```"):
        return "\n".join(line.rstrip() for line in lines[1:-1]).strip()

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

    for tag, original_start, original_end, edited_start, edited_end in matcher.get_opcodes():
        if tag == 'equal':
            merged_chunks.extend(original_chunks[original_start:original_end])
            continue

        for chunk in edited_chunks[edited_start:edited_end]:
            previous_chunk = merged_chunks[-1] if merged_chunks else None
            merged_chunks.append(_demote_inherited_heading(chunk, previous_chunk))

    return "".join(f"{chunk.block}{chunk.separator}" for chunk in merged_chunks)