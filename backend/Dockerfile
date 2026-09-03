FROM python:3.12-slim

WORKDIR /app

# curl is used by the Compose healthcheck; build-essential covers any source
# builds pip falls back to for platforms without a prebuilt wheel.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install the CPU-only torch build first, from PyTorch's own index. The
# default PyPI torch wheel pulls in the full CUDA toolkit (~3GB of
# nvidia-*/cuda-* packages) as dependencies even though sentence-transformers
# only needs CPU inference for a MiniLM-sized model here — installing CPU
# torch up front satisfies sentence-transformers' torch requirement without
# ever touching the GPU stack.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model into the image so the first request (and
# every container restart) doesn't pay a cold-start download. If you change
# EMBEDDING_MODEL in .env away from the build default, the new model is
# fetched once on first use at runtime instead.
ARG EMBEDDING_MODEL=all-MiniLM-L6-v2
COPY app ./app
RUN python -c "from app.rag.embeddings import LocalSentenceTransformerProvider; LocalSentenceTransformerProvider('${EMBEDDING_MODEL}')"

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
