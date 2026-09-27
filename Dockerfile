FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py errors.py image.py logging_config.py settings.py ./

ENV HOST=0.0.0.0
ENV PORT=8000
ENV WORKERS=2

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app:app --host ${HOST} --port ${PORT} --workers ${WORKERS}"]
