# Poma AI Docker Environment

A fully containerized environment for testing and integrating [Poma AI](https://poma.ai/)—a tool for optimizing RAG pipelines through intelligent chunking and "Cheatsheet" generation.

This project demonstrates how to build an advanced Retrieval-Augmented Generation (RAG) pipeline that combines **Poma's SDK**, a **Weaviate** vector database, and a local **Ollama** LLM to deliver high-quality, context-aware answers.

## Project Goals

1.  **Dockerization**: Provide a consistent, isolated environment (`python:3.11-slim`) for Poma SDK development.
2.  **RAG Integration**: Demonstrate ingestion of documents into Weaviate using Poma's `Chunk` and `Chunkset` logic, utilizing bi-directional cross-references.
3.  **Cheatsheet RAG**: Implement a "Cheatsheet" pipeline where Poma dynamically generates high-density summaries (Cheatsheets) from retrieved context before passing them to an LLM.
4.  **Local LLM Support**: Integrate with a locally running Ollama instance (e.g., `gemma3:4b`) for privacy-focused inference.

## Key Components

### Scripts

*   **`rag_test.py`**: The primary ingestion script.
    *   Uploads a text file to Poma.
    *   Retrieves intelligent **Chunks** and **Chunksets**.
    *   Stores them in Weaviate with appropriate indices (`chunk_index`, `chunkset_index`).
    *   Links Chunks and Chunksets using Weaviate Cross-References (`hasChunks`, `inChunkset`).
*   **`cheatsheet_rag.py`**: The advanced retrieval & inference script.
    *   Takes a user query (e.g., "What does Poma do?").
    *   Performs a hybrid search in Weaviate for relevant **Chunksets**.
    *   Uses Poma's `create_cheatsheets` API to generate a concise summary tailored to the query.
    *   Sends this summary to a local **Ollama** LLM (via `host.docker.internal`) to generate the final answer.
*   **`debug_weaviate.py`**: A utility script to inspect database statistics (object counts) and verify cross-reference links between Chunks and Chunksets.

### Infrastructure

*   **`docker-compose.yml`**: Orchestrates two services:
    *   `app`: The Python application container (where scripts run).
    *   `weaviate`: The vector database instance (v1.27.0).
*   **`requirements.txt`**: Python dependencies including `poma`, `weaviate-client`, and `langchain-ollama`.

## Prerequisites

1.  **Docker Desktop** installed and running.
2.  **Poma API Key**: You need an API key from [Poma AI](https://poma.ai/).
3.  **Ollama**: Installed on your host machine with a model pulled (default configuration uses `gemma3:4b`, but is configurable).
    ```bash
    ollama pull gemma3:4b
    ```

## Setup & Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/ryanbateman/poma-ai-docker.git
    cd poma-ai-docker
    ```

2.  **Configure Environment**:
    Create a `.env` file in the root directory (copied from `.env.example`) and add your Poma API Key:
    ```bash
    cp .env.example .env
    ```
    *Edit `.env` and set `POMA_API_KEY=your_key_here`.*

3.  **Build and Start**:
    ```bash
    docker-compose up -d --build
    ```

## Usage Guide

Run all scripts inside the Docker container using `docker-compose exec`.

### 1. Ingest Data
First, populate the database. The default script uses `cheatsheet_test_doc.txt` (a small sample) for demonstration.

```bash
docker-compose exec app python rag_test.py
```
*Output: Confirms upload, job completion, and storage of Chunks/Chunksets in Weaviate.*

### 2. Verify Data (Optional)
Check that data was stored correctly:
```bash
docker-compose exec app python debug_weaviate.py
```

### 3. Run the Cheatsheet RAG Pipeline
Query the system. This triggers the full flow: **Retrieval -> Cheatsheet Generation -> Ollama Inference**.

```bash
docker-compose exec app python cheatsheet_rag.py "What is Poma designed to do?"
```

*Example Output:*
```text
Connecting to Weaviate...
Searching Weaviate for: 'What is Poma designed to do?'
Found 3 relevant chunksets...
Generating Poma Cheatsheet...

--- Cheatsheet Context ---
Poma AI is a tool specifically designed to optimize RAG pipelines...
--------------------------

Querying Ollama (gemma3:4b)...

=== LLM Response ===
Poma AI is designed to optimize RAG pipelines by utilizing intelligent chunking...
```

## Contributing
Feel free to open issues or submit pull requests to improve the integration examples.

## Acknowledgements
This project was generated largely through **Antigravity** with the assistance of AI coding. The code was reviewed and validated by **Ryan Bateman**.
