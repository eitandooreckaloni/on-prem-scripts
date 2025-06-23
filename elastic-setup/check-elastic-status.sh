#!/bin/bash

# 📊 Check Elasticsearch Status
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

echo -e "${BLUE}📊 Elasticsearch Status Check${NC}"
echo "============================="

# Check if .env file exists
if [[ -f ".env" ]]; then
    ELASTIC_PASSWORD=$(grep ELASTIC_PASSWORD .env | cut -d'=' -f2)
else
    echo -e "${RED}❌ .env file not found${NC}"
    exit 1
fi

# Function to make authenticated requests
elastic_request() {
    curl -s -u "elastic:${ELASTIC_PASSWORD}" "$@"
}

# Check Docker containers
echo -e "${YELLOW}🐳 Docker Container Status:${NC}"
if docker-compose ps 2>/dev/null; then
    echo -e "${GREEN}✅ Docker containers found${NC}"
else
    echo -e "${RED}❌ No docker-compose containers found${NC}"
    exit 1
fi

echo ""

# Check Elasticsearch health
echo -e "${YELLOW}🔍 Elasticsearch Health:${NC}"
if health_response=$(elastic_request "http://localhost:${ELASTICSEARCH_PORT}/_cluster/health" 2>/dev/null); then
    echo "$health_response" | jq '.' 2>/dev/null || echo "$health_response"
    
    # Extract status
    status=$(echo "$health_response" | jq -r '.status' 2>/dev/null || echo "unknown")
    case $status in
        "green")
            echo -e "${GREEN}✅ Cluster status: GREEN (All good!)${NC}"
            ;;
        "yellow")
            echo -e "${YELLOW}⚠️  Cluster status: YELLOW (Warning)${NC}"
            ;;
        "red")
            echo -e "${RED}❌ Cluster status: RED (Critical)${NC}"
            ;;
        *)
            echo -e "${YELLOW}⚠️  Cluster status: UNKNOWN${NC}"
            ;;
    esac
else
    echo -e "${RED}❌ Elasticsearch is not responding${NC}"
fi

echo ""

# Check Elasticsearch version
echo -e "${YELLOW}📋 Elasticsearch Version:${NC}"
if version_response=$(elastic_request "http://localhost:${ELASTICSEARCH_PORT}/" 2>/dev/null); then
    actual_version=$(echo "$version_response" | jq -r '.version.number' 2>/dev/null || echo "unknown")
    if [[ "$actual_version" == "$ELASTIC_VERSION" ]]; then
        echo -e "${GREEN}✅ Version: ${actual_version} (matches expected ${ELASTIC_VERSION})${NC}"
    else
        echo -e "${YELLOW}⚠️  Version: ${actual_version} (expected ${ELASTIC_VERSION})${NC}"
    fi
else
    echo -e "${RED}❌ Could not retrieve version information${NC}"
fi

echo ""

# Check node information
echo -e "${YELLOW}🖥️  Node Information:${NC}"
if nodes_response=$(elastic_request "http://localhost:${ELASTICSEARCH_PORT}/_nodes/_local?pretty" 2>/dev/null); then
    node_name=$(echo "$nodes_response" | jq -r '.nodes | to_entries | .[0].value.name' 2>/dev/null || echo "unknown")
    echo "Node name: $node_name"
    
    jvm_version=$(echo "$nodes_response" | jq -r '.nodes | to_entries | .[0].value.jvm.version' 2>/dev/null || echo "unknown")
    echo "JVM version: $jvm_version"
    
    os_name=$(echo "$nodes_response" | jq -r '.nodes | to_entries | .[0].value.os.name' 2>/dev/null || echo "unknown")
    echo "OS: $os_name"
else
    echo -e "${RED}❌ Could not retrieve node information${NC}"
fi

echo ""

# Check indices
echo -e "${YELLOW}📚 Indices:${NC}"
if indices_response=$(elastic_request "http://localhost:${ELASTICSEARCH_PORT}/_cat/indices?v" 2>/dev/null); then
    echo "$indices_response"
else
    echo -e "${RED}❌ Could not retrieve indices information${NC}"
fi

echo ""

# Check Kibana status
echo -e "${YELLOW}🌐 Kibana Status:${NC}"
if kibana_response=$(curl -s "http://localhost:${KIBANA_PORT}/api/status" 2>/dev/null); then
    kibana_status=$(echo "$kibana_response" | jq -r '.status.overall.state' 2>/dev/null || echo "unknown")
    case $kibana_status in
        "green")
            echo -e "${GREEN}✅ Kibana status: GREEN${NC}"
            ;;
        "yellow")
            echo -e "${YELLOW}⚠️  Kibana status: YELLOW${NC}"
            ;;
        "red")
            echo -e "${RED}❌ Kibana status: RED${NC}"
            ;;
        *)
            echo -e "${YELLOW}⚠️  Kibana status: UNKNOWN${NC}"
            ;;
    esac
    
    kibana_version=$(echo "$kibana_response" | jq -r '.version.number' 2>/dev/null || echo "unknown")
    echo "Kibana version: $kibana_version"
else
    echo -e "${RED}❌ Kibana is not responding${NC}"
fi

echo ""

# Security status
echo -e "${YELLOW}🔐 Security Status:${NC}"
if security_response=$(elastic_request "http://localhost:${ELASTICSEARCH_PORT}/_xpack" 2>/dev/null); then
    security_enabled=$(echo "$security_response" | jq -r '.features.security.enabled' 2>/dev/null || echo "unknown")
    if [[ "$security_enabled" == "true" ]]; then
        echo -e "${GREEN}✅ Security is enabled${NC}"
    else
        echo -e "${YELLOW}⚠️  Security status: ${security_enabled}${NC}"
    fi
else
    echo -e "${RED}❌ Could not retrieve security status${NC}"
fi

echo ""

# Summary
echo -e "${BLUE}📊 Summary:${NC}"
echo "Elasticsearch URL: http://localhost:${ELASTICSEARCH_PORT}"
echo "Kibana URL: http://localhost:${KIBANA_PORT}"
echo "Expected version: ${ELASTIC_VERSION}"
echo ""
echo -e "${BLUE}💡 Useful commands:${NC}"
echo "View logs:        docker-compose logs -f"
echo "Restart services: docker-compose restart"
echo "Open Kibana:      ./open-kibana.sh"
echo "Stop services:    ./stop-elasticsearch.sh" 