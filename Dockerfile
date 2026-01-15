FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose ports
EXPOSE 8081

# Force langchain-google-genai to use Vertex AI backend (for Service Account auth)
ENV GOOGLE_GENAI_USE_VERTEXAI=True

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
