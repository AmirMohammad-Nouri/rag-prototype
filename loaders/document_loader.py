from pathlib import Path
from loaders.pdf_loader import load_pdf
from loaders.docx_loader import load_docx


def load_document(file_path: str):
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return load_pdf(file_path)
    elif suffix == ".docx":
        return load_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")