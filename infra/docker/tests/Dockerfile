# Disposable regression runner. Separate from runtime engine and API images.
# Build from repository root with: docker build -f infra/docker/tests/Dockerfile .
FROM python:3.11-slim
WORKDIR /workspace
ENV PYTHONPATH=/workspace PYTHONDONTWRITEBYTECODE=1
COPY pipelines/engine/requirements.txt /tmp/engine-requirements.txt
COPY apps/api/requirements.txt /tmp/api-requirements.txt
RUN pip install --no-cache-dir -r /tmp/engine-requirements.txt -r /tmp/api-requirements.txt
# Include menu, Compose, SQL, application, and tests needed for repository audits.
# .dockerignore excludes personal and runtime data from this context.
COPY . /workspace
CMD ["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"]
