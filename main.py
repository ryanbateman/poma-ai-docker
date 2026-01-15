import os
import shutil
import pathlib
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import weaviate
from poma import Poma
from contextlib import asynccontextmanager

# Import refactored service
from rag_service import ingest_document, query_rag, get_db_stats

# --- Configuration ---
POMA_API_KEY = os.getenv("POMA_API_KEY")

# --- App Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure specific checks if needed
    print("FastAPI RAG Service Starting...")
    yield
    # Shutdown
    print("FastAPI RAG Service Stopping...")

app = FastAPI(title="Poma Cloud RAG", lifespan=lifespan)

# --- Pydantic Models ---
class QueryRequest(BaseModel):
    query: str
    model_provider: str = "ollama" # Default to ollama for now, switch to Gemini later

class StatsResponse(BaseModel):
    chunk_count: int
    chunkset_count: int

# --- Endpoints ---

@app.get("/")
def read_root():
    return {"status": "online", "service": "Poma RAG Framework"}

@app.post("/ingest")
async def ingest_file(file: UploadFile = File(...)):
    """
    Uploads a file, chunks it with Poma, and stores it in Weaviate.
    """
    # 1. Save file temporarily
    temp_dir = pathlib.Path("/tmp/uploads")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / file.filename
    
    try:
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. Trigger Ingestion via Service
        result = ingest_document(temp_path)
        
        return {"filename": file.filename, "status": "ingested_successfully", "details": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

@app.post("/query")
async def query_endpoint(request: QueryRequest):
    """
    Queries the RAG pipeline using Poma Cheatsheets + LLM.
    """
    try:
        answer = query_rag(request.query, request.model_provider)
        return {"query": request.query, "answer": answer, "provider": request.model_provider}
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats", response_model=StatsResponse)
def stats_endpoint():
    try:
        return get_db_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
