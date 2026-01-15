import os
import pathlib
import weaviate
import weaviate.classes as wvc
from weaviate.classes.query import QueryReference
from poma import Poma
from langchain_community.llms import Ollama
from langchain_ollama import OllamaLLM
from langchain_google_vertexai import VertexAI

# Shared Configuration
POMA_API_KEY = os.getenv("POMA_API_KEY")

def get_weaviate_client():
    # Helper to get client (matches docker-compose networking)
    return weaviate.connect_to_custom(
        http_host="weaviate",
        http_port=8080,
        http_secure=False,
        grpc_host="weaviate",
        grpc_port=50051,
        grpc_secure=False,
    )

def ensure_schema(client):
    # Idempotent schema creation
    if not client.collections.exists("PomaChunk"):
        client.collections.create(
            name="PomaChunk",
            properties=[
                wvc.config.Property(name="content", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="source", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="chunk_index", data_type=wvc.config.DataType.INT),
            ],
            references=[
                wvc.config.ReferenceProperty(name="inChunkset", target_collection="PomaChunkset")
            ]
        )
        
    if not client.collections.exists("PomaChunkset"):
        client.collections.create(
            name="PomaChunkset",
            properties=[
                wvc.config.Property(name="content", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="source", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="chunkset_index", data_type=wvc.config.DataType.INT),
            ],
            references=[
                wvc.config.ReferenceProperty(name="hasChunks", target_collection="PomaChunk")
            ]
        )

def ingest_document(file_path: pathlib.Path):
    """
    Ingests a file using Poma SDK and stores results in Weaviate.
    """
    client = get_weaviate_client()
    poma_client = Poma(api_key=POMA_API_KEY)
    
    try:
        ensure_schema(client)
        
        # 1. Poma Chunking
        print(f"Starting chunking for {file_path.name}...")
        job = poma_client.start_chunk_file(file_path)
        job_id = job.get('job_id') if isinstance(job, dict) else getattr(job, 'job_id', str(job))
        
        # Poll
        result = poma_client.get_chunk_result(
            job_id, 
            show_progress=False, # No progress bar in API
            poll_interval=2.0
        )
        
        chunks_data = result.get('chunks', [])
        chunksets_data = result.get('chunksets', [])
        
        chunk_col = client.collections.get("PomaChunk")
        chunkset_col = client.collections.get("PomaChunkset")
        
        chunk_uuid_map = {}
        chunkset_uuid_map = {}
        
        # 2. Store Chunks
        with chunk_col.batch.dynamic() as batch:
            for chunk in chunks_data:
                c_idx = chunk.get('chunk_index')
                content = chunk.get('content', '')
                source = chunk.get('file_id', file_path.name)
                
                c_uuid = weaviate.util.generate_uuid5(f"{job_id}_chunk_{c_idx}")
                chunk_uuid_map[c_idx] = c_uuid
                
                batch.add_object(
                    properties={"content": content, "source": source, "chunk_index": c_idx},
                    uuid=c_uuid
                )

        # 3. Store Chunksets
        with chunkset_col.batch.dynamic() as batch:
            for cset in chunksets_data:
                cs_idx = cset.get('chunkset_index')
                content = cset.get('contents', '')
                source = cset.get('file_id', file_path.name)
                
                cs_uuid = weaviate.util.generate_uuid5(f"{job_id}_chunkset_{cs_idx}")
                chunkset_uuid_map[cs_idx] = cs_uuid
                
                batch.add_object(
                    properties={"content": content, "source": source, "chunkset_index": cs_idx},
                    uuid=cs_uuid
                )

        # 4. Link
        for cset in chunksets_data:
            cs_idx = cset.get('chunkset_index')
            cs_uuid = chunkset_uuid_map.get(cs_idx)
            child_indices = cset.get('chunks', [])
            
            for c_idx in child_indices:
                c_uuid = chunk_uuid_map.get(c_idx)
                if cs_uuid and c_uuid:
                    chunk_col.data.reference_add(from_uuid=c_uuid, from_property="inChunkset", to=cs_uuid)
                    chunkset_col.data.reference_add(from_uuid=cs_uuid, from_property="hasChunks", to=c_uuid)
                    
        return {
            "status": "success", 
            "job_id": job_id,
            "chunks": len(chunks_data), 
            "chunksets": len(chunksets_data)
        }
        
    finally:
        client.close()
        poma_client.close()

def query_rag(query: str, model_provider: str = "ollama"):
    """
    Retrieves chunksets, makes a Poma Cheatsheet, and queries LLM.
    """
    client = get_weaviate_client()
    poma_client = Poma(api_key=POMA_API_KEY)
    
    try:
        chunkset_col = client.collections.get("PomaChunkset")
        chunk_col = client.collections.get("PomaChunk")
        
        # 1. Retrieval
        response = chunkset_col.query.bm25(
            query=query, 
            limit=3,
            return_properties=["content", "source", "chunkset_index"]
        )
        
        relevant_sets = []
        file_ids = set()
        
        for obj in response.objects:
            cset_dict = {
                "chunkset_index": obj.properties.get("chunkset_index"),
                "file_id": obj.properties.get("source"),
                "content": obj.properties.get("content"), 
                "depth": 0,
                "chunks": [] 
            }
            
            obj_with_refs = chunkset_col.query.fetch_object_by_id(
                obj.uuid,
                return_references=[QueryReference(link_on="hasChunks", return_properties=["chunk_index"])]
            )
            
            if obj_with_refs and obj_with_refs.references.get("hasChunks"):
                linked_chunks = obj_with_refs.references["hasChunks"].objects
                cset_dict["chunks"] = [c.properties["chunk_index"] for c in linked_chunks]
                
            relevant_sets.append(cset_dict)
            file_ids.add(obj.properties['source'])
            
        if not relevant_sets:
            return "No relevant context found."

        # 2. Fetch All Chunks
        all_chunks = []
        for fid in file_ids:
            resp = chunk_col.query.fetch_objects(
                filters=wvc.query.Filter.by_property("source").equal(fid),
                limit=10000, 
                return_properties=["chunk_index", "content", "source"]
            )
            for o in resp.objects:
                all_chunks.append({
                    "chunk_index": o.properties["chunk_index"],
                    "content": o.properties["content"],
                    "file_id": o.properties["source"],
                    "depth": 0
                })
                
        # 3. Generate Cheatsheet
        cheatsheets = poma_client.create_cheatsheets(relevant_sets, all_chunks)
        full_context = "\n\n".join([s.get('content', '') for s in cheatsheets])
        
        # 4. Inference
        prompt = f"Context:\n{full_context}\n\nQuestion: {query}\nAnswer:"
        
        if model_provider == "gemini":
            try:
                # Use default credentials from environment
                llm = VertexAI(model_name="gemini-1.5-flash")
                return llm.invoke(prompt)
            except Exception as e:
                return f"Error initializing Gemini: {e}"
        else:
            # Fallback to Ollama
            llm = OllamaLLM(model="gemma3:4b", base_url="http://host.docker.internal:11434")
            return llm.invoke(prompt)

    finally:
        client.close()
        poma_client.close()

def get_db_stats():
    client = get_weaviate_client()
    try:
        chunk_col = client.collections.get("PomaChunk")
        chunkset_col = client.collections.get("PomaChunkset")
        
        n_chunks = chunk_col.aggregate.over_all(total_count=True).total_count
        n_chunksets = chunkset_col.aggregate.over_all(total_count=True).total_count
        return {"chunk_count": n_chunks, "chunkset_count": n_chunksets}
    finally:
        client.close()
