# Poma Cloud RAG Framework

A deployable, API-driven framework for building Retrieval-Augmented Generation (RAG) pipelines using [Poma AI](https://poma.ai/).

This project transforms the Poma SDK into a **Cloud-Ready Service** that integrates:
*   **Poma AI**: For intelligent document chunking and "Cheatsheet" generation.
*   **Weaviate**: As the vector database for storing Chunksets.
*   **Google Gemini (Vertex AI)**: For high-quality, long-context inference.
*   **FastAPI**: Providing a robust REST API for ingestion and querying.

## Features

*   **Cloud Deployment**: One-click provisioning to Google Compute Engine via `deploy.sh`.
*   **Hybrid RAG**: Combines Poma's hierarchical `Chunkset` retrieval with Gemini's reasoning.
*   **REST API**: Simple endpoints for `ingest`, `query`, and `stats`.
*   **Helper Tools**: Python scripts for easy document uploading and monitoring.

---

## 🚀 Cloud Deployment

The included scripts allow you to deploy the entire stack (App + Weaviate) to Google Cloud Platform (GCE) in minutes.

### 1. Prerequisites
*   **Google Cloud Account** & Project.
*   **[gcloud CLI](https://cloud.google.com/sdk/docs/install)** installed and authenticated.
*   **Poma API Key**: Get one at [poma.ai](https://poma.ai).

### 2. Deploy
Run the deployment script. This will provision a VM, configure firewalls, and launch the stack.

```bash
./deploy.sh
```
*Follow the prompts. By default, this deploys to `europe-west1-b`.*

### 3. Verification
Once complete, the script generates a `deployment_info.json` file with your server's details:

```json
{
  "instance_name": "poma-rag-framework",
  "external_ip": "34.123.45.67",
  "api_endpoint": "http://34.123.45.67:8081",
  ...
}
```

---

## 📖 Usage Guide

You can interact with the deployed API using the provided helper script or standard HTTP tools.

### 1. Upload & Ingest Documents
Use the `upload_tool.py` script to upload a file (`.pdf`, `.txt`, etc.). It automatically finds your server using `deployment_info.json` and tracks the Poma indexing job.

```bash
# Usage: python upload_tool.py <path_to_file>
python upload_tool.py documents/whitepaper.pdf
```
*Output will show the Poma Job ID and the number of Chunks/Chunksets created.*

### 2. Query the RAG Pipeline
Ask questions against your uploaded data using `query_tool.py`. It reads your configuration and handles the API request for you.

**Cloud Usage (Gemini via Vertex AI):**
```bash
# Explicitly use the 'gemini' provider
python query_tool.py "What are the key conclusions?" --provider gemini
```

**Local Usage (Ollama):**
```bash
# Defaults to 'ollama' provider
python query_tool.py "What is Poma?" --config local_test_config.json
```

**Manual (Curl):**
If you prefer raw requests:
```bash
export API_URL="http://34.123.45.67:8081"
curl -X POST "$API_URL/query" \
     -H "Content-Type: application/json" \
     -d '{"query": "...", "model_provider": "gemini"}'
```

### 3. Check Stats
See how many chunksets are currently indexed.
```bash
python stats_tool.py
```
*Output displays the total count of Chunks and Chunksets in Weaviate.*

---

## 🛠️ Local Development

You can still run the stack locally using Docker Compose for development and testing.

1.  **Configure**: Create a `.env` file with your `POMA_API_KEY`.
2.  **Start**:
    ```bash
    docker-compose up -d --build
    ```
3.  **Local Testing**:
    The API will be available at `http://localhost:8081`. You can use `upload_tool.py` locally by creating a compatible config:
    ```bash
    # Run against localhost
    python upload_tool.py test.txt --config local_test_config.json
    ```

## Acknowledgements
This project was largely generated through **Antigravity** with the assistance of AI coding. The code was reviewed and validated by **Ryan Bateman**.
