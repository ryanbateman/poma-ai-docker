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

def get_stats(api_base_url):
    url = f"{api_base_url}/stats"
    
    try:
        start_time = time.time()
        response = requests.get(url)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            chunk_count = data.get("chunk_count", 0)
            chunkset_count = data.get("chunkset_count", 0)
            
            print(f"\n=== Poma Cloud Stats ===")
            print(f"Endpoint:   {url}")
            print(f"Latency:    {duration*1000:.2f} ms")
            print("------------------------")
            print(f"Chunks:     {chunk_count}")
            print(f"Chunksets:  {chunkset_count}")
            print("========================")
        else:
            print(f"\n[FAILED] Server returned status code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"\n[ERROR] Could not connect to {url}.")
        print("Please check your internet connection and verify the server is running.")
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="View Poma Cloud Framework Stats")
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
            
    # Strip trailing slash if present
    api_endpoint = api_endpoint.rstrip("/")
    
    get_stats(api_endpoint)
