#!/bin/bash

# 🔍 On-Prem Version Checker
# Validates that your environment matches the expected tool versions

set -e

# Source centralized versions
source ./versions.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 On-Prem Version Checker${NC}"
echo "=========================="
echo ""

# Track overall status
OVERALL_STATUS=0

# Function to check command version
check_tool_version() {
    local tool_name=$1
    local expected_version=$2
    local version_command=$3
    local version_regex=$4
    
    echo -e "${BLUE}Checking ${tool_name}...${NC}"
    
    if ! command -v ${version_command%% *} &> /dev/null; then
        echo -e "${RED}❌ ${tool_name} not found${NC}"
        OVERALL_STATUS=1
        return 1
    fi
    
    actual_version=$(eval "$version_command" 2>/dev/null | grep -oE "$version_regex" | head -1)
    
    if [[ -z "$actual_version" ]]; then
        echo -e "${YELLOW}⚠️  ${tool_name} version could not be determined${NC}"
        OVERALL_STATUS=1
        return 1
    fi
    
    if [[ "$actual_version" == "$expected_version"* ]] || [[ "$actual_version" == "v$expected_version"* ]]; then
        echo -e "${GREEN}✅ ${tool_name}: ${actual_version} (matches ${expected_version})${NC}"
        return 0
    else
        echo -e "${RED}❌ ${tool_name}: ${actual_version} (expected ${expected_version})${NC}"
        OVERALL_STATUS=1
        return 1
    fi
}

# Function to check Kubernetes-deployed tool
check_k8s_tool() {
    local tool_name=$1
    local namespace=$2
    local expected_version=$3
    local deployment_name=$4
    
    echo -e "${BLUE}Checking ${tool_name} in Kubernetes...${NC}"
    
    if ! kubectl get namespace "$namespace" &> /dev/null; then
        echo -e "${RED}❌ ${tool_name} namespace '${namespace}' not found${NC}"
        OVERALL_STATUS=1
        return 1
    fi
    
    if ! kubectl get deployment "$deployment_name" -n "$namespace" &> /dev/null; then
        echo -e "${RED}❌ ${tool_name} deployment '${deployment_name}' not found in namespace '${namespace}'${NC}"
        OVERALL_STATUS=1
        return 1
    fi
    
    # Get image version from deployment
    actual_version=$(kubectl get deployment "$deployment_name" -n "$namespace" -o jsonpath='{.spec.template.spec.containers[0].image}' | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    
    if [[ -z "$actual_version" ]]; then
        echo -e "${YELLOW}⚠️  ${tool_name} version could not be determined from deployment${NC}"
        OVERALL_STATUS=1
        return 1
    fi
    
    if [[ "$actual_version" == "v$expected_version"* ]]; then
        echo -e "${GREEN}✅ ${tool_name}: ${actual_version} (matches v${expected_version})${NC}"
        return 0
    else
        echo -e "${RED}❌ ${tool_name}: ${actual_version} (expected v${expected_version})${NC}"
        OVERALL_STATUS=1
        return 1
    fi
}

# Check system tools
echo -e "${YELLOW}📋 System Tools${NC}"
echo "---------------"

check_tool_version "Docker" "$DOCKER_VERSION" "docker --version" '[0-9]+\.[0-9]+\.[0-9]+'

if command -v lsb_release &> /dev/null; then
    check_tool_version "Ubuntu" "$UBUNTU_VERSION" "lsb_release -r" '[0-9]+\.[0-9]+\.[0-9]+'
elif [[ -f /etc/os-release ]]; then
    actual_ubuntu=$(grep VERSION_ID /etc/os-release | cut -d'"' -f2)
    if [[ "$actual_ubuntu" == "$UBUNTU_VERSION"* ]]; then
        echo -e "${GREEN}✅ Ubuntu: ${actual_ubuntu} (matches ${UBUNTU_VERSION})${NC}"
    else
        echo -e "${RED}❌ Ubuntu: ${actual_ubuntu} (expected ${UBUNTU_VERSION})${NC}"
        OVERALL_STATUS=1
    fi
else
    echo -e "${YELLOW}⚠️  Ubuntu version could not be determined${NC}"
fi

echo ""

# Check Kubernetes tools
echo -e "${YELLOW}☸️  Kubernetes Tools${NC}"
echo "-------------------"

if kubectl cluster-info &> /dev/null; then
    check_k8s_tool "Argo Workflows" "$ARGO_WORKFLOWS_NAMESPACE" "$ARGO_WORKFLOWS_VERSION" "workflow-controller"
    check_k8s_tool "ArgoCD" "$ARGOCD_NAMESPACE" "$ARGOCD_VERSION" "argocd-server"
else
    echo -e "${YELLOW}⚠️  Kubernetes cluster not accessible - skipping K8s tools${NC}"
fi

echo ""

# Check containerized tools (if running)
echo -e "${YELLOW}🐳 Containerized Tools${NC}"
echo "----------------------"

# Check if Grafana container is running
if docker ps --format "table {{.Names}}\t{{.Image}}" | grep -q grafana; then
    grafana_image=$(docker ps --format "{{.Image}}" | grep grafana | head -1)
    grafana_version=$(echo "$grafana_image" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    if [[ "$grafana_version" == "$GRAFANA_VERSION"* ]]; then
        echo -e "${GREEN}✅ Grafana: ${grafana_version} (matches ${GRAFANA_VERSION})${NC}"
    else
        echo -e "${RED}❌ Grafana: ${grafana_version} (expected ${GRAFANA_VERSION})${NC}"
        OVERALL_STATUS=1
    fi
else
    echo -e "${YELLOW}⚠️  Grafana container not running${NC}"
fi

# Check if Elasticsearch container is running
if docker ps --format "table {{.Names}}\t{{.Image}}" | grep -q elasticsearch; then
    elastic_image=$(docker ps --format "{{.Image}}" | grep elasticsearch | head -1)
    elastic_version=$(echo "$elastic_image" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    if [[ "$elastic_version" == "$ELASTIC_VERSION"* ]]; then
        echo -e "${GREEN}✅ Elasticsearch: ${elastic_version} (matches ${ELASTIC_VERSION})${NC}"
    else
        echo -e "${RED}❌ Elasticsearch: ${elastic_version} (expected ${ELASTIC_VERSION})${NC}"
        OVERALL_STATUS=1
    fi
else
    echo -e "${YELLOW}⚠️  Elasticsearch container not running${NC}"
fi

echo ""

# Summary
echo -e "${BLUE}📊 Summary${NC}"
echo "----------"

if [[ $OVERALL_STATUS -eq 0 ]]; then
    echo -e "${GREEN}🎉 All checked versions match expected versions!${NC}"
    echo -e "${GREEN}✅ Your on-prem environment is consistent${NC}"
else
    echo -e "${RED}❌ Some versions don't match expected versions${NC}"
    echo -e "${YELLOW}💡 Consider updating tools or adjusting versions.sh${NC}"
fi

echo ""
echo -e "${BLUE}📋 Expected Versions (from versions.sh):${NC}"
print_versions

exit $OVERALL_STATUS 