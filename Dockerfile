FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NODE_RED_MCP_TRANSPORT=http \
    NODE_RED_MCP_HOST=0.0.0.0 \
    NODE_RED_MCP_PORT=8000

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip install --no-cache-dir .

EXPOSE 8000

CMD ["nodered-mcp"]
