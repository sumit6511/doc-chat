# DocChat — Backend

FastAPI service implementing the RAG pipeline: PDF ingestion, chunking, embeddings, MongoDB
Atlas Vector Search retrieval, and LLM generation via Ollama.

See the [root README](../README.md) for the full architecture, MongoDB Atlas setup, and Docker
instructions. This file covers just the backend-local quick start.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp ../.env.example .env         # fill in MONGODB_URI at minimum
uvicorn app.main:app --reload
```

API: `http://localhost:8000` · Interactive docs: `http://localhost:8000/docs`

## Tests

```bash
pytest
```

No live MongoDB Atlas cluster, Ollama instance, or downloaded ML model is required — see
[Testing](../README.md#testing) in the root README for what's mocked and why.

## Layout

```text
app/
├── main.py, config.py, errors.py, logging_config.py   # app wiring
├── api/          # thin FastAPI routes + dependency injection (deps.py)
├── db/           # Motor client, indexes, one repository per collection
├── models/       # internal MongoDB-backed Pydantic models
├── schemas/      # API request/response Pydantic models
├── services/     # business logic (upload validation, ingestion, chat orchestration)
├── rag/          # chunker, embeddings, retrieval, context builder, prompts, pipeline
└── llm/          # LLMProvider interface + OllamaProvider
```

`app/rag/pipeline.py::RAGPipeline` is the one place that ties retrieval, context building, and
generation together — start there to understand the request flow for `POST
/conversations/{id}/messages`.
