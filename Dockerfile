FROM docker.io/library/python:3.14.8-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt -c constraints.txt
COPY . .
# Photo mount point; a new named volume copies this ownership, existing volumes need scripts/start's chown.
# COPY keeps host modes; a checkout made under umask 077 would otherwise be unreadable to app.
RUN chmod -R a+rX /app \
 && groupadd --gid 10001 app \
 && useradd --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app \
 && mkdir -p /app/media \
 && chown app:app /app/media
USER app
CMD ["uvicorn", "backend.main:api", "--host", "0.0.0.0", "--port", "8000"]
