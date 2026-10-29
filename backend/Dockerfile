FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/models

WORKDIR /app

# Local compose leaves this true and installs the embedding model.
# compose.prod.yaml sets it false so the API image skips torch.
ARG INSTALL_EMBEDDINGS=true
COPY requirements.txt requirements-prod.txt ./
RUN pip install --upgrade pip \
    && if [ "$INSTALL_EMBEDDINGS" = "true" ]; then \
         pip install -r requirements.txt \
         && python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"; \
       else \
         pip install -r requirements-prod.txt; \
       fi

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY evaluations ./evaluations
COPY scripts ./scripts
COPY entrypoint.sh .
RUN chmod 755 entrypoint.sh \
    && useradd --create-home --uid 10001 stride \
    && chown -R stride:stride /app
USER stride

EXPOSE 8000
CMD ["./entrypoint.sh"]
