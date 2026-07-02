from loaders.document_loader import load_document

pdf_docs = load_document(r"data\sample_docs\sample-tables.pdf")
for d in pdf_docs:
    print(f"[page {d.metadata['page_number']}] {d.page_content[:80]}...")

docx_docs = load_document(r"data\sample_docs\Event Source User Guide.docx")
for d in docx_docs:
    print(f"[{d.metadata['source_filename']}] {d.page_content[:80]}...")