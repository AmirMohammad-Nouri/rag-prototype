
import re
import uuid
from dataclasses import dataclass, field
from langchain_text_splitters import TextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from config import settings

CHARS_PER_TOKEN = 4

HEADING_PATTERN = re.compile(
    r"^(?:"
    r"Section\s+\d+[:.]?|"
    r"Chapter\s+\d+[:.]?|"
    r"\d+(?:\.\d+)*\s+[A-Z][A-Za-z ,'\-]{2,80}$|"
    r"[A-Z][A-Z ]{4,60}"
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
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size_tokens * CHARS_PER_TOKEN,
        chunk_overlap=settings.chunk_overlap_tokens * CHARS_PER_TOKEN,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def _split_markdown_table(markdown: str, max_chars: int) -> list[str]:
    lines = markdown.split("\n")
    if len(lines) < 2:
        return [markdown]
    header_lines = lines[:2]
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


@dataclass
class ParentRecord:
    parent_id: str
    text: str
    metadata: dict


@dataclass
class ChildRecord:
    child_id: str
    text: str
    metadata: dict  # includes parent_id


def process_documents(documents: list[Document], department: str) -> tuple[list[ParentRecord], list[ChildRecord]]:
    parent_splitter = StructureAwareTextSplitter()
    child_splitter = get_child_splitter()
    max_chars = settings.chunk_size_tokens * CHARS_PER_TOKEN

    parents: list[ParentRecord] = []
    children: list[ChildRecord] = []

    for doc in documents:
        base_meta = dict(doc.metadata)
        base_meta["department"] = department

        if base_meta.get("type") == "table":
            parent_id = str(uuid.uuid4())
            parents.append(ParentRecord(parent_id=parent_id, text=doc.page_content, metadata=base_meta))
            for piece in _split_markdown_table(doc.page_content, max_chars):
                children.append(ChildRecord(
                    child_id=str(uuid.uuid4()), text=piece,
                    metadata={**base_meta, "parent_id": parent_id},
                ))
        else:
            for parent_text in parent_splitter.split_text(doc.page_content):
                parent_id = str(uuid.uuid4())
                parents.append(ParentRecord(parent_id=parent_id, text=parent_text, metadata=base_meta))
                for child_text in child_splitter.split_text(parent_text):
                    children.append(ChildRecord(
                        child_id=str(uuid.uuid4()), text=child_text,
                        metadata={**base_meta, "parent_id": parent_id},
                    ))

    return parents, children