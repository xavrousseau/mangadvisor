FROM python:3.11-slim

WORKDIR /workspace

COPY apps/ui/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY apps/ui /workspace/apps/ui

CMD ["streamlit", "run", "apps/ui/app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
