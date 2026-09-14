FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

COPY requirements-webapp.txt ./
RUN pip install --no-cache-dir -r requirements-webapp.txt

COPY webapp ./webapp

EXPOSE 8000

# Render supplies PORT at runtime. One worker is intentional: the app keeps its
# small fixture cache in memory and permits only one paid agent run at a time.
CMD ["sh", "-c", "exec uvicorn webapp.app.endpoints:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
