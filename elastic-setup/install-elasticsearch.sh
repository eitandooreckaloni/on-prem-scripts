#!/bin/bash

# 🔍 Elasticsearch Installation Script
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

echo -e "${BLUE}🔍 Installing Elasticsearch ${ELASTIC_VERSION}${NC}"
echo "============================================="

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is required but not installed${NC}"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ docker-compose is required but not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker and docker-compose are available${NC}"

# Create network if it doesn't exist
echo -e "${YELLOW}📡 Creating elastic network...${NC}"
docker network create elastic 2>/dev/null || echo -e "${YELLOW}⚠️  Network 'elastic' already exists${NC}"

# Create directory structure
echo -e "${YELLOW}📁 Creating directory structure...${NC}"
mkdir -p {data,logs,config}

# Set proper permissions for Elasticsearch data directory
echo -e "${YELLOW}🔐 Setting permissions...${NC}"
sudo chown -R 1000:1000 data logs

# Create elasticsearch.yml configuration
echo -e "${YELLOW}⚙️  Creating Elasticsearch configuration...${NC}"
cat > config/elasticsearch.yml << EOF
# Elasticsearch ${ELASTIC_VERSION} Configuration
cluster.name: "on-prem-elastic-cluster"
node.name: "elastic-node-1"

# Network
network.host: 0.0.0.0
http.port: ${ELASTICSEARCH_PORT}

# Discovery
discovery.type: single-node

# Security
xpack.security.enabled: true
xpack.security.enrollment.enabled: true

# Monitoring
xpack.monitoring.collection.enabled: true

# Machine Learning
xpack.ml.enabled: true

# Path settings
path.data: /usr/share/elasticsearch/data
path.logs: /usr/share/elasticsearch/logs

# JVM settings
bootstrap.memory_lock: true

# Index settings
action.destructive_requires_name: true
EOF

# Create Kibana configuration
echo -e "${YELLOW}⚙️  Creating Kibana configuration...${NC}"
mkdir -p config/kibana
cat > config/kibana/kibana.yml << EOF
# Kibana ${ELASTIC_VERSION} Configuration
server.name: "on-prem-kibana"
server.host: "0.0.0.0"
server.port: ${KIBANA_PORT}

# Elasticsearch connection
elasticsearch.hosts: ["http://elasticsearch:${ELASTICSEARCH_PORT}"]
elasticsearch.username: "kibana_system"

# Security
xpack.security.enabled: true
xpack.encryptedSavedObjects.encryptionKey: "fhjskloppd678ehkdfdlliverpoolfcr"

# Monitoring
monitoring.ui.container.elasticsearch.enabled: true
EOF

# Create docker-compose.yml
echo -e "${YELLOW}🐳 Creating docker-compose configuration...${NC}"
cat > docker-compose.yml << EOF
version: '3.8'

services:
  elasticsearch:
    image: ${ELASTICSEARCH_IMAGE}
    container_name: elasticsearch
    environment:
      - node.name=elasticsearch
      - cluster.name=on-prem-elastic-cluster
      - discovery.type=single-node
      - ELASTIC_PASSWORD=\${ELASTIC_PASSWORD:-changeme}
      - bootstrap.memory_lock=true
      - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
      - xpack.security.enabled=true
      - xpack.security.enrollment.enabled=true
    ulimits:
      memlock:
        soft: -1
        hard: -1
    volumes:
      - ./data:/usr/share/elasticsearch/data:rw
      - ./logs:/usr/share/elasticsearch/logs:rw
      - ./config/elasticsearch.yml:/usr/share/elasticsearch/config/elasticsearch.yml:ro
    ports:
      - "${ELASTICSEARCH_PORT}:${ELASTICSEARCH_PORT}"
    networks:
      - elastic
    healthcheck:
      test: ["CMD-SHELL", "curl -u elastic:\$\${ELASTIC_PASSWORD:-changeme} -s http://localhost:${ELASTICSEARCH_PORT}/_cluster/health | grep -q 'yellow\\|green'"]
      interval: 30s
      timeout: 10s
      retries: 5

  kibana:
    image: ${KIBANA_IMAGE}
    container_name: kibana
    depends_on:
      elasticsearch:
        condition: service_healthy
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:${ELASTICSEARCH_PORT}
      - ELASTICSEARCH_USERNAME=kibana_system
      - ELASTICSEARCH_PASSWORD=\${KIBANA_PASSWORD:-changeme}
    volumes:
      - ./config/kibana/kibana.yml:/usr/share/kibana/config/kibana.yml:ro
    ports:
      - "${KIBANA_PORT}:${KIBANA_PORT}"
    networks:
      - elastic
    healthcheck:
      test: ["CMD-SHELL", "curl -s http://localhost:${KIBANA_PORT}/api/status | grep -q 'available'"]
      interval: 30s
      timeout: 10s
      retries: 5

networks:
  elastic:
    external: true

volumes:
  elasticsearch_data:
    driver: local
EOF

# Create environment file
echo -e "${YELLOW}🔧 Creating environment configuration...${NC}"
cat > .env << EOF
# Elasticsearch Environment Configuration
ELASTIC_VERSION=${ELASTIC_VERSION}
ELASTIC_PASSWORD=your-secure-password-here
KIBANA_PASSWORD=your-secure-kibana-password-here

# Ports (from centralized versions)
ELASTICSEARCH_PORT=${ELASTICSEARCH_PORT}
KIBANA_PORT=${KIBANA_PORT}

# JVM Settings
ES_JAVA_OPTS=-Xms1g -Xmx1g
EOF

echo -e "${GREEN}✅ Configuration files created${NC}"
echo ""
echo -e "${YELLOW}🔐 IMPORTANT: Update passwords in .env file before starting!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Edit .env file to set secure passwords"
echo "2. Run: ./start-elasticsearch.sh"
echo "3. Run: ./setup-users.sh (to configure users)"
echo ""
echo -e "${GREEN}📁 Files created:${NC}"
echo "- docker-compose.yml"
echo "- .env"
echo "- config/elasticsearch.yml"
echo "- config/kibana/kibana.yml"
echo "- data/ (directory for Elasticsearch data)"
echo "- logs/ (directory for Elasticsearch logs)" 