import requests
from config import settings

JINA_API_URL = "https://api.jina.ai/v1/embeddings"


def embed_texts(texts: list[str], task: str = "retrieval.passage") -> list[list[float]]:
    if not texts:
        return []

    headers = {
        "Authorization": f"Bearer {settings.jina_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.jina_embedding_model,
        "task": task,
        "input": texts,
    }

    response = requests.post(JINA_API_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()

    data = response.json()
    # Jina returns results possibly out of order under "data", each with an "index" field.
    sorted_results = sorted(data["data"], key=lambda x: x["index"])
    return [item["embedding"] for item in sorted_results]


def embed_query(query: str) -> list[float]:
    return embed_texts([query], task="retrieval.query")[0]


def embed_passages(texts: list[str]) -> list[list[float]]:
    return embed_texts(texts, task="retrieval.passage")