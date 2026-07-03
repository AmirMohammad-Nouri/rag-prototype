
from embeddings import embed_query
from vectorstore import query as vector_query
from storage.parent_store import ParentStore
from llm_client import get_llm_client
from config import settings

SYSTEM_PROMPT = """You are an internal assistant answering questions using only the provided company documents.

Rules:
- Answer ONLY using the information in the provided context. Do not use outside knowledge.
- If the context does not contain enough information to answer, say so clearly instead of guessing.
- When you state a fact, mention which source it came from (the source is labeled in the context).
- Be precise with numbers, names, and dates — do not approximate or round figures from the source."""


def _build_context_block(parent_records: list[dict]) -> str:
    blocks = []
    for i, record in enumerate(parent_records, start=1):
        meta = record["metadata"]
        source = meta.get("source_filename", "unknown")
        location = f"page {meta['page_number']}" if meta.get("page_number") else f"section {meta.get('section_number', '?')}"
        blocks.append(f"[Source {i}: {source}, {location}]\n{record['text']}")
    return "\n\n---\n\n".join(blocks)


def answer_question(question: str, department_filter: str | None = None) -> dict:
    parent_store = ParentStore()

    # 1. Embed the question and search for matching CHILD chunks
    question_vector = embed_query(question)
    where = {"department": department_filter} if department_filter else None
    results = vector_query(question_vector, top_k=settings.top_k, where=where)

    child_metadatas = results["metadatas"][0] if results["metadatas"] else []
    if not child_metadatas:
        return {"answer": "I couldn't find any relevant documents to answer this question.",
                "sources": [], "usage": None}

    # 2. Resolve each matched child back to its full PARENT section,
    #    deduplicating (multiple children can point to the same parent)
    seen_parent_ids = set()
    parent_records = []
    for meta in child_metadatas:
        parent_id = meta.get("parent_id")
        if not parent_id or parent_id in seen_parent_ids:
            continue
        seen_parent_ids.add(parent_id)
        record = parent_store.get(parent_id)
        if record:
            parent_records.append(record)

    # 3. Build the prompt and call the LLM
    context_block = _build_context_block(parent_records)
    user_prompt = f"Context:\n\n{context_block}\n\n---\n\nQuestion: {question}"
    print(user_prompt)
    
    llm = get_llm_client()
    result = llm.generate(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)

    sources = [
        {"source_filename": r["metadata"].get("source_filename"),
         "location": r["metadata"].get("page_number") or r["metadata"].get("section_number"),
         "department": r["metadata"].get("department")}
        for r in parent_records
    ]

    return {"answer": result["text"], "sources": sources, "usage": result["usage"]}