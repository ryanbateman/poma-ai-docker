import os
import weaviate
import json

# Poma SDK Integration Test
# This script demonstrates the full pipeline:
# 1. Connect to Weaviate
# 2. Ingest document via Poma SDK
# 3. Poll for results
# 4. Store structured chunks in Weaviate
# 5. Query results

WEAVIATE_URL = os.environ.get("WEAVIATE_URL", "http://localhost:8080")
POMA_API_KEY = os.environ.get("POMA_API_KEY")

import poma
import time
import pathlib
import inspect

def main():
    print("Inspecting Poma Class...")
    print(dir(poma.Poma))
    print(f"Signature: {inspect.signature(poma.Poma.start_chunk_file)}")
    
    # helper for v3/v4 client difference - attempting v3 style first or v4 generic
    client = weaviate.connect_to_custom(
        http_host="weaviate",
        http_port=8080,
        http_secure=False,
        grpc_host="weaviate",
        grpc_port=50051,
        grpc_secure=False,
    )

    # v4 Schema/Collection management
    if client.collections.exists("PomaChunk"):
        client.collections.delete("PomaChunk")
        
    collection = client.collections.create(
        name="PomaChunk",
        properties=[
            weaviate.classes.config.Property(name="content", data_type=weaviate.classes.config.DataType.TEXT),
            weaviate.classes.config.Property(name="source", data_type=weaviate.classes.config.DataType.TEXT),
        ]
    )
    print("Schema created.")

    # 1. Initialize Poma Client
    print("Initializing Poma Client...")
    poma_client = poma.Poma(api_key=POMA_API_KEY)

    # 2. Upload and Start Chunking
    print("Starting chunking job for test_doc.txt...")
    try:
        abs_path = os.path.abspath("test_doc.txt")
        print(f"Uploading file: {abs_path}")
        job = poma_client.start_chunk_file(pathlib.Path(abs_path))
        print(f"Job started: {job}")
        
        # Handle different potential return types (dict vs object)
        if isinstance(job, dict):
            job_id = job.get('job_id')
        else:
            job_id = getattr(job, 'job_id', str(job)) # Fallback if it returns just ID string
            
        print(f"Job ID: {job_id}")
    except Exception as e:
        print(f"Error starting chunk job: {e}")
        return

    # 3. Poll for Completion
    print("Polling for results...")
    result = None
    start_time = time.time()
    
    while True:
        if time.time() - start_time > 60:
            print("Timeout waiting for chunks.")
            return

        try:
            # get_chunk_result allows downloading the result
            status_res = poma_client.get_chunk_result(job_id)
            
            # Check for success (presence of 'chunks')
            if isinstance(status_res, dict) and 'chunks' in status_res:
                result = status_res
                print(f"Chunks received: {len(result['chunks'])}")
                break
            
            # If it returns a status dict (e.g. pending), print and wait
            # (Note: In observed behavior, it seems to block/download when ready or return the result directly)
            print("Waiting for chunks...")
            time.sleep(2)
        except Exception as e:
            print(f"Polling/Download info: {e}")
            # If 404 or similar, it might be pending. 
            time.sleep(2)

    if not result or 'chunks' not in result:
        print("Failed to get chunks.")
        return

    # 4. Parse Chunks & Store in Weaviate
    print("Storing chunks in Weaviate...")
    chunks_data = result['chunks']
    
    with collection.batch.dynamic() as batch:
        for chunk in chunks_data:
            content = chunk.get('content', '')
            # Use file_id or original filename as source
            source = chunk.get('file_id', 'unknown')
            
            # print(f" - Storing: {content[:30]}...")
            
            batch.add_object(
                properties={
                    "content": content,
                    "source": source
                }
            )
    print("Chunks stored.")

    # 5. Query
    query_text = "Poma"
    print(f"Querying for '{query_text}'...")
    
    response = collection.query.bm25(
        query=query_text,
        limit=2
    )
    
    print("Query Result:")
    for obj in response.objects:
        print(f" - {obj.properties['content']}")

if __name__ == "__main__":
    main()
