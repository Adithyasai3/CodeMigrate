# Hugging Face Space image: builds the React UI and serves it from the FastAPI app on one port.
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf WEB_DIR=/app/web LLM_PROVIDER=offline
WORKDIR /app

COPY requirements.lock pyproject.toml README.md ./
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.lock

COPY src ./src
RUN pip install -e . --no-deps
RUN python -c "from sentence_transformers import SentenceTransformer as S; S('sentence-transformers/all-MiniLM-L6-v2')"

COPY data/kb ./data/kb
COPY results ./results
COPY --from=web /web/dist ./web

# Spaces run the container as uid 1000.
RUN useradd -m -u 1000 app && mkdir -p /app/.cache && chown -R app /app /opt/hf
USER app

EXPOSE 7860
CMD ["uvicorn", "codemigrate.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
