FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

RUN mkdir /interface
WORKDIR /interface

COPY pyproject.toml uv.lock /interface/

RUN uv sync --frozen --no-install-project --no-dev

COPY interface /interface/

RUN uv sync --frozen --no-dev

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN mkdir -p /interface/static /interface/data /interface/media

EXPOSE 20000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uv", "run", "gunicorn", "--bind", ":20000", "--workers", "3", "h4kslanding.wsgi:application"]
