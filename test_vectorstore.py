from vectorstore import add_chunks, query, count
from embeddings import embed_passages, embed_query

texts = [
    "The maximum daily meal allowance is $75 for domestic travel.",
    "Passwords must be at least 12 characters and rotated every 90 days.",
]
metadatas = [
    {"source_filename": "expense_policy.docx", "department": "finance"},
    {"source_filename": "it_security_policy.pdf", "department": "it"},
]
ids = ["chunk-1", "chunk-2"]

vectors = embed_passages(texts)
add_chunks(ids=ids, texts=texts, embeddings=vectors, metadatas=metadatas)

print(f"Collection now has {count()} chunks\n")

question_vec = embed_query("What is the meal allowance?")
results = query(question_vec, top_k=2)

for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
    print(f"[{dist:.4f}] {meta['source_filename']}: {doc[:80]}...")

print("\n--- Now with department filter (should only return finance) ---")
filtered = query(question_vec, top_k=2, where={"department": "finance"})
for doc, meta in zip(filtered["documents"][0], filtered["metadatas"][0]):
    print(f"[{meta['department']}] {meta['source_filename']}: {doc[:80]}...")