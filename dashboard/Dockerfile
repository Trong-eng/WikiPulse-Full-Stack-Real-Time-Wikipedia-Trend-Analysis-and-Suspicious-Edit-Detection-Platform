FROM python:3.11-slim

WORKDIR /app
COPY dashboard/requirements.txt /app/dashboard/requirements.txt
RUN pip install --no-cache-dir -r dashboard/requirements.txt
COPY . /app
RUN pip install --no-cache-dir .

EXPOSE 8501
CMD ["streamlit", "run", "dashboard/app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", "--browser.gatherUsageStats=false"]
