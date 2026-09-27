# REST API image for iso8583sim. See docs/web/index.md.
FROM python:3.12-slim

# subhadipmitra@: Extras to install. The default covers the REST API, PIN blocks and MACs,
# and the Anthropic LLM provider. Use --build-arg EXTRAS=web,security,llm for all providers.
ARG EXTRAS=web,security,anthropic

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# subhadipmitra@: Copy only what the package build needs, so local files (virtualenvs,
# compiled extensions, notebooks) never end up in the image.
COPY pyproject.toml README.md LICENSE ./
COPY iso8583sim ./iso8583sim
RUN pip install --no-cache-dir ".[${EXTRAS}]"

# subhadipmitra@: Run as an unprivileged user rather than root.
RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

# subhadipmitra@: Listen on all interfaces inside the container so a published port can
# reach it. Publish with -p 127.0.0.1:8000:8000 to keep it local to the host.
CMD ["iso8583sim", "web", "--host", "0.0.0.0", "--port", "8000"]
