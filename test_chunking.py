from loaders.document_loader import load_document
from chunking import get_parent_splitter, get_child_splitter

docs = load_document(r"data\sample_docs\sample-tables.pdf")

parent_splitter = get_parent_splitter()
parent_docs = parent_splitter.split_documents(docs)
print(f"Loaded {len(docs)} pages -> {len(parent_docs)} structure-aware parent sections\n")

for p in parent_docs:
    print(f"--- parent (page={p.metadata.get('page_number')}) ---")
    print(p.page_content.replace("\n", " "))

child_splitter = get_child_splitter()
child_docs = child_splitter.split_documents(parent_docs)
print(f"\n{len(parent_docs)} parents -> {len(child_docs)} child chunks")