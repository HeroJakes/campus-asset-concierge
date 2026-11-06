FROM ghcr.io/astral-sh/uv:0.9.26 AS uv
FROM python:3.12-slim AS build
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable --no-cache --python /usr/local/bin/python

FROM python:3.12-slim
WORKDIR /app
RUN useradd --create-home --uid 10001 app
COPY --from=build /app/.venv /app/.venv
# Defaults target the localhost demo. Before deploying to a real host, set
# MCP_ALLOWED_HOSTS/MCP_ALLOWED_ORIGINS to that host or every request returns 421.
# See docs/MCP_LOCAL_CONTAINER.md.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    MCP_TRANSPORT=streamable-http \
    PORT=8080
USER app
EXPOSE 8080
CMD ["python", "-m", "campus_asset_concierge.mcp_server"]
