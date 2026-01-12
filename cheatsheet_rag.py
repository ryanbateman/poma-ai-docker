import weaviate
import sys
import os
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from poma import Poma

# Configuration from environment or defaults
# Note: POMA_API_KEY is expected in environment (passed via docker-compose)
POMA_API_KEY = os.getenv("POMA_API_KEY")

class CheatsheetRetriever:
    def __init__(self, weaviate_client, poma_client):
        self.w_client = weaviate_client
        self.p_client = poma_client
        self.chunkset_col = weaviate_client.collections.get("PomaChunkset")
        self.chunk_col = weaviate_client.collections.get("PomaChunk")

    def get_cheatsheet_context(self, query):
        # Step 1: Vector Search for Chunksets
        print(f"Searching Weaviate for: '{query}'")
        response = self.chunkset_col.query.bm25(
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
                "depth": 0, # Added default
                "chunks": [] 
            }
            
            # Fetch linked chunks to get their IDs (indices)
            obj_with_refs = self.chunkset_col.query.fetch_object_by_id(
                obj.uuid,
                return_references=[
                    weaviate.classes.query.QueryReference(link_on="hasChunks", return_properties=["chunk_index"])
                ]
            )
            
            if obj_with_refs and obj_with_refs.references.get("hasChunks"):
                linked_chunks = obj_with_refs.references["hasChunks"].objects
                cset_dict["chunks"] = [c.properties["chunk_index"] for c in linked_chunks]
                
            relevant_sets.append(cset_dict)
            file_ids.add(obj.properties['source'])
            
        print(f"Found {len(relevant_sets)} relevant chunksets from {len(file_ids)} files.")
        
        if not relevant_sets:
            return ""

        # Step 2: Fetch All Chunks for these files
        all_chunks = []
        for fid in file_ids:
            print(f"Fetching all chunks for file: {fid}")
            # Fetch all chunks where source == fid
            resp = self.chunk_col.query.fetch_objects(
                filters=weaviate.classes.query.Filter.by_property("source").equal(fid),
                limit=10000, 
                return_properties=["chunk_index", "content", "source"]
            )
            
            for o in resp.objects:
                all_chunks.append({
                    "chunk_index": o.properties["chunk_index"],
                    "content": o.properties["content"],
                    "file_id": o.properties["source"],
                    "depth": 0 # Added default
                })
            
        # Step 3: Generate
        print("Generating Poma Cheatsheet...")
        try:
            # Poma SDK call
            cheatsheets = self.p_client.create_cheatsheets(relevant_sets, all_chunks)
            
            full_context_parts = []
            for sheet in cheatsheets:
                full_context_parts.append(sheet.get('content', ''))
                
            full_context = "\n\n".join(full_context_parts)
            return full_context
            
        except Exception as e:
            print(f"Error generating cheatsheet: {e}")
            return ""

def main():
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "Why does Ahab chase the whale?"

    print("Connecting to Weaviate...")
    client = weaviate.connect_to_custom(
        http_host="weaviate",
        http_port=8080,
        http_secure=False,
        grpc_host="weaviate",
        grpc_port=50051,
        grpc_secure=False,
    )
    
    try:
        poma_client = Poma(api_key=POMA_API_KEY)
        
        # Initialize LLM
        # Using host.docker.internal to access host machine's Ollama
        llm = OllamaLLM(
            model="gemma3:4b", 
            base_url="http://host.docker.internal:11434"
        )
        
        retriever = CheatsheetRetriever(client, poma_client)
        
        # Execute Flow
        context = retriever.get_cheatsheet_context(query)
        
        if not context:
            print("No context generated. Exiting.")
            return

        print("\n--- Cheatsheet Context ---")
        print(context[:500] + "..." if len(context) > 500 else context)
        print("--------------------------\n")

        prompt = f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"
        
        print(f"Querying Ollama (gemma3:4b)...")
        # llm.invoke might fail if Ollama is unreachable
        try:
            response = llm.invoke(prompt)
            print("\n=== LLM Response ===")
            print(response)
        except Exception as e:
            print(f"\nError calling Ollama: {e}") 
            print("Ensure Ollama is running on the host and 'gemma3:4b' is pulled.")
        
    finally:
        client.close()
        if 'poma_client' in locals() and hasattr(poma_client, 'close'):
            poma_client.close()
        
        # Attempt to clean up LLM resources (LangChain specific)
        if 'llm' in locals():
            # Check for client session in LangChain Ollama integration
            if hasattr(llm, 'client') and hasattr(llm.client, 'close'):
                try:
                    llm.client.close()
                except:
                    pass
            elif hasattr(llm, 'http_client') and hasattr(llm.http_client, 'close'):
                 try:
                    llm.http_client.close()
                 except:
                    pass

import warnings
# Suppress ResourceWarning for unclosed sockets at exit if libraries don't clean up perfectly
warnings.simplefilter("ignore", ResourceWarning)

if __name__ == "__main__":
    main()
