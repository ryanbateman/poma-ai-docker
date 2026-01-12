import weaviate
import os
from weaviate.classes.query import QueryReference

def main():
    print("Connecting to Weaviate...")
    # Connection logic matches docker-compose setup
    client = weaviate.connect_to_custom(
        http_host="weaviate",
        http_port=8080,
        http_secure=False,
        grpc_host="weaviate",
        grpc_port=50051,
        grpc_secure=False,
    )

    try:
        # Get Collections
        chunk_col = client.collections.get("PomaChunk")
        chunkset_col = client.collections.get("PomaChunkset")

        # 1. Output Stats
        # Use aggregate to get total counts cheaply
        n_chunks = chunk_col.aggregate.over_all(total_count=True).total_count
        n_chunksets = chunkset_col.aggregate.over_all(total_count=True).total_count
        
        print(f"\n=== Database Statistics ===")
        print(f"Collection: PomaChunk    | Count: {n_chunks}")
        print(f"Collection: PomaChunkset | Count: {n_chunksets}")

        # 2. Random Chunk Example
        print(f"\n=== Example Chunk ===")
        # Fetch 1 random object (Weaviate's default list order is uuid-based/arbitrary enough for this)
        response_c = chunk_col.query.fetch_objects(
            limit=1,
            return_references=[QueryReference(link_on="inChunkset")]
        )
        
        if response_c.objects:
            obj = response_c.objects[0]
            content = obj.properties.get('content', '')
            
            # Inspect References
            refs = obj.references.get("inChunkset")
            ref_count = len(refs.objects) if refs else 0
            
            print(f"UUID:            {obj.uuid}")
            print(f"Content (start): {content[:100].replace(chr(10), ' ')}...") # escape newlines
            print(f"Cross-Refs:      {ref_count} (Parent Chunksets)")
            if ref_count > 0:
                print(f" -> Parent UUID: {refs.objects[0].uuid}")
        else:
            print("No chunks found.")

        # 3. Random Chunkset Example
        print(f"\n=== Example Chunkset ===")
        response_cs = chunkset_col.query.fetch_objects(
            limit=1,
            return_references=[QueryReference(link_on="hasChunks")]
        )
        
        if response_cs.objects:
            obj = response_cs.objects[0]
            content = obj.properties.get('content', '')
            
            # Inspect References
            refs = obj.references.get("hasChunks")
            ref_count = len(refs.objects) if refs else 0
            
            print(f"UUID:            {obj.uuid}")
            print(f"Content (start): {content[:100].replace(chr(10), ' ')}...")
            print(f"Cross-Refs:      {ref_count} (Child Chunks)")
            if ref_count > 0:
                # Just show first few
                ids = [str(o.uuid) for o in refs.objects[:3]]
                print(f" -> Child UUIDs: {', '.join(ids)} {'...' if ref_count > 3 else ''}")
        else:
            print("No chunksets found.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        client.close()
        print("\nConnection closed.")

if __name__ == "__main__":
    main()
