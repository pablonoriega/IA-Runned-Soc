FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY simulator_api.py .
EXPOSE 9000
CMD ["uvicorn", "simulator_api:app", "--host", "0.0.0.0", "--port", "9000"]
