FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY pipeline ./pipeline

RUN pip install --no-cache-dir '.[pipeline]' \
    && useradd --uid 10001 --create-home --shell /usr/sbin/nologin hcg \
    && chown -R hcg:hcg /app

USER hcg
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
