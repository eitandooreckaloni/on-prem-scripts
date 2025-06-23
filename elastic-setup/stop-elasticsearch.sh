#!/bin/bash

# 🛑 Stop Elasticsearch and Kibana
# Uses centralized version management from versions.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 Stopping Elasticsearch Stack${NC}"
echo "================================"

# Check if docker-compose.yml exists
if [[ ! -f "docker-compose.yml" ]]; then
    echo -e "${RED}❌ docker-compose.yml not found. Are you in the correct directory?${NC}"
    exit 1
fi

# Show current status
echo -e "${YELLOW}📊 Current status:${NC}"
docker-compose ps

echo ""
echo -e "${YELLOW}🛑 Stopping services...${NC}"
docker-compose down

echo -e "${GREEN}✅ Elasticsearch stack stopped${NC}"
echo ""
echo -e "${BLUE}💡 Useful commands:${NC}"
echo "Start again:        ./start-elasticsearch.sh"
echo "Remove data:        docker-compose down -v"
echo "View logs:          docker-compose logs"
echo "Remove containers:  docker-compose rm" 