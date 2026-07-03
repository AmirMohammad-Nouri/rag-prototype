# Enterprise RAG Prototype

A Retrieval-Augmented Generation (RAG) system that answers questions using a company's own documents (PDF, DOCX) instead of relying on an LLM's general knowledge. Built as a proof-of-concept to validate the core mechanism — ingestion, retrieval, and grounded generation — before scaling to a production system handling 100K–1M documents.

Every answer is generated strictly from retrieved document content and returned with **source citations**, so users can verify where information came from rather than trusting the model blindly.

---

## Table of Contents

- [Why this exists](#why-this-exists)
- [Features](#features)
- [Architecture](#architecture)
- [Project structure](#project-structure)
- [Setup](#setup)
- [Usage](#usage)
- [Code walkthrough](#code-walkthrough)
- [Design decisions](#design-decisions)
- [Known limitations (prototype scope)](#known-limitations-prototype-scope)
- [Roadmap](#roadmap)

---

## Why this exists

Generic LLMs don't know a company's internal documents and will either say "I don't know" or — worse — hallucinate a plausible-sounding but wrong answer. RAG solves this by:

1. Storing company documents as searchable vector embeddings
2. Retrieving the most relevant passages for a given question
3. Feeding only that retrieved content to the LLM as context
4. Generating an answer grounded in that context, with citations

This repo is the **prototype stage**: it proves the mechanism works end-to-end on real PDF/DOCX documents, using free/open and low-cost API-based components, before the team commits to a production architecture (self-hosted models, larger-scale vector DB, full access-control system, etc.).

---

## Features

- **Table-aware document parsing** — tables in PDFs and DOCX files are extracted as clean markdown, not flattened into scrambled text. This matters for financial/billing data where row/column structure carries meaning.
- **Structure-aware + parent-child chunking** — documents are split along natural section boundaries (not arbitrary character counts), and retrieval uses small precise chunks for search while the LLM sees the full parent section for context.
- **Grounded generation with citations** — the LLM is instructed to answer only from retrieved context and to cite which source each fact came from. If nothing relevant is found, it says so instead of guessing.
- **Department-based metadata filtering** — every stored chunk is tagged with an owning department at ingestion time, and retrieval queries can be filtered by it — the foundation for role-based access control.
- **Retry with exponential backoff** — external API calls (embeddings) retry automatically on transient failures instead of crashing the pipeline.
- **Swappable components** — vector store, embedding provider, and LLM provider are each isolated behind a single module, so upgrading any one (e.g. Chroma → Qdrant, GLM → another model) doesn't require touching the rest of the codebase.
- **Config centralization** — all settings load from `.env` through one `config.py`, nothing is hardcoded or scattered across files.

---

## Architecture

```
                     ┌─────────────────────┐
                     │   PDF / DOCX files    │
                     └──────────┬───────────┘
                                │
                    ┌───────────▼────────────┐
                    │   Document Loaders       │  loaders/
                    │  (table-aware extraction)│
                    └───────────┬────────────┘
                                │
                    ┌───────────▼────────────┐
                    │       Chunking            │  chunking.py
                    │  structure-aware split →  │
                    │  parent sections →         │
                    │  recursive split → children│
                    └──────┬─────────────┬──────┘
                           │             │
                 ┌─────────▼───┐   ┌─────▼──────────┐
                 │ Parent Store  │   │  Embeddings      │  embeddings.py
                 │ (full text)   │   │  (Jina API)       │
                 │ storage/      │   └─────┬──────────┘
                 └───────▲───────┘         │
                         │           ┌─────▼──────────┐
                         │           │  Vector Store     │  vectorstore.py
                         │           │  (Chroma, +dept   │
                         │           │   metadata filter)│
                         │           └─────┬──────────┘
                         │                 │
                    ┌────┴─────────────────▼────┐
                    │        RAG Pipeline           │  rag_pipeline.py
                    │  question → embed → search →  │
                    │  resolve parents → prompt →   │
                    │  LLM → answer + citations     │
                    └───────────────┬────────────┘
                                    │
                          ┌─────────▼─────────┐
                          │   LLM (GLM-4.5)      │  llm_client.py
                          └───────────────────┘
```

**Key design principle: small chunks for search, large chunks for context.** A short, precise chunk matches a specific question well in vector search, but an isolated sentence often lacks the context an LLM needs to answer correctly. This system embeds and searches small "child" chunks, then swaps each matched child for its full "parent" section before generation — the retrieval accuracy of small chunks, the context quality of large ones.

---

## Project structure

```
rag-prototype/
├── config.py                 # Centralized settings, loaded from .env
├── loaders/
│   ├── pdf_loader.py          # Table-aware PDF extraction (pdfplumber)
│   ├── docx_loader.py         # Table-aware DOCX extraction (python-docx)
│   └── document_loader.py     # Dispatches by file extension
├── chunking.py                # Structure-aware + recursive + parent/child chunking
├── embeddings.py              # Jina AI embedding client, with retry/backoff
├── vectorstore.py             # Chroma wrapper (storage + metadata-filtered search)
├── llm_client.py              # GLM-4.5 client (OpenAI-SDK-compatible)
├── rag_pipeline.py            # Core RAG loop: retrieve → resolve parents → generate
├── ingest.py                  # CLI: walk data/sample_docs/<department>/, ingest all files
├── ask.py                     # CLI: interactive question-answering
├── storage/
│   └── parent_store.py        # JSON-backed store for full parent sections
├── data/sample_docs/
│   ├── finance/                # Sample docs tagged "finance" department
│   └── it/                     # Sample docs tagged "it" department
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Setup

**1. Clone and install dependencies:**
```bash
git clone <your-repo-url>
cd rag-prototype
pip install -r requirements.txt
```

**2. Configure environment variables:**
```bash
cp .env.example .env
```
Edit `.env` and fill in:
- `ZHIPU_API_KEY` — from [Zhipu AI's platform](https://open.bigmodel.cn) (GLM-4.5 access)
- `JINA_API_KEY` — from [Jina AI](https://jina.ai) (embeddings)

**3. Add documents to ingest**, organized by department (folder name becomes the access-control tag):
```
data/sample_docs/
├── finance/
│   └── expense_policy.docx
└── it/
    └── it_security_policy.pdf
```

**4. Run ingestion:**
```bash
python ingest.py
```

**5. Ask questions:**
```bash
python ask.py
```

---

## Usage

```
$ python ask.py
RAG prototype — ask a question (type 'exit' to quit)

> What is the maximum daily meal allowance for domestic travel?

The maximum daily meal allowance is $75 for domestic travel and $100 for
international travel, according to the expense policy.

Sources:
  - expense_policy.docx (page/section 2, dept: finance)

[tokens: 412]
```

---

## Code walkthrough

### `config.py` — centralized configuration
Every setting (API keys, model names, chunk sizes, top-k) is read from environment variables in exactly one place. Every other module imports `settings` from here rather than calling `os.getenv` directly — this means changing a provider or tuning a parameter never requires hunting through multiple files.

### `loaders/pdf_loader.py` and `loaders/docx_loader.py` — table-aware extraction
Naive text extraction (`pypdf`'s default, or `docx2txt`) flattens tables into a stream of words with no row/column structure — a table row like `2010  Average  104  201` becomes indistinguishable from prose, which corrupts both chunking (a number can look like a section heading) and the LLM's understanding of what the numbers mean.

These loaders use `pdfplumber` (PDF) and direct `python-docx` traversal (DOCX) to detect table regions explicitly and serialize them as **markdown tables**, kept completely separate from surrounding prose text. Each extracted piece is tagged `metadata["type"] = "table"` or `"text"` so downstream chunking treats them differently.

### `chunking.py` — structure-aware + recursive + parent/child splitting
Three techniques, applied in sequence, not as alternatives:
1. **`StructureAwareTextSplitter`** — a custom splitter that detects heading patterns (`"Section 1:"`, `"1.1 Introduction"`, etc.) and splits text into topic-coherent parent sections. Falls back to treating the whole page as one section if no headings are detected.
2. **`RecursiveCharacterTextSplitter`** (LangChain) — runs on every parent section to enforce a target chunk size, splitting on paragraph/sentence boundaries where possible rather than cutting mid-sentence.
3. **Table splitting** — markdown tables are split by row groups instead, always repeating the header row in every piece, so a table chunk is never ambiguous about what its columns mean.

Every child chunk carries `metadata["parent_id"]`, linking it back to its full parent section.

### `embeddings.py` — Jina embedding client with retry
Wraps Jina's embeddings API with two query modes (`retrieval.passage` for documents, `retrieval.query` for questions — required by the underlying model for optimal accuracy) and automatic retry with exponential backoff (2s → 4s → 8s) on failures, since this external dependency has shown intermittent errors in testing.

### `vectorstore.py` — Chroma wrapper
Stores child chunks with their embeddings and metadata in a local persistent Chroma collection. Embeddings are computed externally (via `embeddings.py`) and passed in explicitly, rather than letting Chroma manage embedding internally — this guarantees ingestion and query always use the identical model, with no risk of silent mismatch. The `query()` function accepts a `where` filter, which is the mechanism department-based access control uses.

### `storage/parent_store.py` — parent section storage
A simple JSON-backed key-value store for full parent sections, keyed by `parent_id`. Kept deliberately simple for the prototype; swappable for a real database in production without touching any calling code.

### `llm_client.py` — GLM-4.5 client
Thin wrapper around the OpenAI-compatible SDK pointed at Zhipu's endpoint. Every call goes through `LLMClient.generate()`, never the raw SDK — this is what will make a future model fallback chain a one-file change instead of a codebase-wide refactor. Temperature defaults low (0.1), since RAG generation should stick closely to retrieved context rather than being creative.

### `rag_pipeline.py` — the core RAG loop
Ties everything together: embed the question → search Chroma for matching child chunks (optionally filtered by department) → deduplicate and resolve each match to its full parent section → build a prompt with clearly labeled sources → call the LLM → return the answer alongside a structured source list. The system prompt explicitly instructs the model to answer only from provided context and to say so when it can't.

### `ingest.py` and `ask.py` — CLI entry points
`ingest.py` walks `data/sample_docs/<department>/`, so folder structure directly becomes the department metadata tag used for access filtering. `ask.py` is a minimal interactive loop for manually testing questions against the ingested corpus.

---

## Design decisions

| Decision | Reasoning |
|---|---|
| Parent-child chunking over flat chunking | Small chunks retrieve accurately; large chunks generate accurately. Using one chunk size for both is a compromise that hurts one or the other. |
| Table extraction as a separate path | Flattened table text broke both chunking (false heading matches) and answer accuracy (misread numbers). Verified with real test output during development. |
| Metadata filtering at the vector-store level | Access control has to happen *before* results come back, not by filtering the LLM's output — that's a real security boundary, not a prompt instruction. |
| Config centralized in one file | Swapping any provider (embeddings, LLM, vector DB) should mean editing one file, not searching the codebase for hardcoded values. |
| Low temperature (0.1) for generation | RAG answers should reflect the source documents, not the model's creativity. |

---

## Known limitations (prototype scope)

These are deliberately out of scope for this stage, not oversights:

- **No OCR** — scanned/image-only PDF pages are skipped, not processed.
- **No speech-to-text** — voice source documents aren't yet supported.
- **No model fallback chain** — a single LLM provider (GLM-4.5) with no automatic failover.
- **No full observability stack** — no request tracing, structured logging, or metrics endpoint yet.
- **Not containerized** — runs as local Python scripts, no Docker packaging yet.
- **No automated tests** — validated manually during development so far.
- **Sample/non-confidential data only** — this prototype has not been evaluated against real company documents; using it with confidential data requires a decision from legal/security on whether third-party API usage (LLM + embeddings) is acceptable, given data leaves company infrastructure.

## Roadmap

- [ ] Role-based access control demo (sample users/departments, visible query filtering)
- [ ] OCR ingestion (scanned PDFs/images)
- [ ] Speech-to-text ingestion (voice sources)
- [ ] Retrieval + answer quality evaluation set
- [ ] Model fallback chain, retry logic on generation calls
- [ ] Structured logging, metrics endpoint, request tracing
- [ ] FastAPI wrapper with Pydantic validation, rate limiting, input sanitization
- [ ] Dockerize + docker-compose for local/staging
- [ ] Automated test suite
- [ ] Scale-out to production vector DB (Qdrant/Milvus) for 100K–1M document corpus