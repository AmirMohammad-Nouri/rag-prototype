from embeddings import embed_query, embed_passages

query_vec = embed_query("What is the meal allowance for travel?")
print(f"Query embedding dimensions: {len(query_vec)}")
print(f"First 5 values: {query_vec[:5]}")

passage_vecs = embed_passages([
    "The maximum daily meal allowance is $75 for domestic travel.",
    "Passwords must be at least 12 characters.",
])
print(f"\nEmbedded {len(passage_vecs)} passages, each with {len(passage_vecs[0])} dimensions")