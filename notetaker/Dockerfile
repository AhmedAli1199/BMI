FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY notetaker ./notetaker
RUN useradd -r -u 10001 app && chown -R app /app
USER app
EXPOSE 8080
CMD ["uvicorn", "notetaker.api.app:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
