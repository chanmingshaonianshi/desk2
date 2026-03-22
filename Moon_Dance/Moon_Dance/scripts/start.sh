#!/bin/bash

# ================= Configuration =================
# Docker Image Name
IMAGE_NAME="moon_dance_simulator"
# Number of Containers to Start
NUM_CONTAINERS=30
# ===============================================

echo "======================================"
echo "      Moon Dance Simulator Launcher    "
echo "======================================"

# 1. Build Docker Image
echo "[Step 1/2] Building Docker Image: $IMAGE_NAME..."
# Check if Dockerfile exists
if [ ! -f "Dockerfile" ]; then
    echo "Error: Dockerfile not found in current directory!"
    exit 1
fi

docker build -t $IMAGE_NAME .

if [ $? -ne 0 ]; then
    echo "Build failed, please check error logs."
    exit 1
fi
echo "Image built successfully!"

# 2. Batch Start Containers
echo "[Step 2/2] Starting $NUM_CONTAINERS container instances..."

for i in $(seq 1 $NUM_CONTAINERS); do
    # Container Name Format: simulator-1, simulator-2...
    CONTAINER_NAME="simulator-$i"
    
    # Check for existing container (running or stopped)
    if [ "$(docker ps -aq -f name=^/${CONTAINER_NAME}$)" ]; then
        echo "  - Found old container $CONTAINER_NAME, removing..."
        docker rm -f $CONTAINER_NAME > /dev/null
    fi
    
    # Start new container
    # -d: Run in background
    # --restart unless-stopped: Auto-restart on crash
    # -v $(pwd)/data/container_$i:/app/data: Mount data volume for persistence
    echo "  - Starting: $CONTAINER_NAME (Data Dir: ./data/container_$i)"
    
    # Create data directory for this container
    mkdir -p "data/container_$i"
    
    docker run -itd \
        --name $CONTAINER_NAME \
        --restart unless-stopped \
        -v "$(pwd)/data/container_$i:/app/data" \
        $IMAGE_NAME > /dev/null
done

echo "======================================"
echo "All containers started!"
echo "Common Commands:"
echo "  Check status:    docker ps"
echo "  Check logs:      docker logs -f simulator-1"
echo "  Stop all:        docker stop \$(docker ps -q --filter name=simulator-)"
echo "======================================"
