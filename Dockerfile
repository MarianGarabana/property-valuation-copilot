# API service image, deployed on Render's free tier. Listens on $PORT
# (Render injects it; 7860 stays the local default).
# Build context is the repo root:  docker build -t pvc-api .
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    KMP_DUPLICATE_LIB_OK=TRUE \
    OMP_NUM_THREADS=1 \
    MALLOC_ARENA_MAX=2 \
    MLFLOW_ALLOW_FILE_STORE=true \
    PORT=7860

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Slim serving dependencies only (no torch/torchvision/streamlit/plotly/pydeck;
# the production model is LightGBM and those are not on the serving import path).
COPY api/requirements.txt ./api/requirements.txt
RUN pip install -r api/requirements.txt

# Application code and the git-tracked processed parquet. mlruns/ and the SHAP
# cache are excluded by .dockerignore; the model is fetched below and SHAP is
# recomputed per property on demand.
COPY . .

# Fetch the production MLflow run subtree (~22M, 8.4M gzipped) from a public
# model repo and reconstruct it under mlruns/, so predict.py resolves the model
# via the is_production tag with no code change. Pinned to an immutable revision
# SHA for reproducible builds.
ARG MODEL_BUNDLE_REVISION=e7ab195a35fbad3ce6bc9df2eb749c3977577b2e
ARG MODEL_BUNDLE_URL=https://huggingface.co/MarianGarabana/property-valuation-model/resolve/${MODEL_BUNDLE_REVISION}/production_run.tar.gz
RUN curl -fsSL "$MODEL_BUNDLE_URL" -o /tmp/production_run.tar.gz \
    && tar xzf /tmp/production_run.tar.gz -C . \
    && rm /tmp/production_run.tar.gz \
    && test -f mlruns/494524669144656547/f52e8fc77a9d4a528d48e6ff6103b3b2/tags/is_production \
    && sed -i -E "s|file://[^[:space:]]*/mlruns|file:///app/mlruns|" \
        mlruns/494524669144656547/meta.yaml \
        mlruns/494524669144656547/f52e8fc77a9d4a528d48e6ff6103b3b2/meta.yaml

# Build-time proof the model resolves exactly the way predict.py resolves it.
# A bundle, path, or metadata defect fails the build here instead of the runtime.
RUN python -c "\
import sys; sys.path.insert(0, 'models/tabular'); \
import predict; b = predict._load_bundle(); \
assert b['_booster'] is not None and b['_q05'] is not None and b['_q95'] is not None; \
print('model bundle resolves, run', b['run_id'])"

EXPOSE 7860

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
