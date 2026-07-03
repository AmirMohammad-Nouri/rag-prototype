"""
Ingestion CLI. 
data/sample_docs/<department>/* -->  loads each file --> chunks into parent/child records --> embeds children --> stores children in
Chroma and parents in ParentStore.

"""
from pathlib import Path
from loaders.document_loader import load_document
from chunking import process_documents
from embeddings import embed_passages
from vectorstore import add_chunks
from storage.parent_store import ParentStore

SAMPLE_DOCS_ROOT = Path("data/sample_docs")
SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def main():
    parent_store = ParentStore()
    total_files = 0
    total_children = 0

    for department_dir in SAMPLE_DOCS_ROOT.iterdir():
        if not department_dir.is_dir():
            continue
        department = department_dir.name

        for file_path in department_dir.iterdir():
            if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            print(f"Ingesting {file_path} (department={department})...")
            documents = load_document(str(file_path))
            parents, children = process_documents(documents, department=department)

            if not children:
                print(f"  no content extracted, skipping")
                continue

            parent_store.add_many({p.parent_id: {"text": p.text, "metadata": p.metadata} for p in parents})

            child_texts = [c.text for c in children]
            child_vectors = embed_passages(child_texts)
            add_chunks(
                ids=[c.child_id for c in children],
                texts=child_texts,
                embeddings=child_vectors,
                metadatas=[c.metadata for c in children],
            )

            print(f"  {len(parents)} parents, {len(children)} children stored")
            total_files += 1
            total_children += len(children)

    print(f"\nDone. {total_files} files ingested, {total_children} child chunks stored.")
    print(f"Parent store has {parent_store.count()} parents total.")


if __name__ == "__main__":
    main()