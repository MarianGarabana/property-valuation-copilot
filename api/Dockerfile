# Hugging Face Spaces Docker convention: the app must listen on port 7860.
# Build context is the repo root:  docker build -f api/Dockerfile -t pvc-api .
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    KMP_DUPLICATE_LIB_OK=TRUE \
    OMP_NUM_THREADS=4 \
    MLFLOW_ALLOW_FILE_STORE=true \
    PORT=7860

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

# The value path needs: model artifacts (mlruns/), processed data
# (data/processed/listings.parquet) and the SHAP cache. Ship them in the
# image or mount/fetch at startup (Phase 7 deploy-cache decision).
COPY . .

EXPOSE 7860

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
