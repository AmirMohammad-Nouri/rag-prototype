import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import chromadb
from chromadb.config import Settings as ChromaSettings
from config import settings
import chromadb
from chromadb.config import Settings as ChromaSettings
from config import settings


def get_collection():
    client = chromadb.PersistentClient(
        path=settings.chroma_persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(
        name=settings.chroma_collection_name,
        metadata={"hnsw:space": "cosine"},  # cosine similarity, standard for text embeddings
    )


def add_chunks(ids: list[str], texts: list[str], embeddings: list[list[float]], metadatas: list[dict]):
    collection = get_collection()
    # Chroma metadata values must be str/int/float/bool — None is not allowed,
    # so we sanitize here rather than pushing that concern onto every caller.
    clean_metadatas = [
        {k: v for k, v in m.items() if v is not None}
        for m in metadatas
    ]
    collection.add(ids=ids, documents=texts, embeddings=embeddings, metadatas=clean_metadatas)


def query(query_embedding: list[float], top_k: int, where: dict | None = None) -> dict:
    """where: Chroma metadata filter, e.g. {"department": "finance"}
    — this is the hook role-based filtering will use in Step 9."""
    collection = get_collection()
    return collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
    )


def count() -> int:
    return get_collection().count()