#!/bin/bash

# Quick-start script for building and pushing RunPod serverless worker
# Usage: ./build-and-push.sh your-dockerhub-username

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if username provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Docker Hub username required${NC}"
    echo "Usage: ./build-and-push.sh your-dockerhub-username"
    exit 1
fi

DOCKER_USERNAME=$1
IMAGE_NAME="model-store-worker"
IMAGE_TAG="latest"
FULL_IMAGE_NAME="${DOCKER_USERNAME}/${IMAGE_NAME}:${IMAGE_TAG}"

echo -e "${GREEN}=== Building RunPod Serverless Worker ===${NC}"
echo "Image: ${FULL_IMAGE_NAME}"
echo ""

# Check if required files exist
echo -e "${YELLOW}Checking required files...${NC}"
if [ ! -f "rp_handler.py" ]; then
    echo -e "${RED}Error: rp_handler.py not found${NC}"
    exit 1
fi
if [ ! -f "Dockerfile" ]; then
    echo -e "${RED}Error: Dockerfile not found${NC}"
    exit 1
fi
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: requirements.txt not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ All required files found${NC}"
echo ""

# Build the image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -t ${FULL_IMAGE_NAME} .
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Build successful${NC}"
else
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi
echo ""

# Check if user is logged in to Docker Hub
echo -e "${YELLOW}Checking Docker Hub login...${NC}"
if ! docker info | grep -q "Username: ${DOCKER_USERNAME}"; then
    echo -e "${YELLOW}Not logged in to Docker Hub. Logging in...${NC}"
    docker login
fi
echo ""

# Push the image
echo -e "${YELLOW}Pushing image to Docker Hub...${NC}"
docker push ${FULL_IMAGE_NAME}
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Push successful${NC}"
else
    echo -e "${RED}✗ Push failed${NC}"
    exit 1
fi
echo ""

echo -e "${GREEN}=== Complete! ===${NC}"
echo ""
echo "Your image is ready to use in RunPod:"
echo -e "${GREEN}${FULL_IMAGE_NAME}${NC}"
echo ""
echo "Next steps:"
echo "1. Go to https://www.runpod.io/console/serverless"
echo "2. Click 'New Endpoint'"
echo "3. Use this container image: ${FULL_IMAGE_NAME}"
echo "4. Don't forget to add your model to cache!"
echo "   - Click 'Cache Models'"
echo "   - Add: microsoft/Phi-3-mini-4k-instruct (or your model)"
echo ""
echo -e "${YELLOW}Pro tip:${NC} Set environment variable MODEL_NAME to use a different model"
