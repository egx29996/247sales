FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir . && \
    python -c "import nltk; nltk.download('punkt_tab', quiet=True)"

COPY src/ src/

VOLUME /app/data

CMD ["python", "-m", "src.main"]
