#!/bin/bash

# 👥 Setup Elasticsearch Users and Roles
# Uses centralized version management from versions.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Source centralized versions
if [[ -f "../versions.sh" ]]; then
    source ../versions.sh
elif [[ -f "./versions.sh" ]]; then
    source ./versions.sh
else
    echo -e "${RED}❌ versions.sh not found. Please run from project root or elastic-setup directory${NC}"
    exit 1
fi

echo -e "${BLUE}👥 Setting up Elasticsearch Users${NC}"
echo "=================================="

# Check if Elasticsearch is running
if ! curl -s http://localhost:${ELASTICSEARCH_PORT} >/dev/null 2>&1; then
    echo -e "${RED}❌ Elasticsearch is not running. Please start it first with ./start-elasticsearch.sh${NC}"
    exit 1
fi

# Get elastic password from .env
ELASTIC_PASSWORD=$(grep ELASTIC_PASSWORD .env | cut -d'=' -f2)

if [[ -z "$ELASTIC_PASSWORD" || "$ELASTIC_PASSWORD" == "your-secure-password-here" ]]; then
    echo -e "${RED}❌ Please set ELASTIC_PASSWORD in .env file${NC}"
    exit 1
fi

echo -e "${YELLOW}🔧 Setting up Kibana system password...${NC}"
KIBANA_PASSWORD=$(grep KIBANA_PASSWORD .env | cut -d'=' -f2)

# Set kibana_system password
curl -X POST "localhost:${ELASTICSEARCH_PORT}/_security/user/kibana_system/_password" \
  -u "elastic:${ELASTIC_PASSWORD}" \
  -H "Content-Type: application/json" \
  -d "{\"password\":\"${KIBANA_PASSWORD}\"}"

echo -e "${GREEN}✅ Kibana system password set${NC}"

# Create monitoring user
echo -e "${YELLOW}🔧 Creating monitoring user...${NC}"
curl -X POST "localhost:${ELASTICSEARCH_PORT}/_security/user/monitoring_user" \
  -u "elastic:${ELASTIC_PASSWORD}" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "monitoring_password_123",
    "roles": ["monitoring_user"],
    "full_name": "Monitoring User",
    "email": "monitoring@onprem.local"
  }'

echo -e "${GREEN}✅ Monitoring user created${NC}"

# Create application user for workflows
echo -e "${YELLOW}🔧 Creating workflow application user...${NC}"
curl -X POST "localhost:${ELASTICSEARCH_PORT}/_security/user/workflow_app" \
  -u "elastic:${ELASTIC_PASSWORD}" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "workflow_app_password_123",
    "roles": ["editor"],
    "full_name": "Workflow Application User",
    "email": "workflow@onprem.local"
  }'

echo -e "${GREEN}✅ Workflow application user created${NC}"

# Create read-only user
echo -e "${YELLOW}🔧 Creating read-only user...${NC}"
curl -X POST "localhost:${ELASTICSEARCH_PORT}/_security/user/readonly_user" \
  -u "elastic:${ELASTIC_PASSWORD}" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "readonly_password_123",
    "roles": ["viewer"],
    "full_name": "Read Only User",
    "email": "readonly@onprem.local"
  }'

echo -e "${GREEN}✅ Read-only user created${NC}"

# Create custom role for Argo Workflows integration
echo -e "${YELLOW}🔧 Creating custom role for Argo Workflows...${NC}"
curl -X POST "localhost:${ELASTICSEARCH_PORT}/_security/role/argo_workflows_role" \
  -u "elastic:${ELASTIC_PASSWORD}" \
  -H "Content-Type: application/json" \
  -d '{
    "cluster": ["monitor", "manage_index_templates"],
    "indices": [
      {
        "names": ["argo-*", "workflow-*", "logs-*", "metrics-*"],
        "privileges": ["create", "delete", "index", "manage", "read", "write"]
      }
    ]
  }'

echo -e "${GREEN}✅ Argo Workflows role created${NC}"

# Create user for Argo Workflows
echo -e "${YELLOW}🔧 Creating Argo Workflows user...${NC}"
curl -X POST "localhost:${ELASTICSEARCH_PORT}/_security/user/argo_workflows" \
  -u "elastic:${ELASTIC_PASSWORD}" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "argo_workflows_password_123",
    "roles": ["argo_workflows_role"],
    "full_name": "Argo Workflows Integration User",
    "email": "argo@onprem.local"
  }'

echo -e "${GREEN}✅ Argo Workflows user created${NC}"

echo ""
echo -e "${GREEN}🎉 User setup complete!${NC}"
echo ""
echo -e "${BLUE}👥 Created Users:${NC}"
echo "┌─────────────────┬─────────────────────────┬──────────────────────────┐"
echo "│ Username        │ Password                │ Role                     │"
echo "├─────────────────┼─────────────────────────┼──────────────────────────┤"
echo "│ elastic         │ $(grep ELASTIC_PASSWORD .env | cut -d'=' -f2 | head -c 20)... │ superuser                │"
echo "│ kibana_system   │ $(grep KIBANA_PASSWORD .env | cut -d'=' -f2 | head -c 20)...  │ kibana_system           │"
echo "│ monitoring_user │ monitoring_password_123 │ monitoring_user          │"
echo "│ workflow_app    │ workflow_app_password_123│ editor                   │"
echo "│ readonly_user   │ readonly_password_123   │ viewer                   │"
echo "│ argo_workflows  │ argo_workflows_password_123│ argo_workflows_role    │"
echo "└─────────────────┴─────────────────────────┴──────────────────────────┘"
echo ""
echo -e "${YELLOW}🔐 Security Notes:${NC}"
echo "• Change default passwords in production"
echo "• Use strong passwords (consider using a password manager)"
echo "• Regularly rotate passwords"
echo "• Consider using API keys for service-to-service authentication"
echo ""
echo -e "${BLUE}🔗 Integration Examples:${NC}"
echo "• Argo Workflows logging: Use 'argo_workflows' user"
echo "• Monitoring dashboards: Use 'monitoring_user' user"
echo "• Application logs: Use 'workflow_app' user"
echo "• Read-only access: Use 'readonly_user' user" 