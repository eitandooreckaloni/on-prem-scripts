#!/bin/bash

# 🔐 Argo Workflows Authentication Fix
# Disables authentication for local development access

set -e

# Source centralized versions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../versions.sh"

# Configuration
NAMESPACE="${ARGO_WORKFLOWS_NAMESPACE}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔐 Argo Workflows Authentication Fix${NC}"
echo "==================================="

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl not found${NC}"
    exit 1
fi

# Check if Argo is installed
if ! kubectl get namespace ${NAMESPACE} &> /dev/null; then
    echo -e "${RED}❌ Argo namespace '${NAMESPACE}' not found${NC}"
    echo -e "${YELLOW}💡 Run ./install-argo.sh first${NC}"
    exit 1
fi

if ! kubectl get deployment argo-server -n ${NAMESPACE} &> /dev/null; then
    echo -e "${RED}❌ Argo server not found${NC}"
    exit 1
fi

echo -e "${BLUE}🔍 Current argo-server configuration...${NC}"

# Check current auth mode
CURRENT_ARGS=$(kubectl get deployment argo-server -n ${NAMESPACE} -o jsonpath='{.spec.template.spec.containers[0].args}' 2>/dev/null || echo "[]")
echo -e "${YELLOW}📋 Current server args: ${CURRENT_ARGS}${NC}"

# Method 1: Disable authentication (recommended for local development)
echo -e "${BLUE}🔧 Disabling authentication for local development...${NC}"

# Get the current image to preserve it
CURRENT_IMAGE=$(kubectl get deployment argo-server -n ${NAMESPACE} -o jsonpath='{.spec.template.spec.containers[0].image}')
echo -e "${YELLOW}📋 Using image: ${CURRENT_IMAGE}${NC}"

kubectl patch deployment argo-server -n ${NAMESPACE} --type='merge' -p='{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "argo-server",
          "image": "'${CURRENT_IMAGE}'",
          "args": [
            "server",
            "--auth-mode=server",
            "--secure=false"
          ]
        }]
      }
    }
  }
}'

# Wait for rollout to complete
echo -e "${BLUE}⏳ Waiting for server restart...${NC}"
kubectl rollout status deployment/argo-server -n ${NAMESPACE} --timeout=120s

# Also create a service account and bind cluster-admin role for broader access
echo -e "${BLUE}🔑 Setting up service account permissions...${NC}"

# Create service account
kubectl apply -f - <<EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: argo-server
  namespace: ${NAMESPACE}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: argo-server
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: argo-server
  namespace: ${NAMESPACE}
EOF

# Update the deployment to use the service account
kubectl patch deployment argo-server -n ${NAMESPACE} --type='merge' -p='{
  "spec": {
    "template": {
      "spec": {
        "serviceAccountName": "argo-server"
      }
    }
  }
}'

# Wait for the final rollout
echo -e "${BLUE}⏳ Waiting for final configuration...${NC}"
kubectl rollout status deployment/argo-server -n ${NAMESPACE} --timeout=120s

# Verify the server is ready
echo -e "${BLUE}🔍 Verifying server status...${NC}"
kubectl wait --for=condition=available deployment/argo-server -n ${NAMESPACE} --timeout=60s

# Show current pods
echo -e "${BLUE}📊 Current pod status:${NC}"
kubectl get pods -n ${NAMESPACE} -l app=argo-server

# Check if server is responding
echo -e "${BLUE}🌐 Testing server connectivity...${NC}"
sleep 5  # Give the server a moment to fully start

# Kill any existing port forwards
pkill -f "kubectl.*port-forward.*${ARGO_WORKFLOWS_PORT}:${ARGO_WORKFLOWS_PORT}" 2>/dev/null || true
sleep 2

# Start port forwarding in background for testing
kubectl -n ${NAMESPACE} port-forward deployment/argo-server ${ARGO_WORKFLOWS_PORT}:${ARGO_WORKFLOWS_PORT} > /dev/null 2>&1 &
PORT_FORWARD_PID=$!
sleep 3

# Test the connection
if curl -k -s "https://localhost:${ARGO_WORKFLOWS_PORT}/api/v1/info" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Server is responding correctly${NC}"
    CONNECTIVITY_OK=true
else
    echo -e "${YELLOW}⚠️  Server may still be starting up${NC}"
    CONNECTIVITY_OK=false
fi

# Clean up test port forward
kill $PORT_FORWARD_PID 2>/dev/null || true

echo ""
echo -e "${GREEN}🎉 Authentication fix completed!${NC}"
echo ""
echo -e "${BLUE}📋 Summary of changes:${NC}"
echo "   • Authentication disabled (--auth-mode=server)"
echo "   • HTTPS disabled for local development (--secure=false)"
echo "   • Service account created with cluster-admin permissions"
echo "   • Server restarted with new configuration"
echo ""
echo -e "${BLUE}🚀 Next steps:${NC}"
echo "   1. Run: ./open-argo-gui.sh"
echo "   2. Or manually: kubectl -n ${NAMESPACE} port-forward deployment/argo-server ${ARGO_WORKFLOWS_PORT}:${ARGO_WORKFLOWS_PORT}"
echo "   3. Then open: https://localhost:${ARGO_WORKFLOWS_PORT}"
echo ""
echo -e "${YELLOW}🔒 Security Note:${NC}"
echo "   This configuration is for LOCAL DEVELOPMENT only."
echo "   For production, enable proper authentication and RBAC."

# Offer to open GUI immediately
echo ""
read -p "Open Argo GUI now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}🚀 Starting GUI...${NC}"
    exec "${SCRIPT_DIR}/open-argo-gui.sh"
fi 