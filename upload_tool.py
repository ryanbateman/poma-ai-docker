import json
import requests
import sys
import os
import argparse
import time

def load_config(config_path="deployment_info.json"):
    if not os.path.exists(config_path):
        print(f"Error: Configuration file '{config_path}' not found.")
        print("Please run './deploy.sh' first to generate deployment details.")
        sys.exit(1)
        
    with open(config_path, "r") as f:
        return json.load(f)

def upload_document(file_path, api_base_url):
    url = f"{api_base_url}/ingest"
    file_name = os.path.basename(file_path)
    
    print(f"--- Poma Cloud Uploader ---")
    print(f"Target: {url}")
    print(f"File:   {file_name}")
    print("---------------------------")
    print(f"Uploading and processing... (This may take a moment)")
    
    start_time = time.time()
    
    try:
        with open(file_path, "rb") as f:
            files = {"file": f}
            # The API currently blocks while Poma processes the file.
            # A future improvement could be async polling, but for now we wait.
            response = requests.post(url, files=files)
            
        duration = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            details = data.get("details", {})
            print("\n[SUCCESS] Document Ingested!")
            print(f"Time Taken: {duration:.2f}s")
            print(f"Job ID:     {details.get('job_id', 'N/A')}")
            print(f"Chunks:     {details.get('chunks', 0)}")
            print(f"Chunksets:  {details.get('chunksets', 0)}")
            print(f"Server Status: {data.get('status')}")
        else:
            print(f"\n[FAILED] Server returned status code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"\n[ERROR] Could not connect to {url}.")
        print("Please check your internet connection and verify the server is running.")
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload documents to Poma Cloud Framework")
    parser.add_argument("file", help="Path to the document to upload")
    parser.add_argument("--config", default="deployment_info.json", help="Path to deployment info JSON")
    
    args = parser.parse_args()
    
    config = load_config(args.config)
    
    # Prefer API endpoint from config
    api_endpoint = config.get("api_endpoint")
    if not api_endpoint:
        # Fallback to external IP construction if full endpoint missing
        ip = config.get("external_ip")
        if ip:
            api_endpoint = f"http://{ip}:8081"
        else:
            print("Error: Invalid configuration file. Missing 'api_endpoint' or 'external_ip'.")
            sys.exit(1)
            
    # Stip trailing slash if present
    api_endpoint = api_endpoint.rstrip("/")
    
    upload_document(args.file, api_endpoint)
