#!/bin/bash

# Milk Booth Application Deployment Script
# Deploy the application to Kubernetes after kubeadm is installed

set -e

echo "=========================================="
echo "Milk Booth Kubernetes Deployment"
echo "=========================================="
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "✗ kubectl not found. Install Kubernetes first using install-kubernetes.sh"
    exit 1
fi

# Get project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if k8s folder exists
if [ ! -d "$PROJECT_DIR/k8s" ]; then
    echo "✗ k8s folder not found in $PROJECT_DIR"
    exit 1
fi

echo "Project directory: $PROJECT_DIR"
echo ""

# Step 1: Build Docker image
echo "Step 1: Building Docker image..."
docker build -t milkbooth:latest "$PROJECT_DIR"

if [ $? -eq 0 ]; then
    echo "✓ Docker image built successfully"
else
    echo "✗ Docker build failed"
    exit 1
fi
echo ""

# Step 2: Update secrets (optional)
echo "Step 2: Reviewing k8s/secret.yaml..."
echo ""
echo "⚠️  IMPORTANT: Update the following in k8s/secret.yaml before proceeding:"
echo "   - SECRET_KEY: Use a strong random secret (change from 'replace-with-secure-secret')"
echo "   - DATABASE_URL: Update password (change from 'milkpass')"
echo "   - POSTGRES_PASSWORD: Update password (change from 'milkpass')"
echo ""
read -p "Press Enter to continue, or Ctrl+C to edit k8s/secret.yaml first..."
echo ""

# Step 3: Deploy resources
echo "Step 3: Deploying Kubernetes resources..."
echo ""

echo "  Deploying secrets..."
kubectl apply -f "$PROJECT_DIR/k8s/secret.yaml"

echo "  Deploying PostgreSQL PVC..."
kubectl apply -f "$PROJECT_DIR/k8s/postgres-pvc.yaml"

echo "  Deploying PostgreSQL..."
kubectl apply -f "$PROJECT_DIR/k8s/postgres-deployment.yaml"
kubectl apply -f "$PROJECT_DIR/k8s/postgres-service.yaml"

echo "  Waiting for PostgreSQL to be ready..."
kubectl rollout status deployment/milkbooth-postgres --timeout=5m

echo "  Deploying Application..."
kubectl apply -f "$PROJECT_DIR/k8s/app-deployment.yaml"
kubectl apply -f "$PROJECT_DIR/k8s/app-service.yaml"

echo "  Waiting for Application to be ready..."
kubectl rollout status deployment/milkbooth-app --timeout=5m

echo "✓ Deployment completed"
echo ""

# Step 4: Show status
echo "=========================================="
echo "Deployment Status"
echo "=========================================="
echo ""
echo "Pods:"
kubectl get pods
echo ""
echo "Services:"
kubectl get svc
echo ""
echo "Deployments:"
kubectl get deployments
echo ""

# Check if all pods are running
RUNNING_PODS=$(kubectl get pods --no-headers | grep -c "Running" || true)
TOTAL_PODS=$(kubectl get pods --no-headers | wc -l)

echo "Pod Status: $RUNNING_PODS/$TOTAL_PODS running"
echo ""

if [ "$RUNNING_PODS" -eq "$TOTAL_PODS" ]; then
    echo "✓ All pods are running!"
else
    echo "⚠️  Some pods are still starting. Check with: kubectl get pods"
    echo "   To view logs: kubectl logs <pod-name>"
fi

echo ""
echo "=========================================="
echo "Access Your Application"
echo "=========================================="
echo ""
echo "Run this command to port-forward:"
echo "  kubectl port-forward svc/milkbooth 8080:80"
echo ""
echo "Then open: http://localhost:8080"
echo ""
echo "Default credentials:"
echo "  Username: admin"
echo "  Password: admin123"
echo ""
echo "=========================================="
