import re
from langchain_text_splitters import TextSplitter, RecursiveCharacterTextSplitter
from config import settings

CHARS_PER_TOKEN = 4

# Matches common business-document heading patterns:
# "Section 1:", "Chapter 2", "1.1 Something", "1. Something", ALL CAPS short lines
HEADING_PATTERN = re.compile(
    r"^(?:"
    r"Section\s+\d+[:.]?|"
    r"Chapter\s+\d+[:.]?|"
    r"\d+(?:\.\d+)*\s+[A-Z][A-Za-z ,'\-]{2,80}$|"   # no digits allowed after the heading number
    r"[A-Z][A-Z ]{4,60}"                              # tightened: letters/spaces only, no digits
    r")\s*$",
    re.MULTILINE,
)


class StructureAwareTextSplitter(TextSplitter):
    def split_text(self, text: str) -> list[str]:
        matches = list(HEADING_PATTERN.finditer(text))
        if not matches:
            return [text.strip()] if text.strip() else []

        sections = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section = text[start:end].strip()
            if section:
                sections.append(section)

        if matches[0].start() > 0:
            preamble = text[: matches[0].start()].strip()
            if preamble:
                sections.insert(0, preamble)

        return sections


def get_child_splitter() -> RecursiveCharacterTextSplitter:
    chunk_size_chars = settings.chunk_size_tokens * CHARS_PER_TOKEN
    chunk_overlap_chars = settings.chunk_overlap_tokens * CHARS_PER_TOKEN
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size_chars,
        chunk_overlap=chunk_overlap_chars,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

def _split_markdown_table(markdown: str, max_chars: int) -> list[str]:
    lines = markdown.split("\n")
    if len(lines) < 2:
        return [markdown]
    header_lines = lines[:2]  # header row + separator row, repeated in every piece
    body_lines = lines[2:]

    pieces, current, current_len = [], header_lines.copy(), sum(len(l) for l in header_lines)
    for line in body_lines:
        if current_len + len(line) > max_chars and len(current) > len(header_lines):
            pieces.append("\n".join(current))
            current, current_len = header_lines.copy(), sum(len(l) for l in header_lines)
        current.append(line)
        current_len += len(line)
    if len(current) > len(header_lines):
        pieces.append("\n".join(current))
    return pieces


def chunk_documents(documents) -> list:
    from langchain_core.documents import Document

    parent_splitter = get_parent_splitter()
    child_splitter = get_child_splitter()
    max_chars = settings.chunk_size_tokens * CHARS_PER_TOKEN

    all_chunks = []
    for doc in documents:
        if doc.metadata.get("type") == "table":
            for piece in _split_markdown_table(doc.page_content, max_chars):
                all_chunks.append(Document(page_content=piece, metadata=dict(doc.metadata)))
        else:
            parent_docs = parent_splitter.split_documents([doc])
            all_chunks.extend(child_splitter.split_documents(parent_docs))

    for i, chunk in enumerate(all_chunks):
        chunk.metadata["chunk_index"] = i
    return all_chunks

def get_parent_splitter() -> StructureAwareTextSplitter:
    return StructureAwareTextSplitter()