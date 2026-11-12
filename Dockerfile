FROM python:3.14-slim
ARG VERSION=dev
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 APP_VERSION=${VERSION} DATA_DIR=/data
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd -r -m -u 10001 app && mkdir -p /data && chown app /data
COPY src/ ./
USER app
EXPOSE 8090
VOLUME /data
HEALTHCHECK --interval=60s --timeout=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8090/health',timeout=3)"
CMD ["gunicorn", "-w", "1", "--threads", "8", "-b", "0.0.0.0:8090", "--timeout", "30", "--access-logfile", "-", "app:app"]
