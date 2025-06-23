# 🔧 Version Management System

This document describes how to use the centralized version management system for your on-prem infrastructure.

## 📋 Overview

All tool versions are centrally managed in `versions.sh` to ensure consistency between development, testing, and on-premises deployment environments.

## 🏗️ Your Current Infrastructure Versions

| Tool | Version |
|------|---------|
| ArgoCD | 2.5.15 |
| Argo Workflows | 3.6.5 |
| Grafana | 9.1.6 |
| Elasticsearch | 8.17.0 |
| Docker | 24.0.7 |
| Ubuntu | 20.04.1 |
| PostgreSQL | 13.12 |
| Redis | 7.0.12 |

## 📁 Files

- **`versions.sh`** - Central version configuration (source this in your scripts)
- **`check-versions.sh`** - Validates your environment matches expected versions
- **`VERSION_MANAGEMENT.md`** - This documentation file

## 🚀 Usage

### 1. View Current Versions
```bash
./versions.sh
```

### 2. Check Environment Compatibility
```bash
./check-versions.sh
```

### 3. Use in Your Scripts
```bash
#!/bin/bash
# Source centralized versions
source ./versions.sh

# Use version-controlled URLs
kubectl apply -f "$ARGO_WORKFLOWS_INSTALL_URL"

# Use version-controlled images
docker run "$GRAFANA_IMAGE"

# Use version-controlled ports
kubectl port-forward deployment/argo-server "$ARGO_WORKFLOWS_PORT:$ARGO_WORKFLOWS_PORT"
```

## 🔄 Updated Scripts

The following scripts have been updated to use centralized versions:

- **`argo-workflows/install-argo.sh`** - Now uses `ARGO_WORKFLOWS_VERSION` (3.6.5)
- **`argo-workflows/open-argo-gui.sh`** - Now uses `ARGO_WORKFLOWS_PORT` and `ARGO_WORKFLOWS_NAMESPACE`

## 🎯 Benefits

### ✅ Consistency
- All scripts use the same versions
- No version mismatches between environments
- Easy to maintain and update

### ✅ Traceability
- Clear record of what versions are deployed
- Easy to identify version differences
- Centralized change management

### ✅ Validation
- `check-versions.sh` validates your environment
- Detects version mismatches early
- Prevents deployment issues

## 🔧 Available Variables

### Core Infrastructure
```bash
$DOCKER_VERSION        # 24.0.7
$ARGOCD_VERSION        # 2.5.15
$ARGO_WORKFLOWS_VERSION # 3.6.5
$GRAFANA_VERSION       # 9.1.6
$ELASTIC_VERSION       # 8.17.0
$UBUNTU_VERSION        # 20.04.1
```

### Docker Images
```bash
$ARGOCD_IMAGE          # quay.io/argoproj/argocd:v2.5.15
$GRAFANA_IMAGE         # grafana/grafana:9.1.6
$ELASTICSEARCH_IMAGE   # docker.elastic.co/elasticsearch/elasticsearch:8.17.0
```

### Installation URLs
```bash
$ARGO_WORKFLOWS_INSTALL_URL # https://github.com/argoproj/argo-workflows/releases/download/v3.6.5/install.yaml
$ARGOCD_INSTALL_URL         # https://raw.githubusercontent.com/argoproj/argo-cd/v2.5.15/manifests/install.yaml
```

### Ports & Namespaces
```bash
$ARGO_WORKFLOWS_PORT      # 2746
$ARGO_WORKFLOWS_NAMESPACE # argo
$ARGOCD_PORT             # 8080
$GRAFANA_PORT            # 3000
```

## 🛠️ Helper Functions

### Print All Versions
```bash
source ./versions.sh
print_versions
```

### Validate Docker Version
```bash
source ./versions.sh
validate_docker_version
```

### Check Specific Version
```bash
source ./versions.sh
check_version "Docker" "24.0.7" "24.0.7"
```

## 📝 Updating Versions

1. **Edit `versions.sh`** to update version numbers
2. **Run `check-versions.sh`** to validate your environment
3. **Update affected scripts** if needed
4. **Test in development** before deploying to on-prem

## 🚨 Important Notes

- **Always source `versions.sh`** in your scripts for consistency
- **Run `check-versions.sh`** before deploying to validate compatibility
- **Update versions.sh first** when upgrading tools
- **Test thoroughly** after version changes

## 📊 Example Validation Output

```bash
$ ./check-versions.sh
🔍 On-Prem Version Checker
==========================

📋 System Tools
---------------
Checking Docker...
✅ Docker: 24.0.7 (matches 24.0.7)

☸️  Kubernetes Tools
-------------------
Checking Argo Workflows in Kubernetes...
✅ Argo Workflows: v3.6.5 (matches v3.6.5)

🐳 Containerized Tools
----------------------
⚠️  Grafana container not running

📊 Summary
----------
🎉 All checked versions match expected versions!
✅ Your on-prem environment is consistent
```

## 🔗 Integration Examples

### Docker Compose
```yaml
version: '3.8'
services:
  grafana:
    image: ${GRAFANA_IMAGE}
    ports:
      - "${GRAFANA_PORT}:3000"
```

### Kubernetes Manifests
```bash
# Use version-controlled installation
kubectl apply -f "$ARGO_WORKFLOWS_INSTALL_URL"

# Deploy to version-controlled namespace
kubectl apply -n "$ARGO_WORKFLOWS_NAMESPACE" -f my-workflow.yaml
```

### Shell Scripts
```bash
#!/bin/bash
source ./versions.sh

echo "Installing Argo Workflows ${ARGO_WORKFLOWS_VERSION}"
kubectl apply -f "$ARGO_WORKFLOWS_INSTALL_URL"

echo "Opening GUI on port ${ARGO_WORKFLOWS_PORT}"
kubectl port-forward deployment/argo-server "$ARGO_WORKFLOWS_PORT:$ARGO_WORKFLOWS_PORT"
``` 