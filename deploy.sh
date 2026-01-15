#!/bin/bash

# Configuration
ZONE="europe-west1-b"
INSTANCE_NAME="poma-rag-framework"
MACHINE_TYPE="e2-standard-4"
IMAGE_FAMILY="ubuntu-2204-lts"
IMAGE_PROJECT="ubuntu-os-cloud"
TAGS="http-server,https-server"

echo "=== Poma Cloud Framework Deployment ==="
echo "This script will:"
echo "1. Create a Google Compute Engine instance (${INSTANCE_NAME})"
echo "2. Install Docker & Docker Compose"
echo "3. Deploy the Poma RAG stack"
echo "4. Expose the API on port 8081"
echo "---------------------------------------"

# 1. Check for gcloud
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed."
    exit 1
fi

# 2. Authenticate/Config (Start)
TARGET_PROJECT=$1

if [ -n "$TARGET_PROJECT" ]; then
    echo "Using provided project ID: $TARGET_PROJECT"
    # Verify project exists/access
    if ! gcloud projects describe $TARGET_PROJECT &> /dev/null; then
        echo "Error: Project '$TARGET_PROJECT' not found or not accessible."
        exit 1
    fi
    # Set project for this session/command context if needed, or just warn user
    # Ideally we just ensure commands use it, but gcloud config set is global.
    # We will verify it matches current or ask to switch?
    # Simpler: Just rely on gcloud config, but if arg provided, check mismatch.
    
    CURRENT=$(gcloud config get-value project)
    if [ "$CURRENT" != "$TARGET_PROJECT" ]; then
        echo "Switching active gcloud project to $TARGET_PROJECT..."
        gcloud config set project $TARGET_PROJECT
    fi
fi

echo "[1/5] Checking Google Cloud Project..."
CURRENT_PROJECT=$(gcloud config get-value project)
echo "Current Project: $CURRENT_PROJECT"

if [ -z "$CURRENT_PROJECT" ]; then
    echo "Error: No project selected in gcloud config and no argument provided."
    echo "Usage: ./deploy.sh [PROJECT_ID]"
    exit 1
fi

if [ -z "$TARGET_PROJECT" ]; then
    read -p "Proceed with this project? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 3. Create Firewall Rules (8081 for API, 8080 for Weaviate)
echo "[2/5] Configuring Firewall..."
gcloud compute firewall-rules create allow-poma-api \
    --allow tcp:8081 \
    --description="Allow incoming traffic to Poma API" \
    --direction=INGRESS \
    --target-tags=poma-api \
    --quiet || echo "Firewall rule likely already exists, skipping."

# 4. Create Instance
echo "[3/5] Creating GCE Instance..."
gcloud compute instances create $INSTANCE_NAME \
    --zone=$ZONE \
    --machine-type=$MACHINE_TYPE \
    --image-family=$IMAGE_FAMILY \
    --image-project=$IMAGE_PROJECT \
    --tags=poma-api,http-server \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --quiet || echo "Instance likely exists, continuing..."

# 5. Provisioning & Deployment
echo "[4/5] Provisioning Instance (Docker Install & Stack Deploy)..."
echo "Waiting for SSH to be ready..."
sleep 20

gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command '
    # Update & Install Docker
    sudo apt-get update
    sudo apt-get install -y docker.io docker-compose
    sudo usermod -aG docker $USER

    # Create App Directory
    mkdir -p ~/poma-rag
' --quiet

# Copy files
echo "Copying project files..."
gcloud compute scp --zone=$ZONE \
    docker-compose.yml \
    Dockerfile \
    requirements.txt \
    main.py \
    rag_service.py \
    cheatsheet_test_doc.txt \
    .env \
    $INSTANCE_NAME:~/poma-rag/ --quiet

# Start Stack
echo "Starting Stack..."
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command '
    cd ~/poma-rag
    # Ensure env file exists
    touch .env
    
    # Start
    sudo docker-compose down
    sudo docker-compose up -d --build
' --quiet

# 6. Finish
EXTERNAL_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

# Save deployment info
cat > deployment_info.json <<EOF
{
  "instance_name": "$INSTANCE_NAME",
  "zone": "$ZONE",
  "external_ip": "$EXTERNAL_IP",
  "api_endpoint": "http://$EXTERNAL_IP:8081",
  "weaviate_endpoint": "http://$EXTERNAL_IP:8080"
}
EOF

echo "Deployment info saved to deployment_info.json"

echo "---------------------------------------"
echo "Deployment Complete!"
echo "API Endpoint: http://${EXTERNAL_IP}:8081"
echo "Weaviate:     http://${EXTERNAL_IP}:8080"
echo ""
echo "Try it:"
echo "curl http://${EXTERNAL_IP}:8081/"
echo "---------------------------------------"
