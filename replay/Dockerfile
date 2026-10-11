FROM python:3.11-slim-bookworm
ENV PYTHONUNBUFFERED=1
WORKDIR /workspace
COPY replay/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY . .
RUN pip install --no-cache-dir .
CMD ["python", "-m", "replay.replay_producer"]
