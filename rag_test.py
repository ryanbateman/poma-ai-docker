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
    # Clean up existing collections
    if client.collections.exists("PomaChunk"):
        client.collections.delete("PomaChunk")
    if client.collections.exists("PomaChunkset"):
        client.collections.delete("PomaChunkset")
        
    client.collections.delete("PomaChunk") 
    client.collections.delete("PomaChunkset") # Ensure deleted

    print("Creating Schemas...")
    # Define Chunkset first (target of Chunk)
    chunkset_collection = client.collections.create(
        name="PomaChunkset",
        properties=[
            weaviate.classes.config.Property(name="content", data_type=weaviate.classes.config.DataType.TEXT),
            weaviate.classes.config.Property(name="source", data_type=weaviate.classes.config.DataType.TEXT),
        ]
    )

    chunk_collection = client.collections.create(
        name="PomaChunk",
        properties=[
            weaviate.classes.config.Property(name="content", data_type=weaviate.classes.config.DataType.TEXT),
            weaviate.classes.config.Property(name="source", data_type=weaviate.classes.config.DataType.TEXT),
        ],
        references=[
            weaviate.classes.config.ReferenceProperty(
                name="inChunkset",
                target_collection="PomaChunkset"
            )
        ]
    )
    
    # Add 'hasChunks' reference to Chunkset
    chunkset_collection.config.add_reference(
        weaviate.classes.config.ReferenceProperty(
            name="hasChunks",
            target_collection="PomaChunk"
        )
    )
    print("Schemas created with cross-references.")

    # 1. Initialize Poma Client
    print("Initializing Poma Client...")
    poma_client = poma.Poma(api_key=POMA_API_KEY)

    # 2. Upload and Start Chunking
    test_file = "cheatsheet_test_doc.txt"
    print(f"Starting chunking job for {test_file}...")
    try:
        abs_path = os.path.abspath(test_file)
        print(f"Uploading file: {abs_path}")
        job = poma_client.start_chunk_file(pathlib.Path(abs_path))
        print(f"Job started: {job}")
        
        if isinstance(job, dict):
            job_id = job.get('job_id')
        else:
            job_id = getattr(job, 'job_id', str(job)) 
        print(f"Job ID: {job_id}")
    except Exception as e:
        print(f"Error starting chunk job: {e}")
        return

    # 3. Poll for Completion (Using SDK Polling)
    print("Polling for results using SDK...")
    try:
        # SDK handles polling loop
        result = poma_client.get_chunk_result(
            job_id, 
            show_progress=True,
            poll_interval=2.0 
        )
        print("Job completed.")
    except Exception as e:
        print(f"Error getting results: {e}")
        return

    if not result or 'chunks' not in result:
        print("Failed to get chunks from result.")
        return

    # 4. Parse & Store with Relationships
    print("Storing data in Weaviate...")
    chunks_data = result.get('chunks', [])
    chunksets_data = result.get('chunksets', [])
    
    chunk_uuid_map = {} # chunk_index -> UUID
    chunkset_uuid_map = {} # chunkset_index -> UUID
    
    # Store Chunks
    print(f" - Inserting {len(chunks_data)} chunks...")
    with chunk_collection.batch.dynamic() as batch:
        for chunk in chunks_data:
            c_idx = chunk.get('chunk_index')
            content = chunk.get('content', '')
            source = chunk.get('file_id', 'unknown')
            
            # Generate deterministic UUID or let Weaviate generate and capture return?
            # Batch add_object returns generated UUID if not provided? No, batch is async/fire-and-forget often.
            # Ideally we generate UUID to track it.
            import uuid
            c_uuid = weaviate.util.generate_uuid5(f"{job_id}_chunk_{c_idx}")
            chunk_uuid_map[c_idx] = c_uuid
            
            batch.add_object(
                properties={
                    "content": content,
                    "source": source,
                    "chunk_index": c_idx # Added
                },
                uuid=c_uuid
            )

    # Store Chunksets
    print(f" - Inserting {len(chunksets_data)} chunksets...")
    with chunkset_collection.batch.dynamic() as batch:
        for cset in chunksets_data:
            cs_idx = cset.get('chunkset_index')
            content = cset.get('contents', '') # Note: 'contents' plural in sample
            source = cset.get('file_id', 'unknown')
            
            cs_uuid = weaviate.util.generate_uuid5(f"{job_id}_chunkset_{cs_idx}")
            chunkset_uuid_map[cs_idx] = cs_uuid
            
            batch.add_object(
                properties={
                    "content": content,
                    "source": source,
                    "chunkset_index": cs_idx # Added
                },
                uuid=cs_uuid
            )
            
    # Check for errors in batch
    if len(client.batch.failed_objects) > 0:
        print(f"Errors during insertion: {client.batch.failed_objects}")
        
    # 5. Create Cross-References
    print(" - Linking Chunks and Chunksets...")
    # Iterate chunksets to find relationships
    for cset in chunksets_data:
        cs_idx = cset.get('chunkset_index')
        cs_uuid = chunkset_uuid_map.get(cs_idx)
        
        child_indices = cset.get('chunks', []) # list of chunk indices
        
        for c_idx in child_indices:
            c_uuid = chunk_uuid_map.get(c_idx)
            
            if cs_uuid and c_uuid:
                # Link Chunk -> Chunkset
                chunk_collection.data.reference_add(
                    from_uuid=c_uuid,
                    from_property="inChunkset",
                    to=cs_uuid
                )
                
                # Link Chunkset -> Chunk
                chunkset_collection.data.reference_add(
                    from_uuid=cs_uuid,
                    from_property="hasChunks",
                    to=c_uuid
                )

    print("Data stored and linked.")

    # 6. Query to Verify
    query_text = "Poma"
    print(f"Querying Chunks for '{query_text}'...")
    from weaviate.classes.query import QueryReference
    
    response_c = chunk_collection.query.bm25(
        query=query_text, 
        limit=1, 
        return_properties=["content", "chunk_index"], # Added chunk_index
        return_references=[
            QueryReference(link_on="inChunkset", return_properties=["content", "chunkset_index"]) # Added chunkset_index
        ]
    )
    
    for obj in response_c.objects:
        print(f" [Chunk] {obj.properties['content']}")
        # Check reference (requires extra query or generic object handling in v4? 
        # v4 returns references as objects if requested or checked)
        # Note: references might be returned differently depending on client setup.
        
    # ... (skipping to end of function)
    
    print(f"Querying Chunksets for '{query_text}'...")
    response_cs = chunkset_collection.query.bm25(query=query_text, limit=1)
    
    for obj in response_cs.objects:
        print(f" [Chunkset] {obj.properties['content'][:100]}...")

    # Close clients
    client.close()
    if hasattr(poma_client, 'close'):
        poma_client.close()

if __name__ == "__main__":
    main()
