# API image: FastAPI + scan pipeline (CPU-only torch for the dense retriever).
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf
WORKDIR /app

COPY requirements.lock pyproject.toml README.md ./
# The +cpu torch wheel from the extra index satisfies the torch==x.y.z pin without CUDA.
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.lock \
 && pip install "psycopg[binary]==3.2.3"

COPY src ./src
RUN pip install -e . --no-deps
# Bake the embedding model into the image so scans don't download it at runtime.
RUN python -c "from sentence_transformers import SentenceTransformer as S; S('sentence-transformers/all-MiniLM-L6-v2')"

COPY data/kb ./data/kb
COPY results ./results

RUN useradd --create-home app && mkdir -p /app/.cache /data && chown -R app /app /data
USER app

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"
CMD ["uvicorn", "codemigrate.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
