# Poma Cloud RAG Framework

A deployable, API-driven framework for building Retrieval-Augmented Generation (RAG) pipelines using [Poma AI](https://poma.ai/).

This project transforms the Poma SDK into a **Cloud-Ready Service** (for local or Cloud deployment) that integrates:
*   **Poma AI**: For intelligent document chunking and "Cheatsheet" generation.
*   **Weaviate**: As the vector database for storing Chunksets.
*   **Google Gemini (Vertex AI)**: For high-quality, long-context inference (using `langchain-google-genai`).
*   **FastAPI**: Providing a robust REST API for ingestion and querying.

## Features

*   **Cloud Deployment**: One-click provisioning to Google Compute Engine via `deploy.sh`.
*   **Hybrid RAG**: Combines Poma's hierarchical `Chunkset` retrieval with Gemini's reasoning.
*   **REST API**: Simple endpoints for `ingest`, `query`, and `stats`.
*   **Helper Tools**: Python scripts for easy document uploading and monitoring.

---

## Cloud Deployment

The included scripts allow you to deploy the entire stack (App + Weaviate) to Google Cloud Platform (GCE) in minutes.

### 1. Prerequisites
*   **Google Cloud Account** & Project.
*   **[gcloud CLI](https://cloud.google.com/sdk/docs/install)** installed and authenticated.
*   **Poma API Key**: Get one at [poma.ai](https://poma.ai).

### 2. Deploy
Run the deployment script. This will provision a VM, configure firewalls, and launch the stack.

```bash
# Deploy using your active gcloud config
./deploy.sh

# ... OR ... deploy to a specific project
./deploy.sh my-project-id
```

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

## Usage Guide

Interact with the deployed API using the provided python helper tools. These tools automatically read your `deployment_info.json` configuration.

### 1. Upload & Ingest Documents
Use the `upload_tool.py` script to upload a file (`.pdf`, `.txt`, etc.). It uploads the file to the API, tracking the Poma indexing job until completion.

```bash
# Usage: python upload_tool.py <path_to_file>
python upload_tool.py documents/whitepaper.pdf
```
*Output will show the Poma Job ID and the number of Chunks/Chunksets created.*

### 2. Query the RAG Pipeline
Ask questions against your uploaded data. You can choose between **Gemini** (Cloud) or **Ollama** (if running locally).

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

### 3. Check Stats
See how many chunksets are currently indexed.
```bash
python stats_tool.py
```

---

## Local Development

You can still run the stack locally using Docker Compose for development and testing.

1.  **Configure**: Create a `.env` file with your `POMA_API_KEY`.
2.  **Start**:
    ```bash
    docker-compose up -d --build
    ```
3.  **Local Testing**:
    The API will be available at `http://localhost:8081`. You can use the tools locally by creating a configuration file:
    ```bash
    # Create config
    echo '{"api_endpoint": "http://localhost:8081"}' > local_test_config.json
    
    # Run against localhost
    python upload_tool.py test.txt --config local_test_config.json
    ```

## Acknowledgements
This project was largely generated through **Antigravity** with the assistance of AI coding. The code was reviewed and validated by **Ryan Bateman**.
