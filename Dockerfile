FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY migrations/ ./migrations/
COPY .env.example ./

ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=backend.app
ENV FLASK_RUN_HOST=0.0.0.0
ENV PYTHONPATH=/app

EXPOSE 5000
CMD ["python", "backend/app.py"]
