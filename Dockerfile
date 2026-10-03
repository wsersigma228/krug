FROM docker.io/library/python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt -c constraints.txt
COPY . .
CMD ["uvicorn", "backend.main:api", "--host", "0.0.0.0", "--port", "8000"]
