FROM python:3.11-slim

WORKDIR /workspace

ENV PYTHONPATH=/workspace

COPY pipelines/engine/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY pipelines/engine /workspace/pipelines/engine