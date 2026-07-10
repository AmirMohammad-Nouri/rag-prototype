
import time
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

# Below this relevance score, we treat the result as "not confident" —
# tune this against your own corpus; cosine-distance-derived scores vary
# by embedding model.
LOW_CONFIDENCE_THRESHOLD = 0.35


def _distance_to_relevance(distance: float) -> float:
    """Chroma returns cosine DISTANCE (0 = identical, 2 = opposite).
    Convert to a 0-1 relevance score that's intuitive to display."""
    relevance = 1 - (distance / 2)
    return max(0.0, min(1.0, relevance))


def _build_context_block(sources: list[dict]) -> str:
    blocks = []
    for i, s in enumerate(sources, start=1):
        meta = s["parent_metadata"]
        loc = f"page {meta['page_number']}" if meta.get("page_number") else f"section {meta.get('section_number', '?')}"
        blocks.append(f"[Source {i}: {meta.get('source_filename', 'unknown')}, {loc}]\n{s['parent_text']}")
    return "\n\n---\n\n".join(blocks)


def answer_question(question: str, department_filter: str | None = None) -> dict:
    stages = []
    parent_store = ParentStore()

    t0 = time.perf_counter()
    question_vector = embed_query(question)
    stages.append({"name": "embed", "duration_ms": round((time.perf_counter() - t0) * 1000, 1)})

    t1 = time.perf_counter()
    where = {"department": department_filter} if department_filter else None
    results = vector_query(question_vector, top_k=settings.top_k, where=where)
    stages.append({"name": "search", "duration_ms": round((time.perf_counter() - t1) * 1000, 1)})

    child_metadatas = results["metadatas"][0] if results["metadatas"] else []
    child_documents = results["documents"][0] if results["documents"] else []
    child_distances = results["distances"][0] if results["distances"] else []

    t2 = time.perf_counter()
    seen_parent_ids = set()
    sources = []
    for meta, child_text, distance in zip(child_metadatas, child_documents, child_distances):
        parent_id = meta.get("parent_id")
        if not parent_id or parent_id in seen_parent_ids:
            continue
        seen_parent_ids.add(parent_id)
        parent_record = parent_store.get(parent_id)
        if not parent_record:
            continue
        sources.append({
            "child_text": child_text,
            "parent_text": parent_record["text"],
            "parent_metadata": parent_record["metadata"],
            "relevance": round(_distance_to_relevance(distance), 4),
        })
    stages.append({"name": "resolve_parents", "duration_ms": round((time.perf_counter() - t2) * 1000, 1)})

    if not sources:
        stages.append({"name": "generate", "duration_ms": 0})
        return {
            "answer": "I couldn't find any relevant documents to answer this question.",
            "sources": [], "usage": None, "stages": stages,
            "low_confidence": True,
        }

    t3 = time.perf_counter()
    context_block = _build_context_block(sources)
    user_prompt = f"Context:\n\n{context_block}\n\n---\n\nQuestion: {question}"
    llm = get_llm_client()
    result = llm.generate(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)
    stages.append({"name": "generate", "duration_ms": round((time.perf_counter() - t3) * 1000, 1)})

    top_relevance = max(s["relevance"] for s in sources)

    return {
        "answer": result["text"],
        "sources": [
            {
                "source_filename": s["parent_metadata"].get("source_filename"),
                "location": s["parent_metadata"].get("page_number") or s["parent_metadata"].get("section_number"),
                "department": s["parent_metadata"].get("department"),
                "relevance": s["relevance"],
                "child_text": s["child_text"],
                "parent_text": s["parent_text"],
            }
            for s in sources
        ],
        "usage": result["usage"],
        "stages": stages,
        "low_confidence": top_relevance < LOW_CONFIDENCE_THRESHOLD,
    }