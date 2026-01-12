import os
import sys

def main():
    print("Starting Poma AI connection test...")
    
    # Test Import
    try:
        import poma
        print("SUCCESS: Poma AI library imported successfully.")
    except ImportError as e:
        print(f"FAILURE: Error importing poma: {e}")
        sys.exit(1)

    # Test API Key presence
    api_key = os.environ.get("POMA_API_KEY")
    if not api_key:
        print("FAILURE: POMA_API_KEY not found in environment variables.")
        sys.exit(1)
    else:
        # Print a masked version for verification
        masked_key = f"{api_key[:10]}...{api_key[-5:]}" if len(api_key) > 15 else "***"
        print(f"SUCCESS: POMA_API_KEY found: {masked_key}")

if __name__ == "__main__":
    main()
