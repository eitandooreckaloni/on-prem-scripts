#!/bin/bash

# 🔧 On-Prem Infrastructure Versions
# Central version management for all on-prem deployment scripts
# Source this file in other scripts: source ./versions.sh

# =============================================================================
# CORE INFRASTRUCTURE VERSIONS
# =============================================================================

# Kubernetes & Container Orchestration
export DOCKER_VERSION="24.0.7"
export KUBERNETES_VERSION="1.28.0"  # Add if needed

# Argo Ecosystem
export ARGOCD_VERSION="2.5.15"
export ARGO_WORKFLOWS_VERSION="3.6.5"

# Monitoring & Observability
export GRAFANA_VERSION="9.1.6"
export ELASTIC_VERSION="8.17.0"
export PROMETHEUS_VERSION="2.45.0"  # Common pairing with Grafana

# Operating System
export UBUNTU_VERSION="20.04.1"

# Database
export POSTGRES_VERSION="13.12"
export REDIS_VERSION="7.0.12"

# =============================================================================
# DOCKER IMAGE TAGS
# =============================================================================

# Argo
export ARGOCD_IMAGE="quay.io/argoproj/argocd:v${ARGOCD_VERSION}"
export ARGO_WORKFLOWS_IMAGE="quay.io/argoproj/workflow-controller:v${ARGO_WORKFLOWS_VERSION}"
export ARGO_SERVER_IMAGE="quay.io/argoproj/argocli:v${ARGO_WORKFLOWS_VERSION}"

# Monitoring
export GRAFANA_IMAGE="grafana/grafana:${GRAFANA_VERSION}"
export ELASTICSEARCH_IMAGE="docker.elastic.co/elasticsearch/elasticsearch:${ELASTIC_VERSION}"
export KIBANA_IMAGE="docker.elastic.co/kibana/kibana:${ELASTIC_VERSION}"

# Database
export POSTGRES_IMAGE="postgres:${POSTGRES_VERSION}-alpine"
export REDIS_IMAGE="redis:${REDIS_VERSION}-alpine"

# =============================================================================
# INSTALLATION URLs & MANIFESTS
# =============================================================================

# Argo Workflows
export ARGO_WORKFLOWS_INSTALL_URL="https://github.com/argoproj/argo-workflows/releases/download/v${ARGO_WORKFLOWS_VERSION}/install.yaml"
export ARGO_WORKFLOWS_NAMESPACE_INSTALL_URL="https://github.com/argoproj/argo-workflows/releases/download/v${ARGO_WORKFLOWS_VERSION}/namespace-install.yaml"

# ArgoCD
export ARGOCD_INSTALL_URL="https://raw.githubusercontent.com/argoproj/argo-cd/v${ARGOCD_VERSION}/manifests/install.yaml"
export ARGOCD_HA_INSTALL_URL="https://raw.githubusercontent.com/argoproj/argo-cd/v${ARGOCD_VERSION}/manifests/ha/install.yaml"

# Grafana (Helm)
export GRAFANA_HELM_REPO="https://grafana.github.io/helm-charts"
export GRAFANA_HELM_CHART="grafana/grafana"

# =============================================================================
# NETWORK & PORTS
# =============================================================================

# Argo
export ARGOCD_PORT="8080"
export ARGOCD_GRPC_PORT="8443"
export ARGO_WORKFLOWS_PORT="2746"

# Monitoring
export GRAFANA_PORT="3000"
export ELASTICSEARCH_PORT="9200"
export KIBANA_PORT="5601"

# Databases
export POSTGRES_PORT="5432"
export REDIS_PORT="6379"

# =============================================================================
# NAMESPACES
# =============================================================================

export ARGOCD_NAMESPACE="argocd"
export ARGO_WORKFLOWS_NAMESPACE="argo"
export MONITORING_NAMESPACE="monitoring"
export ELASTIC_NAMESPACE="elastic-system"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

# Print all versions
print_versions() {
    echo "🔧 On-Prem Infrastructure Versions"
    echo "=================================="
    echo "ArgoCD:          ${ARGOCD_VERSION}"
    echo "Argo Workflows:  ${ARGO_WORKFLOWS_VERSION}"
    echo "Grafana:         ${GRAFANA_VERSION}"
    echo "Elasticsearch:   ${ELASTIC_VERSION}"
    echo "Docker:          ${DOCKER_VERSION}"
    echo "Ubuntu:          ${UBUNTU_VERSION}"
    echo "PostgreSQL:      ${POSTGRES_VERSION}"
    echo "Redis:           ${REDIS_VERSION}"
}

# Check if version matches expected
check_version() {
    local tool=$1
    local expected=$2
    local actual=$3
    
    if [[ "$actual" == "$expected"* ]]; then
        echo "✅ $tool version matches: $actual"
        return 0
    else
        echo "❌ $tool version mismatch. Expected: $expected, Got: $actual"
        return 1
    fi
}

# Validate Docker version
validate_docker_version() {
    if command -v docker &> /dev/null; then
        DOCKER_ACTUAL=$(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
        check_version "Docker" "$DOCKER_VERSION" "$DOCKER_ACTUAL"
    else
        echo "❌ Docker not found"
        return 1
    fi
}

# Export all functions
export -f print_versions check_version validate_docker_version

# =============================================================================
# USAGE EXAMPLES
# =============================================================================

# In your scripts, source this file:
# source ./versions.sh
# kubectl apply -f "$ARGO_WORKFLOWS_INSTALL_URL"
# docker run "$GRAFANA_IMAGE"

# Print versions when sourced directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    print_versions
fi 