FROM node:24-slim AS frontend

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend ./

FROM frontend AS frontend-build
RUN npm run build

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
RUN mkdir -p src/mache_cells \
    && touch src/mache_cells/__init__.py \
    && pip install ".[dev]" \
    && pip uninstall -y mache-cell-voltages

COPY src ./src
COPY --from=frontend-build /frontend/dist ./src/mache_cells/web
RUN pip install --no-deps -e .
COPY tests ./tests

EXPOSE 8080
CMD ["mache-cells", "serve"]
