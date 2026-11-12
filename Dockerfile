FROM python:3.15-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd -r -m -u 10001 app
COPY src/*.py ./
USER app
EXPOSE 8090
HEALTHCHECK --interval=60s --timeout=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8090/health',timeout=3)"
CMD ["gunicorn", "-w", "1", "--threads", "4", "-b", "0.0.0.0:8090", "--timeout", "30", "--access-logfile", "-", "app:app"]
