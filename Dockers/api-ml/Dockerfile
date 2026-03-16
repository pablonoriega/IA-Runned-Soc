FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema (opcionales, pero útiles)
RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY app ./app
COPY soc_action_recommender_rf.joblib .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
