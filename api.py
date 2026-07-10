
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag_pipeline import answer_question

app = FastAPI(title="RAG Prototype API")

# Local-only CORS for the static HTML frontend — tighten before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str
    department: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/departments")
def departments():
    """Reads department names straight from the sample_docs folder structure —
    keeps the UI's department selector in sync with what was actually ingested."""
    root = Path("data/sample_docs")
    if not root.exists():
        return {"departments": []}
    return {"departments": sorted([d.name for d in root.iterdir() if d.is_dir()])}


@app.post("/ask")
def ask(request: AskRequest):
    return answer_question(request.question, department_filter=request.department)