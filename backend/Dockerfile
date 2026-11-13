FROM python:3.13-alpine
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY server.py .
RUN apk add --no-cache tzdata && addgroup -S app && adduser -S -G app app && mkdir -p /data && chown app:app /data
USER app
EXPOSE 8000
CMD ["python", "server.py"]
