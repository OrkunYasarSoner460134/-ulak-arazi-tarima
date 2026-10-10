FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py index.html ./
COPY Ulak/llm ./llm
COPY Ulak/validation ./validation

ENV PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:' + __import__('os').environ.get('PORT','8000') + '/health')"
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
