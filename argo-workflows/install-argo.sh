#!/bin/bash

# 🛠️ Argo Workflows Quick Installer
# This script installs Argo Workflows on your local Kubernetes cluster

set -e

# Configuration
NAMESPACE="argo"
ARGO_VERSION="v3.4.4"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛠️  Argo Workflows Quick Installer${NC}"
echo "===================================="

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl not found. Please install kubectl first.${NC}"
    echo -e "${YELLOW}💡 Install kubectl:${NC}"
    echo "   brew install kubectl  # macOS"
    echo "   # or visit: https://kubernetes.io/docs/tasks/tools/"
    exit 1
fi

# Check if we can connect to Kubernetes cluster
echo -e "${BLUE}🔍 Checking Kubernetes connection...${NC}"
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}❌ Cannot connect to Kubernetes cluster.${NC}"
    echo -e "${YELLOW}💡 Start a local cluster first:${NC}"
    echo "   # Docker Desktop: Enable Kubernetes in settings"
    echo "   # or minikube: minikube start"
    echo "   # or kind: kind create cluster"
    exit 1
fi
echo -e "${GREEN}✅ Connected to cluster: $(kubectl config current-context)${NC}"

# Check if Argo is already installed
if kubectl get namespace ${NAMESPACE} &> /dev/null && kubectl get deployment argo-server -n ${NAMESPACE} &> /dev/null; then
    echo -e "${YELLOW}⚠️  Argo Workflows already installed in namespace '${NAMESPACE}'${NC}"
    echo -e "${BLUE}💡 Run './open-argo-gui.sh' to access the UI${NC}"
    exit 0
fi

# Create Argo namespace
echo -e "${BLUE}📦 Creating Argo namespace...${NC}"
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
echo -e "${GREEN}✅ Namespace '${NAMESPACE}' ready${NC}"

# Install Argo Workflows
echo -e "${BLUE}⬇️  Installing Argo Workflows ${ARGO_VERSION}...${NC}"
kubectl apply -n ${NAMESPACE} -f "https://github.com/argoproj/argo-workflows/releases/download/${ARGO_VERSION}/install.yaml"

# Wait for installation to complete
echo -e "${BLUE}⏳ Waiting for Argo server to be ready (this may take a few minutes)...${NC}"
kubectl wait --for=condition=available deployment/argo-server -n ${NAMESPACE} --timeout=300s

# Check all pods are running
echo -e "${BLUE}🔍 Checking pod status...${NC}"
kubectl get pods -n ${NAMESPACE}

echo ""
echo -e "${GREEN}🎉 Argo Workflows installed successfully!${NC}"
echo -e "${BLUE}🚀 Next steps:${NC}"
echo "   1. Run: ./open-argo-gui.sh"
echo "   2. Or manually: kubectl -n argo port-forward deployment/argo-server 2746:2746"
echo "   3. Then open: https://localhost:2746"
echo ""
echo -e "${YELLOW}📝 Note: You may see certificate warnings in the browser - this is normal for local development${NC}" 