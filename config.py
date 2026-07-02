
from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {key}. "
            f"Copy .env.example to .env and fill it in."
        )
    return value


@dataclass(frozen=True)
class Settings:
    zhipu_api_key: str
    zhipu_base_url: str
    llm_model: str

    jina_api_key: str
    jina_embedding_model: str

    chroma_persist_dir: str
    chroma_collection_name: str

    chunk_size_tokens: int
    chunk_overlap_tokens: int

    top_k: int


def load_settings() -> Settings:
    return Settings(
        zhipu_api_key=_require("ZHIPU_API_KEY"),
        zhipu_base_url=os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
        llm_model=os.getenv("LLM_MODEL", "glm-4.5-flash"),

        jina_api_key=_require("JINA_API_KEY"),
        jina_embedding_model=os.getenv("JINA_EMBEDDING_MODEL", "jina-embeddings-v3"),

        chroma_persist_dir=os.getenv("CHROMA_PERSIST_DIR", "./storage/chroma_db"),
        chroma_collection_name=os.getenv("CHROMA_COLLECTION_NAME", "company_docs"),

        chunk_size_tokens=int(os.getenv("CHUNK_SIZE_TOKENS", "500")),
        chunk_overlap_tokens=int(os.getenv("CHUNK_OVERLAP_TOKENS", "50")),

        top_k=int(os.getenv("TOP_K", "5")),
    )


settings = load_settings()