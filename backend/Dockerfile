FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini .
COPY content ./content
RUN useradd --system --uid 1001 syniq
USER syniq
EXPOSE 8000
# Bring the database schema and the content packs up to date, then serve. Only the web proxy can reach this port.
CMD ["sh", "-c", "alembic upgrade head && (python -m app.content_packs || echo 'Content packs not loaded') && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips='*'"]
