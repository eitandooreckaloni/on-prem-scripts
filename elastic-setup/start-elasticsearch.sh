#!/bin/bash

# 🚀 Start Elasticsearch and Kibana
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

echo -e "${BLUE}🚀 Starting Elasticsearch ${ELASTIC_VERSION}${NC}"
echo "======================================="

# Check if docker-compose.yml exists
if [[ ! -f "docker-compose.yml" ]]; then
    echo -e "${RED}❌ docker-compose.yml not found. Please run ./install-elasticsearch.sh first${NC}"
    exit 1
fi

# Check if .env file exists and has been configured
if [[ ! -f ".env" ]]; then
    echo -e "${RED}❌ .env file not found. Please run ./install-elasticsearch.sh first${NC}"
    exit 1
fi

# Check if passwords have been changed from defaults
if grep -q "your-secure-password-here" .env; then
    echo -e "${RED}❌ Please update passwords in .env file before starting!${NC}"
    echo "Edit .env and change ELASTIC_PASSWORD and KIBANA_PASSWORD"
    exit 1
fi

# Pull latest images
echo -e "${YELLOW}📥 Pulling Elasticsearch images...${NC}"
docker-compose pull

# Start services
echo -e "${YELLOW}🐳 Starting Elasticsearch and Kibana...${NC}"
docker-compose up -d

# Wait for Elasticsearch to be ready
echo -e "${YELLOW}⏳ Waiting for Elasticsearch to be ready...${NC}"
timeout=300
counter=0

while [ $counter -lt $timeout ]; do
    if docker-compose exec -T elasticsearch curl -u elastic:$(grep ELASTIC_PASSWORD .env | cut -d'=' -f2) -s http://localhost:${ELASTICSEARCH_PORT}/_cluster/health >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Elasticsearch is ready!${NC}"
        break
    fi
    echo -n "."
    sleep 5
    counter=$((counter + 5))
done

if [ $counter -ge $timeout ]; then
    echo -e "${RED}❌ Elasticsearch failed to start within ${timeout} seconds${NC}"
    echo "Check logs with: docker-compose logs elasticsearch"
    exit 1
fi

# Wait for Kibana to be ready
echo -e "${YELLOW}⏳ Waiting for Kibana to be ready...${NC}"
counter=0

while [ $counter -lt $timeout ]; do
    if curl -s http://localhost:${KIBANA_PORT}/api/status >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Kibana is ready!${NC}"
        break
    fi
    echo -n "."
    sleep 5
    counter=$((counter + 5))
done

if [ $counter -ge $timeout ]; then
    echo -e "${RED}❌ Kibana failed to start within ${timeout} seconds${NC}"
    echo "Check logs with: docker-compose logs kibana"
    exit 1
fi

# Show status
echo ""
echo -e "${GREEN}🎉 Elasticsearch Stack is running!${NC}"
echo ""
echo -e "${BLUE}📊 Access URLs:${NC}"
echo "Elasticsearch: http://localhost:${ELASTICSEARCH_PORT}"
echo "Kibana:        http://localhost:${KIBANA_PORT}"
echo ""
echo -e "${BLUE}🔐 Default credentials:${NC}"
echo "Username: elastic"
echo "Password: $(grep ELASTIC_PASSWORD .env | cut -d'=' -f2)"
echo ""
echo -e "${BLUE}📋 Useful commands:${NC}"
echo "Check status:    docker-compose ps"
echo "View logs:       docker-compose logs -f"
echo "Stop services:   docker-compose down"
echo "Restart:         docker-compose restart"
echo ""
echo -e "${YELLOW}💡 Next steps:${NC}"
echo "1. Open Kibana at http://localhost:${KIBANA_PORT}"
echo "2. Login with elastic user"
echo "3. Set up additional users with ./setup-users.sh"
echo "4. Configure index patterns and dashboards" 