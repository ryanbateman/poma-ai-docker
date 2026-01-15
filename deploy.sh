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
echo "[1/5] Checking Google Cloud Project..."
CURRENT_PROJECT=$(gcloud config get-value project)
echo "Current Project: $CURRENT_PROJECT"
read -p "Proceed with this project? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
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
