#!/bin/bash

# 🚀 Quick Argo Workflows GUI Launcher
# This script sets up port forwarding and opens the Argo UI in your browser

set -e

# Source centralized versions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../versions.sh"

# Configuration
NAMESPACE="${ARGO_WORKFLOWS_NAMESPACE}"
PORT="${ARGO_WORKFLOWS_PORT}"
URL="http://localhost:${PORT}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Argo Workflows GUI Launcher${NC}"
echo "=================================="

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up...${NC}"
    # Kill any existing port-forward processes for this port
    pkill -f "kubectl.*port-forward.*${PORT}:${PORT}" 2>/dev/null || true
    echo -e "${GREEN}✅ Cleanup complete${NC}"
}

# Set trap for cleanup on script exit
trap cleanup EXIT INT TERM

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl not found. Please install kubectl first.${NC}"
    exit 1
fi

# Check if we can connect to Kubernetes cluster
echo -e "${BLUE}🔍 Checking Kubernetes connection...${NC}"
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}❌ Cannot connect to Kubernetes cluster.${NC}"
    echo -e "${YELLOW}💡 Try one of these:${NC}"
    echo "   • Start Docker Desktop with Kubernetes enabled"
    echo "   • Start minikube: minikube start"
    echo "   • Check your kubeconfig: kubectl config current-context"
    exit 1
fi
echo -e "${GREEN}✅ Connected to cluster: $(kubectl config current-context)${NC}"

# Check if Argo namespace exists
echo -e "${BLUE}🔍 Checking Argo Workflows installation...${NC}"
if ! kubectl get namespace ${NAMESPACE} &> /dev/null; then
    echo -e "${RED}❌ Argo namespace '${NAMESPACE}' not found.${NC}"
    echo -e "${YELLOW}💡 Install Argo Workflows first:${NC}"
    echo "   kubectl create namespace argo"
    echo "   kubectl apply -n argo -f https://github.com/argoproj/argo-workflows/releases/download/v3.4.4/install.yaml"
    exit 1
fi

# Check if argo-server deployment exists and is ready
if ! kubectl get deployment argo-server -n ${NAMESPACE} &> /dev/null; then
    echo -e "${RED}❌ Argo server deployment not found in namespace '${NAMESPACE}'.${NC}"
    echo -e "${YELLOW}💡 Install Argo Workflows first:${NC}"
    echo "   kubectl apply -n argo -f https://github.com/argoproj/argo-workflows/releases/download/v3.4.4/install.yaml"
    exit 1
fi

# Wait for argo-server to be ready
echo -e "${BLUE}⏳ Waiting for Argo server to be ready...${NC}"
if ! kubectl wait --for=condition=available deployment/argo-server -n ${NAMESPACE} --timeout=60s; then
    echo -e "${RED}❌ Argo server is not ready. Check the deployment:${NC}"
    echo "   kubectl get pods -n ${NAMESPACE}"
    echo "   kubectl logs -n ${NAMESPACE} deployment/argo-server"
    exit 1
fi
echo -e "${GREEN}✅ Argo server is ready${NC}"

# Kill any existing port-forward for this port
echo -e "${BLUE}🧹 Cleaning up existing port forwards...${NC}"
pkill -f "kubectl.*port-forward.*${PORT}:${PORT}" 2>/dev/null || true

# Start port forwarding in background
echo -e "${BLUE}🔗 Setting up port forwarding (${PORT}:${PORT})...${NC}"
kubectl -n ${NAMESPACE} port-forward deployment/argo-server ${PORT}:${PORT} > /dev/null 2>&1 &
PORT_FORWARD_PID=$!

# Wait a moment for port forwarding to establish
sleep 3

# Check if port forwarding is working
if ! curl -s ${URL} > /dev/null 2>&1; then
    echo -e "${RED}❌ Port forwarding failed to establish${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Port forwarding active (PID: ${PORT_FORWARD_PID})${NC}"
echo -e "${BLUE}🌐 Opening Argo UI in browser...${NC}"
echo -e "${YELLOW}📍 URL: ${URL}${NC}"

# Open browser (works on macOS, Linux, and Windows with WSL)
if command -v open &> /dev/null; then
    # macOS
    open "${URL}"
elif command -v xdg-open &> /dev/null; then
    # Linux
    xdg-open "${URL}"
elif command -v cmd.exe &> /dev/null; then
    # Windows WSL
    cmd.exe /c start "${URL}"
else
    echo -e "${YELLOW}⚠️  Could not auto-open browser. Please manually open: ${URL}${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Argo Workflows UI is now accessible!${NC}"
echo -e "${YELLOW}📝 Note: You may see a certificate warning - click 'Advanced' and 'Proceed'${NC}"
echo -e "${BLUE}ℹ️  Press Ctrl+C to stop the port forwarding and exit${NC}"
echo ""

# Keep the script running to maintain port forwarding
echo -e "${BLUE}⏳ Keeping port forwarding active... (Press Ctrl+C to exit)${NC}"
wait ${PORT_FORWARD_PID} 