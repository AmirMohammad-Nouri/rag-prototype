from pathlib import Path
import pdfplumber
from langchain_core.documents import Document


def _table_to_markdown(table_rows: list) -> str:
    rows = [[cell if cell is not None else "" for cell in row] for row in table_rows]
    if not rows:
        return ""
    header, *body = rows
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * len(header)) + " |"]
    for row in body:
        row = (row + [""] * len(header))[: len(header)]  # defensive padding
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _not_within_bboxes(obj, bboxes):
    v_mid = (obj["top"] + obj["bottom"]) / 2
    h_mid = (obj["x0"] + obj["x1"]) / 2
    for x0, top, x1, bottom in bboxes:
        if x0 <= h_mid < x1 and top <= v_mid < bottom:
            return False
    return True


def load_pdf(file_path: str) -> list[Document]:
    filename = Path(file_path).name
    documents: list[Document] = []

    with pdfplumber.open(file_path) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            found_tables = page.find_tables()
            table_bboxes = [t.bbox for t in found_tables]

            for table_index, table in enumerate(found_tables, start=1):
                markdown = _table_to_markdown(table.extract())
                if markdown.strip():
                    documents.append(Document(
                        page_content=markdown,
                        metadata={"source_filename": filename, "page_number": page_index,
                                  "type": "table", "table_index": table_index},
                    ))

            if table_bboxes:
                filtered_page = page.filter(lambda obj: _not_within_bboxes(obj, table_bboxes))
                text = (filtered_page.extract_text() or "").strip()
            else:
                text = (page.extract_text() or "").strip()

            if text:
                documents.append(Document(
                    page_content=text,
                    metadata={"source_filename": filename, "page_number": page_index, "type": "text"},
                ))

    return documents