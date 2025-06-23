#!/bin/bash

# 🔄 Argo Workflows Version Reinstaller
# Safely reinstalls Argo Workflows to match the centralized version specification

set -e

# Source centralized versions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../versions.sh"

# Configuration
NAMESPACE="${ARGO_WORKFLOWS_NAMESPACE}"
TARGET_VERSION="v${ARGO_WORKFLOWS_VERSION}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔄 Argo Workflows Version Reinstaller${NC}"
echo "====================================="

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up any port-forward processes...${NC}"
    pkill -f "kubectl.*port-forward.*${ARGO_WORKFLOWS_PORT}:${ARGO_WORKFLOWS_PORT}" 2>/dev/null || true
}
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
    exit 1
fi
echo -e "${GREEN}✅ Connected to cluster: $(kubectl config current-context)${NC}"

# Check current version
echo -e "${BLUE}🔍 Checking current Argo Workflows version...${NC}"
if kubectl get namespace ${NAMESPACE} &> /dev/null && kubectl get deployment workflow-controller -n ${NAMESPACE} &> /dev/null; then
    CURRENT_IMAGE=$(kubectl get deployment workflow-controller -n ${NAMESPACE} -o jsonpath='{.spec.template.spec.containers[0].image}')
    CURRENT_VERSION=$(echo "$CURRENT_IMAGE" | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    echo -e "${YELLOW}📋 Current version: ${CURRENT_VERSION}${NC}"
    echo -e "${YELLOW}📋 Target version:  ${TARGET_VERSION}${NC}"
    
    if [[ "$CURRENT_VERSION" == "$TARGET_VERSION" ]]; then
        echo -e "${GREEN}✅ Already running the correct version (${TARGET_VERSION})${NC}"
        exit 0
    fi
else
    echo -e "${YELLOW}⚠️  Argo Workflows not found or not properly installed${NC}"
    CURRENT_VERSION="none"
fi

# Confirm the reinstallation
echo ""
echo -e "${YELLOW}⚠️  This will reinstall Argo Workflows${NC}"
echo -e "${BLUE}   From: ${CURRENT_VERSION}${NC}"
echo -e "${BLUE}   To:   ${TARGET_VERSION}${NC}"
echo ""
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}🚫 Installation cancelled${NC}"
    exit 0
fi

# Step 1: Check for running workflows
echo -e "${BLUE}🔍 Checking for running workflows...${NC}"
if kubectl get workflows -n ${NAMESPACE} 2>/dev/null | grep -q Running; then
    echo -e "${RED}❌ There are running workflows. Please wait for them to complete or terminate them first.${NC}"
    echo -e "${YELLOW}💡 Check running workflows:${NC}"
    echo "   kubectl get workflows -n ${NAMESPACE}"
    echo -e "${YELLOW}💡 Delete workflows (if safe):${NC}"
    echo "   kubectl delete workflows --all -n ${NAMESPACE}"
    exit 1
fi
echo -e "${GREEN}✅ No running workflows found${NC}"

# Step 2: Backup current configuration (if exists)
if kubectl get namespace ${NAMESPACE} &> /dev/null; then
    echo -e "${BLUE}💾 Creating backup of current configuration...${NC}"
    mkdir -p backups
    BACKUP_FILE="backups/argo-backup-$(date +%Y%m%d-%H%M%S).yaml"
    kubectl get all -n ${NAMESPACE} -o yaml > "$BACKUP_FILE" 2>/dev/null || true
    echo -e "${GREEN}✅ Backup saved to: ${BACKUP_FILE}${NC}"
fi

# Step 3: Uninstall current version
if kubectl get namespace ${NAMESPACE} &> /dev/null; then
    echo -e "${BLUE}🗑️  Uninstalling current Argo Workflows...${NC}"
    
    # Delete the namespace and wait for cleanup
    kubectl delete namespace ${NAMESPACE} --timeout=60s
    
    # Wait for namespace to be fully deleted
    echo -e "${BLUE}⏳ Waiting for namespace cleanup...${NC}"
    timeout=60
    while kubectl get namespace ${NAMESPACE} &> /dev/null && [ $timeout -gt 0 ]; do
        sleep 2
        timeout=$((timeout - 2))
        echo -n "."
    done
    echo
    
    if kubectl get namespace ${NAMESPACE} &> /dev/null; then
        echo -e "${RED}❌ Namespace cleanup timeout. You may need to manually clean up resources.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Previous installation removed${NC}"
else
    echo -e "${YELLOW}⚠️  No existing installation found${NC}"
fi

# Step 4: Install target version
echo -e "${BLUE}📦 Installing Argo Workflows ${TARGET_VERSION}...${NC}"

# Create namespace
kubectl create namespace ${NAMESPACE}

# Install specific version
echo -e "${BLUE}⬇️  Downloading and applying manifests...${NC}"
kubectl apply -n ${NAMESPACE} -f "${ARGO_WORKFLOWS_INSTALL_URL}"

# Step 5: Wait for installation to complete
echo -e "${BLUE}⏳ Waiting for Argo Workflows to be ready...${NC}"
kubectl wait --for=condition=available deployment/argo-server -n ${NAMESPACE} --timeout=300s
kubectl wait --for=condition=available deployment/workflow-controller -n ${NAMESPACE} --timeout=300s

# Step 6: Verify installation
echo -e "${BLUE}🔍 Verifying installation...${NC}"
INSTALLED_VERSION=$(kubectl get deployment workflow-controller -n ${NAMESPACE} -o jsonpath='{.spec.template.spec.containers[0].image}' | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' | head -1)

if [[ "$INSTALLED_VERSION" == "$TARGET_VERSION" ]]; then
    echo -e "${GREEN}✅ Successfully installed Argo Workflows ${INSTALLED_VERSION}${NC}"
else
    echo -e "${RED}❌ Version mismatch! Installed: ${INSTALLED_VERSION}, Expected: ${TARGET_VERSION}${NC}"
    exit 1
fi

# Step 7: Show status
echo -e "${BLUE}📊 Deployment status:${NC}"
kubectl get pods -n ${NAMESPACE}

echo ""
echo -e "${GREEN}🎉 Argo Workflows reinstallation completed successfully!${NC}"
echo ""
echo -e "${BLUE}🚀 Next steps:${NC}"
echo "   1. Run: ./open-argo-gui.sh"
echo "   2. Or manually: kubectl -n ${NAMESPACE} port-forward deployment/argo-server ${ARGO_WORKFLOWS_PORT}:${ARGO_WORKFLOWS_PORT}"
echo "   3. Then open: https://localhost:${ARGO_WORKFLOWS_PORT}"
echo ""
echo -e "${YELLOW}📝 Note: Any previous workflows/templates will need to be redeployed${NC}"

# Optional: Auto-start GUI
echo ""
read -p "Open Argo GUI now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}🚀 Starting GUI...${NC}"
    exec "${SCRIPT_DIR}/open-argo-gui.sh"
fi 